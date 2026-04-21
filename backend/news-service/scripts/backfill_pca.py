"""
Backfill: compute FinBERT[CLS]→PCA vectors for existing news.instrument_sentiment rows
that have pca_vector=NULL. Groups by article_id to avoid embedding duplicates.
"""

import asyncio
import os
import sys
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
for _p in [_script_dir.parent.parent, _script_dir.parent]:
    if (_p / "shared").is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
_svc_dir = _script_dir.parent
if str(_svc_dir) not in sys.path:
    sys.path.insert(0, str(_svc_dir))

import structlog
from sqlalchemy import text

from shared.database import async_session_factory
from shared.logging import setup_logging
from services.sentiment import finbert

setup_logging()
logger = structlog.get_logger()

# Batch size for FinBERT forward pass. CPU-only containers OOM at 32+;
# 8 is safe default. Set PCA_BACKFILL_BATCH_SIZE=32 on GPU for 4x throughput.
BATCH_SIZE = int(os.environ.get("PCA_BACKFILL_BATCH_SIZE", "8"))


async def main() -> None:
    # Pull distinct articles that have sentiment rows lacking pca_vector
    async with async_session_factory() as session:
        result = await session.execute(text("""
            SELECT a.id, a.title, COALESCE(a.summary, '') AS summary
            FROM news.articles a
            WHERE a.title IS NOT NULL
              AND EXISTS (
                SELECT 1 FROM news.instrument_sentiment s
                WHERE s.article_id = a.id AND s.pca_vector IS NULL
              )
            ORDER BY a.published_at DESC
        """))
        articles = result.all()

    total = len(articles)
    await logger.ainfo("backfill_pca_start", articles=total)
    if total == 0:
        return

    processed = 0
    for i in range(0, total, BATCH_SIZE):
        batch = articles[i:i + BATCH_SIZE]
        texts = [
            (a.title or "") + (". " + a.summary if a.summary else "")
            for a in batch
        ]
        try:
            vecs = await finbert.embed_batch(texts)
        except Exception as exc:
            await logger.aexception("embed_error", batch_start=i, error=str(exc))
            continue

        # Update all sentiment rows for each article with same vector
        async with async_session_factory() as session:
            for idx, a in enumerate(batch):
                if idx >= len(vecs):
                    continue
                pca_list = [float(x) for x in vecs[idx].tolist()]
                await session.execute(
                    text("""
                        UPDATE news.instrument_sentiment
                        SET pca_vector = :v, updated_at = NOW()
                        WHERE article_id = :aid AND pca_vector IS NULL
                    """),
                    {"v": pca_list, "aid": a.id},
                )
            await session.commit()

        processed += len(batch)
        if processed % 200 == 0 or processed == total:
            await logger.ainfo("backfill_progress", done=processed, total=total)

    await logger.ainfo("backfill_pca_complete", total=total)


if __name__ == "__main__":
    asyncio.run(main())
