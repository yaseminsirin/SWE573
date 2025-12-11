#!/bin/bash

# Hata olursa dur
set -e

echo "Running entrypoint script..."

# Veritabanı URL var mı kontrol et (Sadece varlığını kontrol et, bağlanmayı değil)
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable is missing!"
    exit 1
fi

echo "DATABASE_URL found. Starting migrations..."

# Direkt migrate yap. Eğer veritabanı yoksa Django burada hata verir ve biz de loglarda görürüz.
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
