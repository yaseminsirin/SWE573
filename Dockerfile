# ---- Base image ----
    FROM python:3.10-slim

    # Sistem bağımlılıklarını yükle
    RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
    
    # Çalışma dizini
    WORKDIR /app
    
    # Gereksinimleri yükle
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    
    # Kodları kopyala
    COPY . .
    
    # Ortam değişkenleri
    ENV PYTHONDONTWRITEBYTECODE=1
    ENV PYTHONUNBUFFERED=1
    
    # Render'ın PORT environment variable'ını kullan
    # Render, kendi ortamında $PORT değişkenini 10000 olarak ayarlıyor
    EXPOSE 10000
    
    # Statik dosyaları topla (isteğe bağlı ama iyi olur)
    RUN python manage.py collectstatic --noinput
    
    # Gunicorn ile Django’yu başlat
    # $PORT değişkenini dinle, böylece Render hangi portu verirse orayı kullanır
    CMD gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
    