#!/bin/bash

# Herhangi bir komut hata verirse işlemi durdur
set -e

echo "🚀 Entrypoint script started..."

# 1. Veritabanı tablolarını oluştur (Veritabanı yoksa Django burada hata verir, biz de logda görürüz)
echo "Applying database migrations..."
python manage.py migrate

# 2. Statik dosyaları topla
echo "Collecting static files..."
python manage.py collectstatic --noinput

# 3. Uygulamayı başlat
echo "Starting Gunicorn..."
exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
