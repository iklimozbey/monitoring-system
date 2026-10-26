FROM python:3.12-slim

# Ping komutunun çalışması için gerekli sistem paketini kur
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Bağımlılıkları kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend kodlarını kopyala
COPY . .

ENV PYTHONUNBUFFERED=1

# Kılavuzun istediği 8080 portunu aç
EXPOSE 8080

# Uygulamayı 8080 portunda başlat
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]