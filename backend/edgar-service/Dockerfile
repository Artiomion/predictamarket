FROM python:3.11-slim

WORKDIR /app

COPY edgar-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY edgar-service/ /app/

EXPOSE 8007

RUN useradd -m appuser
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8007"]
