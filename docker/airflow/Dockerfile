FROM apache/airflow:2.9.3-python3.12

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*
USER airflow

# DAG runtime dependencies.
# IMPORTANT: Do NOT install sqlalchemy 2.0 — Airflow 2.9 pins SQLAlchemy ~1.4.
# DAGs call microservices via HTTP or use raw psycopg2/Redis directly.
# Heavy ML deps (torch, lightning) are NOT installed here;
# forecast DAG calls forecast-service API via httpx instead.
RUN pip install --no-cache-dir \
    httpx==0.28.1 \
    yfinance==1.2.1 \
    feedparser==6.0.11 \
    "redis[hiredis]==7.4.0" \
    psycopg2-binary==2.9.10 \
    structlog==25.1.0 \
    requests==2.32.3 \
    tenacity==9.1.2 \
    pandas==2.1.4 \
    numpy==1.26.4
