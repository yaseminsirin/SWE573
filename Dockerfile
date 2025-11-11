# Dockerfile
FROM python:3.10-slim

# Sistem güncelleme ve temel paketler
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Çalışma dizinini oluştur
WORKDIR /app

# Gereksinimleri kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodları kopyala
COPY . .

# Ortam değişkenleri (gereksiz logları engeller)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Portu dışa aç
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Migrate + runserver komutu
CMD bash -c "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"
