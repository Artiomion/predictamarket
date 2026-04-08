FROM python:3.11-slim

WORKDIR /app

COPY auth-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY auth-service/ /app/

EXPOSE 8001

RUN useradd -m appuser
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
