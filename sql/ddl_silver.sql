CREATE SCHEMA IF NOT EXISTS workspace.silver;


CREATE TABLE IF NOT EXISTS workspace.silver.events (
    event_id STRING NOT NULL,
    event_type STRING,
    created_at TIMESTAMP,
    event_date DATE,
    event_hour INT,
    actor_id BIGINT,
    actor_login STRING,
    is_bot BOOLEAN,
    repo_id BIGINT,
    repo_name STRING,
    org_id BIGINT,
    action STRING,
    push_size INT,
    payload STRING,
    _ingest_file STRING,
    _ingest_ts TIMESTAMP
) PARTITIONED BY (event_date);

CREATE TABLE IF NOT EXISTS workspace.silver.events_quarantine (
    raw STRING,
    dq_reason STRING,
    _ingest_file STRING,
    _quarantined_ts TIMESTAMP
);