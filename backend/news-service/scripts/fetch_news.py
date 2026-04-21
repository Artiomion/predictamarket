"""
Fetch news: RSS → FinBERT sentiment → PostgreSQL + Redis Pub/Sub.

# Sources: Yahoo Finance, Reuters, MarketWatch
# Pipeline: parse RSS → deduplicate → strip HTML → FinBERT sentiment
         → match tickers → assign impact → store → publish high-impact

Usage:
  PYTHONPATH=backend .venv/bin/python backend/news-service/scripts/fetch_news.py
"""

import asyncio
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from html import unescape as html_unescape
from pathlib import Path
from time import mktime

_script_dir = Path(__file__).resolve().parent
for _p in [_script_dir.parent.parent, _script_dir.parent]:
    if (_p / "shared").is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
_svc_dir = _script_dir.parent
if str(_svc_dir) not in sys.path:
    sys.path.insert(0, str(_svc_dir))

import feedparser
import structlog
from sqlalchemy import Integer, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import async_session_factory
from shared.logging import setup_logging
from shared.models.market import Instrument
from shared.models.news import Article, InstrumentSentiment, SentimentDaily
from shared.redis_client import redis_client

from services.sentiment import finbert, SentimentResult

setup_logging()
logger = structlog.get_logger()

# Strip HTML tags from RSS content
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    return html_unescape(_HTML_TAG_RE.sub("", text)).strip()


# Short tickers that are common English words — only match with $ prefix
_AMBIGUOUS_TICKERS = {"DE", "GE", "MS", "GL", "DD", "GS", "FIX", "LOW", "HAS", "ALL", "IT", "A"}

LARGE_CAP_TICKERS = {
    "AAPL", "MSFT", "NVDA", "GILD", "LLY", "GS", "MS", "CVX", "COP",
    "COST", "LMT", "NOC", "DE", "ORCL", "LOW", "MRK", "NKE", "DIS",
}

RSS_FEEDS: list[dict[str, str]] = [
    # General market news
    {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news/rssindex"},
    {"name": "Yahoo Finance Top", "url": "https://finance.yahoo.com/rss/topfinstories"},
    {"name": "Reuters Business", "url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best"},
    {"name": "MarketWatch Top", "url": "https://feeds.marketwatch.com/marketwatch/topstories/"},
    {"name": "MarketWatch Markets", "url": "https://feeds.marketwatch.com/marketwatch/marketpulse/"},
    {"name": "CNBC Top", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
    {"name": "CNBC Markets", "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html"},
    {"name": "Investing.com", "url": "https://www.investing.com/rss/news.rss"},
    {"name": "Seeking Alpha", "url": "https://seekingalpha.com/market_currents.xml"},
]

# Yahoo Finance RSS per-ticker feeds for ALL supported S&P 500 tickers.
# Single source of truth: /models/old_model_sp500_tickers.txt (same file
# forecast-service uses for valid_tickers). Loaded lazily at first call so
# import-time failures surface only when fetch_news actually runs, and the
# ticker file is re-read on restart (no stale module-level cache across deploys).
import os as _os
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_ticker_rss_list() -> list[str]:
    """Load ticker list from the models volume; raise loudly if missing.

    Silent fallback to a tiny hardcoded list is worse than failing fast:
    prod would quietly provide news for 10 tickers instead of 346 and look healthy.
    """
    ticker_file = Path(_os.environ.get("MODELS_DIR", "/models")) / "old_model_sp500_tickers.txt"
    try:
        tickers = [
            t.strip().upper()
            for t in ticker_file.read_text().splitlines()
            if t.strip()
        ]
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Ticker list not found at {ticker_file}. Ensure news-service has "
            f"./models mounted read-only (see docker-compose.yml)."
        ) from exc
    if len(tickers) < 50:
        raise RuntimeError(
            f"Ticker list at {ticker_file} contains only {len(tickers)} entries — "
            f"expected ~346. Mounted volume may be stale or truncated."
        )
    return tickers


def _ticker_rss_list() -> list[str]:
    return _load_ticker_rss_list()


class TickerMatcher:
    """FIX #1 + #8: Compiled regex, avoids false positives on short/ambiguous tickers."""

    def __init__(self, tickers: list[str], name_map: dict[str, tuple[str, str]]) -> None:
        # name_map: {"APPLE": ("AAPL", "inst_id"), ...}
        self._tickers = set(tickers)
        self._name_map = name_map

        # Build single compiled regex for non-ambiguous tickers (3+ chars)
        safe_tickers = [t for t in tickers if t not in _AMBIGUOUS_TICKERS and len(t) >= 3]
        if safe_tickers:
            pattern = r'\b(' + '|'.join(re.escape(t) for t in sorted(safe_tickers, key=len, reverse=True)) + r')\b'
            self._safe_re = re.compile(pattern)
        else:
            self._safe_re = None

        # Ambiguous tickers only match with $ prefix: $GE, $MS, etc.
        ambiguous = [t for t in tickers if t in _AMBIGUOUS_TICKERS]
        if ambiguous:
            pattern = r'\$(' + '|'.join(re.escape(t) for t in ambiguous) + r')\b'
            self._ambiguous_re = re.compile(pattern)
        else:
            self._ambiguous_re = None

        self._ticker_to_id: dict[str, str] = {}

    def set_id_map(self, ticker_to_id: dict[str, str]) -> None:
        self._ticker_to_id = ticker_to_id

    def get_id(self, ticker: str) -> str | None:
        """Return instrument_id for a ticker if it's a known, active instrument."""
        return self._ticker_to_id.get(ticker)

    def match(self, title: str, summary: str | None = None) -> list[tuple[str, str]]:
        """Match tickers in title (primary) and summary (secondary). Returns [(ticker, inst_id)]."""
        # Match ticker symbols in title only; company names in title + summary
        text = title.upper()
        found: dict[str, str] = {}  # ticker → inst_id

        # Non-ambiguous tickers via compiled regex on title
        if self._safe_re:
            for m in self._safe_re.finditer(text):
                t = m.group(1)
                if t in self._ticker_to_id and t not in found:
                    found[t] = self._ticker_to_id[t]

        # Ambiguous tickers only with $ prefix (check original case text too)
        if self._ambiguous_re:
            full_text = title + (" " + summary if summary else "")
            for m in self._ambiguous_re.finditer(full_text.upper()):
                t = m.group(1)
                if t in self._ticker_to_id and t not in found:
                    found[t] = self._ticker_to_id[t]

        # Company name matching on title + summary
        full_upper = (title + " " + (summary or "")).upper()
        for name_word, (ticker, inst_id) in self._name_map.items():
            if name_word in full_upper and ticker not in found:
                found[ticker] = inst_id

        return list(found.items())


async def build_ticker_matcher(session: AsyncSession) -> TickerMatcher:
    """Build TickerMatcher from DB instruments."""
    result = await session.execute(
        select(Instrument.id, Instrument.ticker, Instrument.name)
        .where(Instrument.is_active.is_(True))
    )
    tickers: list[str] = []
    ticker_to_id: dict[str, str] = {}
    name_map: dict[str, tuple[str, str]] = {}

    for inst_id, ticker, name in result.all():
        tickers.append(ticker)
        ticker_to_id[ticker] = str(inst_id)
        if name:
            first_word = name.split()[0].rstrip(",.")
            if len(first_word) >= 4:  # Avoid short ambiguous names
                name_map[first_word.upper()] = (ticker, str(inst_id))

    matcher = TickerMatcher(tickers, name_map)
    matcher.set_id_map(ticker_to_id)
    return matcher


def determine_impact(
    sentiment: SentimentResult,
    matched_tickers: list[tuple[str, str]],
) -> str:
    has_large_cap = any(t in LARGE_CAP_TICKERS for t, _ in matched_tickers)
    if sentiment.score > 0.8 and has_large_cap:
        return "high"
    if sentiment.score > 0.6 or matched_tickers:
        return "medium"
    return "low"


def _parse_feed_entries(feed_cfg: dict, feed, seen_urls: set) -> list[dict]:
    """Extract entries from a parsed feed, deduplicating by URL."""
    entries = []
    for entry in feed.entries:
        url = entry.get("link", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = datetime.fromtimestamp(
                mktime(entry.published_parsed), tz=timezone.utc
            )
        if not published:
            published = datetime.now(timezone.utc)

        raw_summary = entry.get("summary", "")
        clean_summary = strip_html(raw_summary)[:500] if raw_summary else None

        entries.append({
            "title": strip_html(entry.get("title", "")),
            "url": url,
            "source": feed_cfg["name"],
            "published_at": published,
            "summary": clean_summary,
            # If this article came from a per-ticker feed (Yahoo ?s=TICKER),
            # carry the ticker so we can auto-tag it — the text matcher alone
            # misses 2-char tickers (BK, CF, CI, GE, ON) which are excluded
            # from the safe regex to avoid false positives in free text.
            "source_ticker": feed_cfg.get("source_ticker"),
        })
    return entries


async def fetch_rss_entries() -> list[dict]:
    """Fetch and deduplicate RSS entries from general + ticker-specific feeds."""
    all_entries: list[dict] = []
    seen_urls: set[str] = set()

    # 1. General feeds
    for feed_cfg in RSS_FEEDS:
        try:
            feed = await asyncio.to_thread(
                feedparser.parse, feed_cfg["url"],
            )
            all_entries.extend(_parse_feed_entries(feed_cfg, feed, seen_urls))
        except Exception as exc:
            await logger.aerror("rss_fetch_error", feed=feed_cfg["name"], error=str(exc))

    # 2. Ticker-specific feeds (Yahoo Finance per-ticker RSS) — auto-tagged
    # with source_ticker so the matcher can attach them even when the text
    # match would fail (short tickers, foreign names, etc.).
    for ticker in _ticker_rss_list():
        feed_cfg = {
            "name": f"Yahoo {ticker}",
            "url": f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
            "source_ticker": ticker,
        }
        try:
            feed = await asyncio.to_thread(
                feedparser.parse, feed_cfg["url"],
            )
            all_entries.extend(_parse_feed_entries(feed_cfg, feed, seen_urls))
        except Exception as exc:
            await logger.aerror("rss_fetch_error", feed=feed_cfg["name"], error=str(exc))

    await logger.ainfo("rss_fetched", total_entries=len(all_entries))
    return all_entries


async def process_and_store(entries: list[dict]) -> dict[str, int]:
    """Run FinBERT, match tickers, store articles, publish high-impact."""
    if not entries:
        return {"new": 0, "skipped": 0, "high_impact": 0}

    urls = [e["url"] for e in entries]
    async with async_session_factory() as session:
        existing = await session.execute(
            select(Article.url).where(Article.url.in_(urls))
        )
        existing_urls = {row[0] for row in existing.all()}
        matcher = await build_ticker_matcher(session)

    new_entries = [e for e in entries if e["url"] not in existing_urls]
    skipped = len(entries) - len(new_entries)

    if not new_entries:
        return {"new": 0, "skipped": skipped, "high_impact": 0}

    # FinBERT batch sentiment (clean text, no HTML)
    texts = [e["title"] + (". " + e["summary"] if e["summary"] else "") for e in new_entries]
    sentiments = await finbert.predict_batch(texts)

    # 32-dim PCA vectors — consumed by forecast-service as `sent_0..sent_31`.
    # If PCA artifact missing, pca_vectors has 768d raw embeddings (caller can still use sent_0).
    try:
        pca_vectors = await finbert.embed_batch(texts)
    except Exception as exc:
        await logger.awarning("pca_embed_failed", error=str(exc), count=len(texts))
        import numpy as _np
        pca_vectors = _np.zeros((len(texts), 32), dtype=_np.float32)

    high_impact_count = 0
    async with async_session_factory() as session:
        for idx, (entry, sentiment) in enumerate(zip(new_entries, sentiments)):
            matched = matcher.match(entry["title"], entry["summary"])

            # Auto-tag from per-ticker feed — covers short/ambiguous tickers
            # (BK, CF, CI, GE, ON, NWS) that the text matcher skips.
            src_ticker = entry.get("source_ticker")
            if src_ticker and not any(t == src_ticker for t, _ in matched):
                inst_id = matcher.get_id(src_ticker)
                if inst_id:
                    matched = list(matched) + [(src_ticker, inst_id)]

            impact = determine_impact(sentiment, matched)
            pca_vec = pca_vectors[idx].tolist() if idx < len(pca_vectors) else None

            article = Article(
                title=entry["title"],
                url=entry["url"],
                source=entry["source"],
                published_at=entry["published_at"],
                summary=entry["summary"],
                sentiment_score=sentiment.score,
                sentiment_label=sentiment.label,
                impact_level=impact,
                is_processed=True,
            )
            session.add(article)
            await session.flush()

            for ticker, inst_id in matched:
                session.add(InstrumentSentiment(
                    article_id=article.id,
                    instrument_id=inst_id,
                    ticker=ticker,
                    sentiment_score=sentiment.score,
                    sentiment_label=sentiment.label,
                    pca_vector=pca_vec,
                ))

            if impact == "high":
                high_impact_count += 1
                event = json.dumps({
                    "article_id": str(article.id),
                    "title": entry["title"],
                    "tickers": [t for t, _ in matched],
                    "sentiment": sentiment.label,
                    "score": sentiment.score,
                })
                await redis_client.publish("news.high_impact", event)

        await session.commit()

    await logger.ainfo(
        "articles_stored", new=len(new_entries), skipped=skipped, high_impact=high_impact_count,
    )
    return {"new": len(new_entries), "skipped": skipped, "high_impact": high_impact_count}


async def update_daily_sentiment() -> None:
    """Aggregate sentiment per ticker per day (last 7 days) into sentiment_daily."""
    cutoff = date.today() - timedelta(days=7)

    async with async_session_factory() as session:
        rows = await session.execute(
            select(
                func.date(Article.published_at).label("pub_date"),
                InstrumentSentiment.ticker,
                InstrumentSentiment.instrument_id,
                func.avg(InstrumentSentiment.sentiment_score).label("avg_sent"),
                func.count().label("cnt"),
                func.sum(func.cast(InstrumentSentiment.sentiment_label == "positive", Integer)).label("pos"),
                func.sum(func.cast(InstrumentSentiment.sentiment_label == "negative", Integer)).label("neg"),
                func.sum(func.cast(InstrumentSentiment.sentiment_label == "neutral", Integer)).label("neu"),
            )
            .join(Article, Article.id == InstrumentSentiment.article_id)
            .where(func.date(Article.published_at) >= cutoff)
            .group_by(func.date(Article.published_at), InstrumentSentiment.ticker, InstrumentSentiment.instrument_id)
        )

        for row in rows.all():
            stmt = pg_insert(SentimentDaily).values(
                instrument_id=row.instrument_id,
                ticker=row.ticker,
                date=row.pub_date,
                avg_sentiment=float(row.avg_sent) if row.avg_sent else None,
                news_count=row.cnt,
                positive_count=row.pos or 0,
                negative_count=row.neg or 0,
                neutral_count=row.neu or 0,
            ).on_conflict_do_update(
                index_elements=["ticker", "date"],
                set_={
                    "avg_sentiment": float(row.avg_sent) if row.avg_sent else None,
                    "news_count": row.cnt,
                    "positive_count": row.pos or 0,
                    "negative_count": row.neg or 0,
                    "neutral_count": row.neu or 0,
                },
            )
            await session.execute(stmt)
        await session.commit()

    await logger.ainfo("daily_sentiment_updated")


async def main() -> None:
    await logger.ainfo("fetch_news_start")

    entries = await fetch_rss_entries()
    stats = await process_and_store(entries)

    try:
        await update_daily_sentiment()
    except Exception as exc:
        await logger.aerror("daily_sentiment_error", error=str(exc))

    await redis_client.aclose()
    await logger.ainfo("fetch_news_complete", **stats)


if __name__ == "__main__":
    asyncio.run(main())
