FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements-base.txt ./requirements-base.txt
COPY forecast-service/requirements.txt ./requirements-service.txt
RUN pip install --no-cache-dir -r requirements-base.txt \
    && grep -v "requirements-base" requirements-service.txt | pip install --no-cache-dir -r /dev/stdin

# Pre-download FinBERT model at build time
RUN python -c "from transformers import AutoTokenizer, AutoModel; \
    AutoTokenizer.from_pretrained('ProsusAI/finbert'); \
    AutoModel.from_pretrained('ProsusAI/finbert'); \
    print('FinBERT downloaded')"

COPY shared/ /app/shared/
COPY forecast-service/ /app/

# Model artifacts are mounted as a volume
VOLUME /models

ENV MODELS_DIR=/models

EXPOSE 8004

RUN useradd -m appuser
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
