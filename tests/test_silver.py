from datetime import datetime
from pyspark.sql import functions as F 

from src.transforms.silver import dedupe_batch, flatten_events, tag_quality

_BRONZE_SCHEMA = (
    "id string, type string, "
    "actor struct<id:bigint,login:string>, "
    "repo struct<id:bigint,name:string>, "
    "org struct<id:bigint,login:string>, "
    "payload string, created_at string, "
    "_ingest_file string, _ingest_ts timestamp"
)

def test_flatten_extracts_nested_fields(spark):
    row = ("42", "PushEvent", (5, "alice"), (9, "alice/proj"), None, '{"action":"opened","size":3}', "2026-06-01T12:30:00Z", "file.gz", datetime(2026, 6, 1))
    out = flatten_events(spark.createDataFrame([row], _BRONZE_SCHEMA)).collect()[0]
    assert out.event_id == "42"
    assert out.actor_id == 5
    assert out.repo_name == "alice/proj"
    assert out.event_hour == 12
    assert out.action == "opened"
    assert out.push_size == 3
    assert out.is_bot is False

def test_is_bot_detects_both_conventions(spark):
    rows = [
        ("1", "PushEvent", (1, "dependabot[bot]"), (1, "a/b"), None, "{}", "2026-06-01T00:00:00Z", "f", datetime(2026, 6, 1)),
        ("2", "PushEvent", (2, "oqs-bot"), (1, "a/b"), None, "{}", "2026-06-01T00:00:00Z", "f", datetime(2026, 6, 1)),
        ("3", "PushEvent", (3, "alice"), (1, "a/b"), None, "{}", "2026-06-01T00:00:00Z", "f", datetime(2026, 6, 1)),
    ]
    out = {r.event_id: r.is_bot for r in flatten_events(spark.createDataFrame(rows, _BRONZE_SCHEMA)).collect()}
    assert out["1"] is True
    assert out["2"] is True
    assert out["3"] is False


def _flat(spark, rows):
    schema = "event_id string, created_at timestamp, repo_id bigint, _ingest_file string,_ingest_ts timestamp"
    return spark.createDataFrame(rows, schema)

def test_tag_quality_routes_bad_rows(spark):
    rows = [
        ("ok", datetime(2026, 6, 1, 12), 9, "f", datetime(2026, 6, 1)),
        (None, datetime(2026, 6, 1, 12), 9, "f", datetime(2026, 6, 1)),
        ("future", datetime(3001, 1, 1), 9, "f", datetime(2026, 6, 1)),
        ("norepo", datetime(2026, 6, 1, 12), None, "f", datetime(2026, 6, 1)),
    ]
    reasons = {r.event_id: r.dq_reason for r in tag_quality(_flat(spark, rows)).collect()}
    assert reasons["ok"] is None
    assert reasons[None] == "null_event_id"
    assert reasons["future"] == "bad_timestamp"
    assert reasons["norepo"] == "null_repo_id"

def test_dedupe_keeps_earliest_ingest(spark):
    rows = [
        ("dup", datetime(2026, 6, 1, 12), 9, "file_b.gz", datetime(2026, 6, 1, 2)),
        ("dup", datetime(2026, 6, 1, 12), 9, "file_a.gz", datetime(2026, 6, 1, 1)),
        ("solo", datetime(2026, 6, 1, 12), 9, "file_a.gz", datetime(2026, 6, 1, 1)),
    ]
    out = dedupe_batch(_flat(spark, rows))
    assert out.count() == 2
    assert out.filter(F.col("event_id") == "dup").collect()[0]._ingest_file == "file_a.gz"
