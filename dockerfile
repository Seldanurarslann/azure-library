# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Bağımlılıklar
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn==21.2.0

# Uygulama dosyaları
COPY app.py ./
COPY templates ./templates

# Non-root kullanıcı ve yazma izni ( .flask_secret_key burada oluşturulacak )
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

# Uygulama portu
ENV PORT=80
EXPOSE 80

# --preload: app bir kez import edilir; .flask_secret_key tek seferde oluşturulur
CMD exec gunicorn --preload \
    --workers=${GUNICORN_WORKERS:-2} --threads=${GUNICORN_THREADS:-4} \
    --bind 0.0.0.0:${PORT} --timeout 60 app:app
