import psycopg2

conn = psycopg2.connect("postgresql://postgres:root@localhost:5432/easy_invoice_mgr")
cur = conn.cursor()

sql = """
CREATE TABLE IF NOT EXISTS operation_logs (
    log_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    username VARCHAR(50) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    action_description TEXT NOT NULL,
    target_type VARCHAR(50),
    target_id BIGINT,
    target_name VARCHAR(200),
    event_id BIGINT REFERENCES events(event_id),
    event_name VARCHAR(200),
    detail JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""
cur.execute(sql)
conn.commit()
print("Table created")

indexes = [
    "CREATE INDEX IF NOT EXISTS idx_operation_logs_user ON operation_logs(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_operation_logs_action ON operation_logs(action_type)",
    "CREATE INDEX IF NOT EXISTS idx_operation_logs_target ON operation_logs(target_type, target_id)",
    "CREATE INDEX IF NOT EXISTS idx_operation_logs_event ON operation_logs(event_id)",
    "CREATE INDEX IF NOT EXISTS idx_operation_logs_time ON operation_logs(created_at DESC)",
]
for idx in indexes:
    cur.execute(idx)
    conn.commit()
    print(f"Index: {idx[:60]}...")

cur.execute("SELECT COUNT(*) FROM operation_logs")
print(f"operation_logs table ready. Current rows: {cur.fetchone()[0]}")

cur.close()
conn.close()
print("Migration completed!")
