#!/bin/bash
set -e  # Hata oluşursa işlemi durdur

echo "Waiting for database to be ready..."

# Veritabanı bağlantısını kontrol etmek için Python script'i
check_db_connection() {
  python3 << EOF
import sys
import os
import psycopg2
from urllib.parse import urlparse

# DATABASE_URL varsa onu kullan, yoksa ayrı değişkenlerden oluştur
database_url = os.environ.get("DATABASE_URL")

if database_url:
    # DATABASE_URL'den parse et
    url = urlparse(database_url)
    dbname = url.path[1:] if url.path.startswith('/') else url.path
    user = url.username
    password = url.password
    host = url.hostname
    port = url.port or 5432
else:
    # Docker Compose için ayrı değişkenlerden oluştur
    dbname = os.environ.get("POSTGRES_DB", "hive_db")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    host = os.environ.get("DB_HOST", "db")
    port = int(os.environ.get("DB_PORT", "5432"))

try:
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
        connect_timeout=5
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
EOF
}

# Veritabanı hazır olana kadar bekle
until check_db_connection; do
  echo "Database is unavailable - sleeping"
  sleep 1
done

echo "Database is ready!"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn server..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${GUNICORN_WORKERS:-4} \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    --access-logfile - \
    --error-logfile - \
    --log-level ${LOG_LEVEL:-info}

