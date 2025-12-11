# Base image
FROM python:3.11-slim

# Python ayarları
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Sistem kütüphanelerini kur (Pillow ve psycopg2 için gerekli)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Requirements dosyasını kopyala ve bağımlılıkları kur
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını kopyala
COPY . .

# Entrypoint script'ini kopyala ve çalıştırılabilir yap
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Port
EXPOSE 8000

# Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
