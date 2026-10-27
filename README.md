# Monitoring System

## Backend Dockerfile (`backend/Dockerfile`)

Dockerfile, backend'in container image'ının nasıl üretileceğini adım adım tarif eder. Her satırın açıklaması dosyanın içinde yorum olarak da bulunur. Özet:

| Satır | Ne yapar? |
|---|---|
| `FROM python:3.12-slim` | Başlangıç noktası olan base image'ı seçer. `slim` sürümü küçüktür. |
| `ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1` | Logların anında görünmesini sağlar, `.pyc` dosyası üretilmesini engeller. |
| `RUN apt-get install ... iputils-ping curl` | `ping` komutunu (cihaz izleme) ve `curl`'ü (healthcheck) kurar. Apt önbelleğini siler. |
| `WORKDIR /app` | Çalışma dizinini `/app` yapar. |
| `COPY requirements.txt .` | Sadece bağımlılık listesini kopyalar. Böylece Docker cache'i kullanılır. |
| `RUN pip install --no-cache-dir -r requirements.txt` | Python bağımlılıklarını kurar. |
| `COPY . .` | Uygulama kodunu image'a kopyalar. `.dockerignore` ile `venv` ve `.env` hariç tutulur. |
| `RUN useradd ...` / `USER appuser` | Uygulamayı root olmayan bir kullanıcıyla çalıştırır. |
| `EXPOSE 8080` | Uygulamanın 8080 portunu dinlediğini belgeler. Portu yayınlamaz. |
| `HEALTHCHECK ... /health` | Docker'ın container sağlığını `/health` ile kontrol etmesini sağlar. |
| `CMD ["uvicorn", "main:app", ...]` | Container başlayınca FastAPI uygulamasını 8080 portunda başlatır. |

`.dockerignore` dosyası, `COPY . .` sırasında `venv/`, `.env` ve `__pycache__` gibi dosyaların image'a girmesini engeller. Böylece secret'lar image'ın içine sızmaz.

### Build ve çalıştırma

```bash
# Image üret
docker build -t monitoring-backend ./backend

# Image'dan container başlat (DB ayarları env ile verilir)
docker run -p 8080:8080 -e DB_HOST=database monitoring-backend

# Tüm sistem
docker compose up --build
```

## Image ile container arasındaki fark

**Image**, uygulamanın çalışması için gereken her şeyin (Python, kütüphaneler, kodumuz) paketlendiği, değişmeyen bir şablondur. Diske yazılmış tarif ve malzeme paketi gibidir. Kendi başına hiçbir şey çalıştırmaz.

**Container**, bu image'dan başlatılmış, çalışan bir örnektir. Aynı image'dan istediğimiz kadar container başlatabiliriz. Her biri kendi süreci, ağı ve geçici dosya sistemi ile izole çalışır. Container silindiğinde içinde oluşan veriler de gider (kalıcı veri için volume kullanılır).

Kısaca: **image = sınıf (class), container = o sınıftan üretilmiş nesne (instance)**. Bu projede `docker build` backend image'ını üretir. `docker compose up` ise bu image'dan `monitoring-backend` container'ını çalıştırır.
