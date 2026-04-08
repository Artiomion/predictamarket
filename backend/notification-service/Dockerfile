FROM python:3.11-slim

WORKDIR /app

COPY notification-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY notification-service/ /app/

EXPOSE 8006

RUN useradd -m appuser
USER appuser

CMD ["uvicorn", "main:socket_app", "--host", "0.0.0.0", "--port", "8006"]
