# 🧪 Monitoring System - Test and Acceptance Criteria Specification

**Project Code:** SE-TRN-001 | v1.1  
**Document Type:** User Acceptance Testing (UAT) & Functional Test Matrix  
**Status:** Approved  

---

## 1. Testing Strategy and Scope
This document specifies the functional testing approach for the 3-tier Monitoring System. Each core feature is verified through:
* **Positive Testing:** Validates that the system functions correctly when provided with expected and valid inputs.
* **Negative Testing:** Validates that the system handles invalid, malformed, or missing inputs gracefully without crashing and produces standardized error responses.
* **Acceptance Criteria:** Explicit pass/fail conditions that determine feature readiness.

---

## 2. Test and Acceptance Matrix

| Test ID | Feature / Module | Test Type | Scenario / Precondition | Expected Behavior | Acceptance Criteria (Pass/Fail Condition) |
|---|---|---|---|---|---|
| **TC-01** | Device Creation | **Positive** | Submit valid payload: `name="Core Switch"`, `ip="192.168.1.10"`, `type="Switch"` | Device is successfully persisted in PostgreSQL and rendered on UI. | HTTP `201 Created` returned. Unique `id` generated. Initial status set to `UNKNOWN`. |
| **TC-02** | Device Creation | **Negative** | Submit payload with missing `ip_address` field | Request is rejected immediately; database transaction is not initiated. | HTTP `422 Unprocessable Entity` returned. Meaningful validation error returned in response body. |
| **TC-03** | Device Listing | **Positive** | Issue `GET /devices` when database contains active records | All persisted device entities are retrieved. | HTTP `200 OK` returned. Response is an array of JSON objects matching the schema. |
| **TC-04** | Single Device Retrieval | **Negative** | Request non-existent device ID (e.g., `GET /devices/99999`) | System indicates entity cannot be found. | HTTP `404 Not Found` returned with `{"detail": "Device not found"}`. |
| **TC-05** | Partial Update (PATCH) | **Positive** | Modify device name to `"Primary Node"` for existing device | Specified field is updated without altering unmentioned fields. | HTTP `200 OK` returned. PostgreSQL trigger fires; `updated_at > created_at`. |
| **TC-06** | Partial Update (PATCH) | **Negative** | Attempt updating status to an illegal value (`status: "CORRUPTED"`) | Update is blocked; existing database state is preserved. | HTTP `422 Unprocessable Entity` returned with message: `Status must be UP, DOWN or UNKNOWN`. |
| **TC-07** | Device Deletion | **Positive** | Trigger delete action on an existing device ID | Device is removed from table; related history records are purged. | HTTP `200 OK` returned. `ON DELETE CASCADE` cleans up `monitoring_history`. |
| **TC-08** | Device Deletion | **Negative** | Trigger delete action on an already deleted device ID | Backend handles idempotent deletion gracefully without internal error. | HTTP `404 Not Found` returned. Service stability maintained (no 500 error). |
| **TC-09** | Health / Availability Check | **Positive** | Reachable target (`127.0.0.1`) processed in monitoring loop | ICMP ping returns exit code 0; device marked operational. | Device status updated to `'UP'`. State change timestamped in `monitoring_history`. |
| **TC-10** | Health / Availability Check | **Negative** | Unreachable target (`192.0.2.1`) processed in monitoring loop | ICMP ping times out; device marked non-operational. | Device status updated to `'DOWN'`. Execution thread is non-blocking (`asyncio.to_thread`). |
| **TC-11** | UI Real-Time Refresh | **Positive** | Observe web dashboard without manual browser refresh (F5) | Polling interval updates DOM elements automatically. | JavaScript `setInterval(..., 10000)` polls API every 10s. Counters and status colors refresh. |
| **TC-12** | Backend Failure Resilience | **Negative** | Trigger frontend action while backend container is halted | Frontend remains responsive; informs user of network loss. | Browser catches `TypeError: Failed to fetch`. Alert displays: `"Could not connect to backend!"`. |

---

## 3. Automated Test Execution Evidence (Hurl)
The following automated suite (`tests/api_tests.hurl`) validates TC-01 through TC-08:
* **Framework:** Hurl 8.0.0 (libcurl-powered)
* **Execution Result:** `8 requests succeeded (100% Pass Rate)`
* **Average Latency:** `< 200 ms`
* **Artifact Generated:** `tests/report/index.html` (Automated HTML Test Report)