"""
DAG: Fetch news from RSS feeds + FinBERT sentiment analysis.
RSS → FinBERT → PostgreSQL articles/sentiment + Redis PUBLISH news.high_impact
Schedule: every 30 min, 24/7 (news breaks any time).
"""

from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "predictamarket",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(minutes=20),
    "email_on_failure": False,
}

with DAG(
    dag_id="dag_fetch_news",
    default_args=default_args,
    description="Fetch RSS news + FinBERT sentiment analysis",
    schedule="*/30 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["news", "sentiment", "frequent"],
) as dag:

    fetch_news = BashOperator(
        task_id="fetch_news",
        bash_command=(
            'curl -sf -X POST http://news-service:8003/api/news/admin/fetch-news '
            '-H "x-internal-key: $INTERNAL_API_KEY"'
        ),
    )
