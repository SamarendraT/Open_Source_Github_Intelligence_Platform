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
    asser out.is_bot is False

def test_is_bot_detects_both_conventions(spark):
    rows = [
        ("1", "PushEvent", (1, "dependabot[bot]"), (1, "a/b"), None, "{}", "2026-06-01T00:00:00Z", "f", datetime(2026, 6, 1)),
        ("2", "PushEvent", (2, "oqs-bot"), (1, "a/b"), None, "{}", "2026-06-01T00:00:00Z", "f", datetime(2026, 6, 1)),
        
    ]