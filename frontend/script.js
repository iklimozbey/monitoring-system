const API_URL = "/api";

// ===================================
// 1. GET - List Devices
// ===================================
async function loadDevices() {
    try {
        const response = await fetch(`${API_URL}/devices`);
        if (!response.ok) {
            throw new Error("Failed to load devices");
        }

        const devices = await response.json();
        const table = document.getElementById("device-table");
        if (!table) return;
        
        table.innerHTML = "";

        devices.forEach(device => {
            const row = document.createElement("tr");

            // ID
            const idCell = document.createElement("td");
            idCell.textContent = device.id;

            // Name
            const nameCell = document.createElement("td");
            nameCell.textContent = device.name;

            // IP
            const ipCell = document.createElement("td");
            ipCell.textContent = device.ip_address;

            // Status
            const statusCell = document.createElement("td");
            const statusText = document.createElement("span");
            statusText.textContent = device.status || "UNKNOWN";
            statusText.style.fontWeight = "bold";
            statusText.style.color = device.status === "UP" ? "green" : (device.status === "DOWN" ? "red" : "gray");
            statusCell.appendChild(statusText);

            // Edit Button (Opens Modal)
            const editCell = document.createElement("td");
            const editButton = document.createElement("button");
            editButton.className = "edit-btn";
            editButton.textContent = "Edit";
            editButton.addEventListener("click", () => openEditModal(device));
            editCell.appendChild(editButton);

            // Delete Button (Opens Modal)
            const deleteCell = document.createElement("td");
            const deleteButton = document.createElement("button");
            deleteButton.className = "delete-btn";
            deleteButton.textContent = "Delete";
            deleteButton.addEventListener("click", () => openDeleteModal(device.id, device.name));
            deleteCell.appendChild(deleteButton);

            row.appendChild(idCell);
            row.appendChild(nameCell);
            row.appendChild(ipCell);
            row.appendChild(statusCell);
            row.appendChild(editCell);
            row.appendChild(deleteCell);

            table.appendChild(row);
        });

    } catch (error) {
        console.error("Error loading devices:", error);
    }
}

// ===================================
// 2. POST - Add New Device
// ===================================
const addForm = document.getElementById("add-device-form");
if (addForm) {
    addForm.addEventListener("submit", async function(event) {
        event.preventDefault();

        const name = document.getElementById("device-name").value.trim();
        const ip_address = document.getElementById("device-ip").value.trim();
        const device_type = document.getElementById("device-type").value.trim();

        try {
            const response = await fetch(`${API_URL}/devices`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, ip_address, device_type })
            });

            if (response.ok) {
                alert("Device added successfully!");
                document.getElementById("add-device-form").reset();
                refreshAll();
            } else {
                const error = await response.json();
                let errorMsg = "Failed to add device!";

                if (Array.isArray(error.detail)) {
                    errorMsg = error.detail.map(err => err.msg.replace("Value error, ", "")).join("\n");
                } else if (typeof error.detail === "string") {
                    errorMsg = error.detail;
                }

                alert("⚠️ Error: " + errorMsg);
            }
        } catch (error) {
            console.error("Error adding device:", error);
            alert("Could not connect to backend!");
        }
    }); 
}

// ===================================
// 3. EDIT DEVICE (HTML Modal Implementation)
// ===================================
function openEditModal(device) {
    document.getElementById("edit-device-id").value = device.id;
    document.getElementById("edit-device-name").value = device.name;
    document.getElementById("edit-device-ip").value = device.ip_address;
    document.getElementById("edit-device-type").value = device.device_type || "";
    document.getElementById("edit-modal").style.display = "flex";
}

function closeEditModal() {
    document.getElementById("edit-modal").style.display = "none";
}

async function saveDeviceEdit() {
    const id = document.getElementById("edit-device-id").value;
    const name = document.getElementById("edit-device-name").value.trim();
    const ip_address = document.getElementById("edit-device-ip").value.trim();
    const device_type = document.getElementById("edit-device-type").value.trim();

    try {
        const updateResponse = await fetch(`${API_URL}/devices/${id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, ip_address, device_type })
        });

        if (!updateResponse.ok) {
            const error = await updateResponse.json();
            let errorMsg = "Failed to update device!";
            if (Array.isArray(error.detail)) {
                errorMsg = error.detail.map(err => err.msg.replace("Value error, ", "")).join("\n");
            } else if (typeof error.detail === "string") {
                errorMsg = error.detail;
            }
            alert("⚠️ Error: " + errorMsg);
            return;
        }

        closeEditModal();
        alert("Device updated successfully!");
        refreshAll();

    } catch (error) {
        console.error("Error updating device:", error);
        alert("Error updating device");
    }
}

// ===================================
// 4. DELETE DEVICE (HTML Modal Implementation)
// ===================================
function openDeleteModal(id, name) {
    document.getElementById("delete-device-id").value = id;
    document.getElementById("delete-modal-text").textContent = `Are you sure you want to delete "${name}" (ID: ${id})?`;
    document.getElementById("delete-modal").style.display = "flex";
}

function closeDeleteModal() {
    document.getElementById("delete-modal").style.display = "none";
}

async function confirmDeviceDelete() {
    const id = document.getElementById("delete-device-id").value;
    try {
        const response = await fetch(`${API_URL}/devices/${id}`, { method: "DELETE" });

        if (response.ok) {
            closeDeleteModal();
            alert("Device deleted successfully!");
            refreshAll();
        } else {
            const error = await response.text();
            alert("Failed to delete device: " + error);
        }
    } catch (error) {
        console.error("Error deleting device:", error);
        alert("Could not connect to backend!");
    }
}

// ===================================
// 5. GET - Dashboard Summary
// ===================================
async function loadDashboardSummary() {
    try {
        const response = await fetch(`${API_URL}/dashboard/summary`);
        if (!response.ok) throw new Error("Failed to fetch dashboard summary");

        const data = await response.json();
        const totalEl = document.getElementById("totalDevices");
        const upEl = document.getElementById("upDevices");
        const downEl = document.getElementById("downDevices");

        if (totalEl) totalEl.textContent = data.total_devices;
        if (upEl) upEl.textContent = data.up_devices;
        if (downEl) downEl.textContent = data.down_devices;

    } catch (error) {
        console.error("Dashboard summary error:", error);
    }
}

// ===================================
// 6. GET - Monitoring History
// ===================================
async function loadMonitoringHistory() {
    try {
        const response = await fetch(`${API_URL}/monitoring-history`);
        if (!response.ok) throw new Error("Failed to fetch monitoring history");

        const history = await response.json();
        const tableBody = document.getElementById("historyTableBody");
        if (!tableBody) return;

        tableBody.innerHTML = "";

        history.forEach(record => {
            const row = document.createElement("tr");
            const values = [
                record.device_name,
                record.old_status ?? "-",
                record.new_status,
                record.changed_at ? new Date(record.changed_at).toLocaleString("en-US") : "-"
            ];

            values.forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });

    } catch (error) {
        console.error("Monitoring history error:", error);
    }
}

// ===================================
// 7. Page Load & Polling Interval
// ===================================
function refreshAll() {
    loadDevices();
    loadDashboardSummary();
    loadMonitoringHistory();
}

window.addEventListener("DOMContentLoaded", () => {
    refreshAll();
    setInterval(refreshAll, 10000); // Poll every 10 seconds
});
