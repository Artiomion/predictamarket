FROM python:3.11-slim

WORKDIR /app

COPY portfolio-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY portfolio-service/ /app/

EXPOSE 8005

RUN useradd -m appuser
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]
