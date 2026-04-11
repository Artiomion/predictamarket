FROM python:3.11-slim

WORKDIR /app

# Install system deps for torch
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements-base.txt ./requirements-base.txt
COPY news-service/requirements.txt ./requirements-service.txt
RUN pip install --no-cache-dir -r requirements-base.txt && grep -v "requirements-base" requirements-service.txt | pip install --no-cache-dir -r /dev/stdin

# Pre-download FinBERT model (~500MB) at build time so container starts fast
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
    AutoTokenizer.from_pretrained('ProsusAI/finbert'); \
    AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert'); \
    print('FinBERT downloaded')"

COPY shared/ /app/shared/
COPY news-service/ /app/

EXPOSE 8003

RUN useradd -m appuser
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
