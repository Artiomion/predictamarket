FROM python:3.11-slim

WORKDIR /app

COPY requirements-base.txt ./requirements-base.txt
COPY market-data-service/requirements.txt ./requirements-service.txt
RUN pip install --no-cache-dir -r requirements-base.txt && grep -v "requirements-base" requirements-service.txt | pip install --no-cache-dir -r /dev/stdin

COPY shared/ /app/shared/
COPY market-data-service/ /app/

EXPOSE 8002

RUN useradd -m appuser
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
