FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Render’ın dinlediği PORT değişkenini kullan
EXPOSE 10000

# collectstatic hata verse bile build devam etsin
RUN python manage.py collectstatic --noinput || true

# Gunicorn ile başlat
CMD gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
