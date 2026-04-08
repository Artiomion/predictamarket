FROM python:3.11-slim

WORKDIR /app

# Install system deps for torch
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY news-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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
