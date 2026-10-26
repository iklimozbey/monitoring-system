# ==========================================
# 1. API Health Check Test
# ==========================================
GET http://localhost:8080/health
HTTP 200
[Asserts]
jsonpath "$.status" == "healthy"

# ==========================================
# 2. List Devices Test
# ==========================================
GET http://localhost:8080/devices
HTTP 200
[Asserts]
jsonpath "$" count >= 1

# ==========================================
# 3. Create Device and Capture ID (POST)
# ==========================================
POST http://localhost:8080/devices
Content-Type: application/json
{
    "name": "Hurl Test Gateway",
    "ip_address": "127.0.0.1",
    "device_type": "Router"
}
HTTP 201
[Asserts]
jsonpath "$.name" == "Hurl Test Gateway"
jsonpath "$.ip_address" == "127.0.0.1"
jsonpath "$.status" == "UNKNOWN"
[Captures]
new_device_id: jsonpath "$.id"

# ==========================================
# 4. Get Single Device by Captured ID
# ==========================================
GET http://localhost:8080/devices/{{new_device_id}}
HTTP 200
[Asserts]
jsonpath "$.name" == "Hurl Test Gateway"
jsonpath "$.device_type" == "Router"

# ==========================================
# 5. Partial Update Device (PATCH)
# ==========================================
PATCH http://localhost:8080/devices/{{new_device_id}}
Content-Type: application/json
{
    "name": "Updated Hurl Gateway",
    "status": "UP"
}
HTTP 200
[Asserts]
jsonpath "$.name" == "Updated Hurl Gateway"
jsonpath "$.status" == "UP"

# ==========================================
# 6. Delete Device (DELETE)
# ==========================================
DELETE http://localhost:8080/devices/{{new_device_id}}
HTTP 200
[Asserts]
jsonpath "$.id" == {{new_device_id}}
jsonpath "$.message" == "Device deleted successfully"

# ==========================================
# 7. Negative Test: Retrieve Deleted Device (404)
# ==========================================
GET http://localhost:8080/devices/{{new_device_id}}
HTTP 404
[Asserts]
jsonpath "$.detail" == "Device not found"

# ==========================================
# 8. Negative Test: Create with Missing IP (422)
# ==========================================
POST http://localhost:8080/devices
Content-Type: application/json
{
    "name": "Incomplete Device"
}
HTTP 422
