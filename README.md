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

## API Dokümantasyonu (OpenAPI / Swagger)

Backend çalışırken API sözleşmesi otomatik üretilir ve tarayıcıdan denenebilir:

| Adres | Ne sunar? |
|---|---|
| http://localhost:8080/docs | Swagger UI. Endpoint'leri tarayıcıdan dener (**Try it out** → **Execute**) |
| http://localhost:8080/redoc | ReDoc. Okunabilir referans |
| http://localhost:8080/openapi.json | Ham OpenAPI şeması (istemci kodu üretimi için) |

Dokümantasyon [`backend/main.py`](backend/main.py) içindeki endpoint tanımlarından üretilir: etiketler, özetler, response modelleri ve hata örnekleri kodun içindedir.

### Endpoint'ler ve status kodları

| Endpoint | Başarılı | Hatalar |
|---|---|---|
| `GET /health` | `200` | `503` (DB kapalı) |
| `GET /devices` | `200` | `500` |
| `GET /devices/{id}` | `200` | `404`, `422` (id sayı değil) |
| `POST /devices` | `201` | `409` (aynı IP), `422` (geçersiz/eksik alan) |
| `PATCH /devices/{id}` | `200` | `400` (boş gövde), `404`, `409`, `422` |
| `DELETE /devices/{id}` | `200` | `404` |
| `GET /monitoring-history` | `200` | `500` |
| `GET /dashboard/summary` | `200` | `500` |
| `GET`/`POST /monitor` | `200` | `500` |

**Hata gövdesi her zaman `{"detail": ...}` biçimindedir.** `422` hatalarında `detail` bir liste (alan bazlı hatalar), diğerlerinde tek bir metindir. Beklenmeyen hatalarda (`500`) iç ayrıntı istemciye verilmez, yalnızca loga yazılır.

> **Kılavuzdan farklar:**
> - Geçersiz IP için `400` yerine **`422`** dönülür. FastAPI/Pydantic doğrulama hatalarında `422` kullanır ve proje test dokümanı (`TC-02`) da bunu bekler.
> - `401 Unauthorized` ve `403 Forbidden` **dönülmez**, çünkü projede henüz kimlik doğrulama/yetkilendirme yoktur.

### Başarılı response örnekleri

**`POST /devices` → `201 Created`**
```json
// İstek
{"name": "Swagger Test", "ip_address": "192.0.2.50", "device_type": "Server"}

// Cevap
{
  "id": 23,
  "name": "Swagger Test",
  "ip_address": "192.0.2.50",
  "device_type": "Server",
  "status": "UNKNOWN",
  "created_at": "2026-10-27T11:42:24.580836+00:00",
  "updated_at": "2026-10-27T11:42:24.580836+00:00"
}
```

**`GET /devices/1` → `200 OK`**
```json
{
  "id": 1,
  "name": "Localhost",
  "ip_address": "127.0.0.1",
  "device_type": "Server",
  "status": "UP",
  "created_at": "2026-10-19T10:59:46.109493+00:00",
  "updated_at": "2026-10-19T12:30:18.937120+00:00"
}
```

**`PATCH /devices/23` → `200 OK`** (istek: `{"status": "UP"}`)
```json
{"id": 23, "name": "Swagger Test", "ip_address": "192.0.2.50", "device_type": "Server", "status": "UP", "...": "..."}
```

**`DELETE /devices/23` → `200 OK`**
```json
{"message": "Device deleted successfully", "id": 23}
```

**`GET /dashboard/summary` → `200 OK`**
```json
{"total_devices": 6, "up_devices": 2, "down_devices": 4}
```

**`GET /health` → `200 OK`**
```json
{"status": "healthy", "database": "up"}
```

### Hatalı response örnekleri

**`409 Conflict`: aynı IP adresli cihaz var** (`POST /devices`, `PATCH /devices/{id}`)
```json
{"detail": "A device with this IP address already exists"}
```

**`404 Not Found`: cihaz yok** (`GET`, `PATCH`, `DELETE /devices/{id}`)
```json
{"detail": "Device not found"}
```

**`422 Unprocessable Entity`: geçersiz IP** (`POST /devices` ile `"ip_address": "999.1.1.1"`)
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "ip_address"],
      "msg": "Value error, Invalid IPv4 address format! Example: 192.168.1.1",
      "input": "999.1.1.1"
    }
  ]
}
```

**`422 Unprocessable Entity`: eksik alan** (`POST /devices` ile `{"name": "Missing ip"}`)
```json
{
  "detail": [
    {"type": "missing", "loc": ["body", "ip_address"], "msg": "Field required"},
    {"type": "missing", "loc": ["body", "device_type"], "msg": "Field required"}
  ]
}
```

**`422 Unprocessable Entity`: geçersiz status** (`PATCH` ile `{"status": "CORRUPTED"}`)
```json
{"detail": "Status must be UP, DOWN or UNKNOWN"}
```

**`400 Bad Request`: boş gövde** (`PATCH /devices/{id}` ile `{}`)
```json
{"detail": "No fields provided"}
```

**`503 Service Unavailable`: veritabanı kapalı** (`GET /health`)
```json
{"status": "unhealthy", "database": "down"}
```

**`500 Internal Server Error`: beklenmeyen hata** (herhangi bir endpoint)
```json
{"detail": "Internal server error"}
```

### Swagger üzerinden deneme

1. http://localhost:8080/docs adresini açın.
2. Bir endpoint'i genişletin, **Try it out** düğmesine basın, gerekirse gövdeyi/parametreyi düzenleyin ve **Execute** deyin.
3. Aşağıdaki sırayla deneyin:
   1. `GET /health` → `200`
   2. `POST /devices` (örnek IP: `192.0.2.50`) → `201`, cevaptaki `id`'yi not edin
   3. `POST /devices` (aynı IP ile tekrar) → `409`
   4. `GET /devices/{device_id}` (not ettiğiniz id) → `200`, olmayan id (`999999`) → `404`
   5. `PATCH /devices/{device_id}` (`{"status": "UP"}`) → `200`, `{"status": "CORRUPTED"}` → `422`
   6. `DELETE /devices/{device_id}` → `200`, tekrar çalıştırınca `404`

Bu akışı otomatik çalıştırmak için [`tests/api_tests.hurl`](tests/api_tests.hurl) dosyası kullanılabilir: `hurl --test tests/api_tests.hurl`
