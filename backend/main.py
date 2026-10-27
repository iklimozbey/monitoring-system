import os
import subprocess
import threading
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import psycopg
from dotenv import load_dotenv
import ipaddress
from pydantic import BaseModel, field_validator

load_dotenv()

# ===================================
# DATABASE CONNECTION HELPER
# ===================================
def get_db(connect_timeout: int | None = None):
    kwargs = {}
    if connect_timeout is not None:
        kwargs["connect_timeout"] = connect_timeout
    return psycopg.connect(
        dbname=os.getenv("DB_NAME", "monitoring_db"),
        user=os.getenv("DB_USER", "monitoring_user"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "database"),
        port=os.getenv("DB_PORT", "5432"),
        **kwargs
    )

# ===================================
# 1. LIFESPAN & BACKGROUND TASK
# ===================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Starts background monitoring task on startup
    task = asyncio.create_task(monitoring_loop())
    try:
        yield
    finally:
        # Gracefully cancel task on shutdown
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="Monitoring System API",
    version="1.0.0",
    description=(
        "Ağ cihazlarını (IP/ping) izleyen sistemin REST API'si.\n\n"
        "**Hata gövdesi:** Tüm hatalar `{\"detail\": ...}` biçimindedir. "
        "Doğrulama hatalarında (`422`) `detail` bir liste, diğerlerinde bir metindir.\n\n"
        "**Kimlik doğrulama:** Şu an yoktur, bu yüzden `401`/`403` dönülmez."
    ),
    openapi_tags=[
        {"name": "Health", "description": "Servis ve veritabanı sağlık kontrolü"},
        {"name": "Devices", "description": "Cihaz CRUD işlemleri"},
        {"name": "Monitoring", "description": "Ping ile durum kontrolü ve geçmiş"},
        {"name": "Dashboard", "description": "Özet istatistikler"},
    ],
    lifespan=lifespan,
)

# ===================================
# 2. CORS SETTINGS
# ===================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow port 3000 and any client
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# ===================================
# 3. MONITORING LOGIC (PING)
# ===================================
def check_device(ip):
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=4
        )
        return "UP" if result.returncode == 0 else "DOWN"
    except (subprocess.TimeoutExpired, OSError):
        return "DOWN"

monitor_lock = threading.Lock()

def monitor_devices():
    if not monitor_lock.acquire(blocking=False):
        return {"message": "Monitoring already running"}

    try:
        with get_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, ip_address, status FROM devices")
                devices = cursor.fetchall()

                for device_id, ip_address, old_status in devices:
                    new_status = check_device(ip_address)

                    if old_status != new_status:
                        # Update device status
                        cursor.execute(
                            "UPDATE devices SET status = %s WHERE id = %s",
                            (new_status, device_id)
                        )

                        # Record to history log
                        cursor.execute(
                            """
                            INSERT INTO monitoring_history (device_id, old_status, new_status)
                            VALUES (%s, %s, %s)
                            """,
                            (device_id, old_status, new_status)
                        )
                        print(f"Device {device_id} ({ip_address}): {old_status} -> {new_status}")
            conn.commit()
        return {"message": "Monitoring completed successfully"}
    except Exception as e:
        print(f"Monitoring error: {e}")
        return {"error": str(e)}
    finally:
        monitor_lock.release()

async def monitoring_loop():
    # Wait 5 seconds on startup for database readiness
    await asyncio.sleep(5)
    while True:
        try:
            await asyncio.to_thread(monitor_devices)
        except Exception as e:
            print("Monitoring loop error: ", e)
        await asyncio.sleep(30)

# ===================================
# 4. PYDANTIC SCHEMAS (IPv4 VALIDATION)
# ===================================
class DeviceCreate(BaseModel):
    name: str
    ip_address: str
    device_type: str

    @field_validator("ip_address")
    @classmethod
    def validate_ipv4(cls, v: str):
        try:
            ip = ipaddress.IPv4Address(v.strip())
            return str(ip)
        except ValueError:
            raise ValueError("Invalid IPv4 address format! Example: 192.168.1.1")

class DeviceUpdate(BaseModel):
    name: str | None = None
    ip_address: str | None = None
    device_type: str | None = None
    status: str | None = None

    @field_validator("ip_address")
    @classmethod
    def validate_ipv4(cls, v: str | None):
        if v is not None:
            try:
                ip = ipaddress.IPv4Address(v.strip())
                return str(ip)
            except ValueError:
                raise ValueError("Invalid IPv4 address format! Example: 192.168.1.1")
        return v

# ===================================
# 4.1 RESPONSE MODELS (OpenAPI)
# ===================================
class DeviceOut(BaseModel):
    id: int
    name: str
    ip_address: str
    device_type: str
    status: str
    created_at: str | None = None
    updated_at: str | None = None

class ErrorResponse(BaseModel):
    detail: str

class MessageResponse(BaseModel):
    message: str
    id: int

class HealthResponse(BaseModel):
    status: str
    database: str

class HistoryOut(BaseModel):
    id: int
    device_id: int
    device_name: str
    old_status: str | None = None
    new_status: str
    changed_at: str | None = None

class DashboardSummary(BaseModel):
    total_devices: int
    up_devices: int
    down_devices: int

# Ortak hata cevapları: Swagger'da her endpoint için görünür
R_404 = {404: {"model": ErrorResponse, "description": "Cihaz bulunamadı",
               "content": {"application/json": {"example": {"detail": "Device not found"}}}}}
R_409 = {409: {"model": ErrorResponse, "description": "Aynı IP adresli cihaz zaten mevcut",
               "content": {"application/json": {"example": {"detail": "A device with this IP address already exists"}}}}}
R_500 = {500: {"model": ErrorResponse, "description": "Beklenmeyen sunucu hatası",
               "content": {"application/json": {"example": {"detail": "Internal server error"}}}}}

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    # Beklenmeyen hatalarda iç ayrıntıyı istemciye vermeden tutarlı {"detail": ...} gövdesi döner
    print(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# ===================================
# 5. API ENDPOINTS
# ===================================

@app.get(
    "/health",
    tags=["Health"],
    summary="Servis ve veritabanı sağlığı",
    response_model=HealthResponse,
    responses={503: {"description": "Veritabanına ulaşılamıyor",
                     "content": {"application/json": {"example": {"status": "unhealthy", "database": "down"}}}}},
)
def health_check():
    # Veritabanına bağlanıp basit bir sorgu çalıştırarak DB'nin ulaşılabilir olduğunu doğrular.
    # 3 sn bağlantı zaman aşımı: DB kapalıyken health isteği asılı kalmaz.
    try:
        with get_db(connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception as e:
        print(f"db_connection_failed: {e}")
        # DB yoksa 200 dönmemeli: Docker healthcheck ve izleme araçları HTTP koduna bakar
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "down"}
        )
    return {"status": "healthy", "database": "up"}

@app.get("/devices", tags=["Devices"], summary="Tüm cihazları listele",
         response_model=list[DeviceOut], responses={**R_500})
def get_devices():
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, ip_address, device_type, status, created_at, updated_at
                FROM devices
                ORDER BY id ASC
                """
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "ip_address": row[2],
                    "device_type": row[3],
                    "status": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "updated_at": row[6].isoformat() if row[6] else None
                }
                for row in rows
            ]

@app.get("/devices/{device_id}", tags=["Devices"], summary="Tek cihazı getir",
         response_model=DeviceOut, responses={**R_404, **R_500})
def get_device(device_id: int):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, ip_address, device_type, status, created_at, updated_at
                FROM devices WHERE id = %s
                """,
                (device_id,)
            )
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Device not found")
            return {
                "id": row[0],
                "name": row[1],
                "ip_address": row[2],
                "device_type": row[3],
                "status": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "updated_at": row[6].isoformat() if row[6] else None
            }

@app.post("/devices", status_code=201, tags=["Devices"], summary="Yeni cihaz oluştur",
          response_model=DeviceOut, responses={**R_409, **R_500})
def create_device(device: DeviceCreate):
    with get_db() as conn:
        with conn.cursor() as cursor:
            # Aynı IP adresine sahip cihaz zaten varsa ekleme
            cursor.execute("SELECT 1 FROM devices WHERE ip_address = %s", (device.ip_address,))
            if cursor.fetchone() is not None:
                raise HTTPException(status_code=409, detail="A device with this IP address already exists")
            cursor.execute(
                """
                INSERT INTO devices (name, ip_address, device_type)
                VALUES (%s, %s, %s)
                RETURNING id, name, ip_address, device_type, status, created_at, updated_at
                """,
                (device.name, device.ip_address, device.device_type)
            )
            row = cursor.fetchone() 
            conn.commit()
            return {
                "id": row[0],
                "name": row[1],
                "ip_address": row[2],
                "device_type": row[3],
                "status": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "updated_at": row[6].isoformat() if row[6] else None
            }

@app.post("/monitor", tags=["Monitoring"], summary="Ping kontrolünü şimdi çalıştır")
@app.get("/monitor", tags=["Monitoring"], summary="Ping kontrolünü şimdi çalıştır")
def run_monitoring():
    return monitor_devices()

@app.patch("/devices/{device_id}", tags=["Devices"], summary="Cihazı kısmen güncelle",
           response_model=DeviceOut,
           responses={400: {"model": ErrorResponse, "description": "Hiç alan gönderilmedi",
                            "content": {"application/json": {"example": {"detail": "No fields provided"}}}},
                      **R_404, **R_409, **R_500})
def update_device(device_id: int, device: DeviceUpdate):
    updates = device.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided")

    if any(value is None for value in updates.values()):
        raise HTTPException(status_code=422, detail="Fields cannot be null")

    if "status" in updates and updates["status"] not in ("UP", "DOWN", "UNKNOWN"):
        raise HTTPException(status_code=422, detail="Status must be UP, DOWN or UNKNOWN")

    fields = [f"{key} = %s" for key in updates.keys()]
    values = list(updates.values())
    values.append(device_id)

    query = f"""
        UPDATE devices
        SET {", ".join(fields)}
        WHERE id = %s
        RETURNING id, name, ip_address, device_type, status, created_at, updated_at
    """

    with get_db() as conn:
        with conn.cursor() as cursor:
            # IP değiştiriliyorsa başka bir cihazda aynı IP olmamalı
            if "ip_address" in updates:
                cursor.execute(
                    "SELECT 1 FROM devices WHERE ip_address = %s AND id <> %s",
                    (updates["ip_address"], device_id)
                )
                if cursor.fetchone() is not None:
                    raise HTTPException(status_code=409, detail="A device with this IP address already exists")
            cursor.execute(query, values)
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Device not found")
            conn.commit()
            return {
                "id": row[0],
                "name": row[1],
                "ip_address": row[2],
                "device_type": row[3],
                "status": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "updated_at": row[6].isoformat() if row[6] else None
            }

@app.delete("/devices/{device_id}", tags=["Devices"], summary="Cihazı sil",
            response_model=MessageResponse, responses={**R_404, **R_500})
def delete_device(device_id: int):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM devices WHERE id = %s RETURNING id", (device_id,))
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Device not found")
            conn.commit()
            return {"message": "Device deleted successfully", "id": row[0]}

@app.get("/monitoring-history", tags=["Monitoring"], summary="Son 50 durum değişikliği",
         response_model=list[HistoryOut], responses={**R_500})
def get_monitoring_history():
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT h.id, h.device_id, d.name AS device_name, h.old_status, h.new_status, h.changed_at
                FROM monitoring_history h
                JOIN devices d ON h.device_id = d.id
                ORDER BY h.changed_at DESC
                LIMIT 50
            """)
            rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "device_id": row[1],
                "device_name": row[2],
                "old_status": row[3],
                "new_status": row[4],
                "changed_at": row[5].isoformat() if row[5] else None
            }
            for row in rows
        ]

@app.get("/dashboard/summary", tags=["Dashboard"], summary="Cihaz sayısı özeti",
         response_model=DashboardSummary, responses={**R_500})
def get_dashboard_summary():
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) AS total_devices,
                    COUNT(*) FILTER (WHERE status = 'UP') AS up_devices,
                    COUNT(*) FILTER (WHERE status = 'DOWN') AS down_devices
                FROM devices
            """)
            result = cursor.fetchone()

        return {
            "total_devices": result[0] if result else 0,
            "up_devices": result[1] if result else 0,
            "down_devices": result[2] if result else 0
        }
