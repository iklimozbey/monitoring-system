-- Devices table schema
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    device_type VARCHAR(50) NOT NULL,
    status VARCHAR(10) DEFAULT 'UNKNOWN',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Monitoring history log table
CREATE TABLE IF NOT EXISTS monitoring_history (
    id SERIAL PRIMARY KEY,
    device_id INT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    old_status VARCHAR(10),
    new_status VARCHAR(10) NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trigger to automatically update updated_at timestamp on record changes
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_devices_updated_at ON devices;
CREATE TRIGGER update_devices_updated_at
    BEFORE UPDATE ON devices
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Seed initial records
INSERT INTO devices (name, ip_address, device_type, status)
VALUES 
    ('Localhost Gateway', '127.0.0.1', 'Server', 'UP'),
    ('Google DNS', '8.8.8.8', 'External DNS', 'UP'),
    ('Offline Test Device', '192.0.2.1', 'Router', 'DOWN')
ON CONFLICT DO NOTHING;
