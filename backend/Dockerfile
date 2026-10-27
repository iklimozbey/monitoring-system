# Base image: Python 3.12'nin küçültülmüş (slim) Debian sürümü. Image boyutunu düşük tutar.
FROM python:3.12-slim

# Python çıktısını tamponlamaz; loglar `docker logs` içinde anında görünür.
# .pyc dosyaları yazılmaz; image içinde gereksiz dosya oluşmaz.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Sistem paketleri: iputils-ping (monitoring ping komutu için), curl (HEALTHCHECK için).
# --no-install-recommends gereksiz paketleri engeller; son satır apt önbelleğini siler.
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Sonraki komutların çalışacağı dizin. Yoksa oluşturulur.
WORKDIR /app

# Önce yalnızca requirements.txt kopyalanır. Kod değişse bile bu katman cache'ten gelir,
# bağımlılıklar sadece requirements.txt değişince yeniden kurulur (build hızlanır).
COPY requirements.txt .

# Bağımlılıkları kurar. --no-cache-dir pip önbelleğini image'a yazmaz.
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyalar. .dockerignore sayesinde venv, .env, __pycache__ dahil edilmez.
COPY . .

# Güvenlik: uygulamayı root yerine yetkisiz bir kullanıcıyla çalıştırır.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Dokümantasyon amaçlıdır: container 8080 portunu dinler. Port yayını docker-compose'taki `ports` ile yapılır.
EXPOSE 8080

# Docker, container'ın sağlıklı olup olmadığını /health endpoint'ine istek atarak kontrol eder.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Container başlayınca çalışan komut: FastAPI uygulamasını (main.py içindeki `app`) uvicorn ile başlatır.
# 0.0.0.0 dinlemek, container dışından gelen isteklerin kabul edilmesi için gereklidir.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
