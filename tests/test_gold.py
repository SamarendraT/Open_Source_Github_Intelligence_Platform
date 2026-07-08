from datetime import date, datetime
from src.transforms.gold import build_dim_date, daily_repo_metrics, latest_repo_state

_EVENT_SCHEMA = (
    "event_id string, event_type string, created_at timestamp, event_date date, "
    "event_hour int, actor_id bigint, actor_login string, is_bot boolean, "
    "repo_id bigint, repo_name string, action string, push_size int, payload string"
)

def _events(spark, rows):
    return spark.createDataFrame(rows, _EVENT_SCHEMA)

def test_dim_date_range_and_weekend(spark):
    d = build_dim_date(spark, "2026-06-01", "2026-06-07")
    assert d.count() == 7
    assert d.filter("date = '2026-06-06'").collect()[0].is_weekend is True
    mon = d.filter("date = '2026-06-01'").collect()[0]
    assert mon.is_weekend is False
    assert mon.date_key == 20260601

def test_daily_metrics_counts_by_type(spark):
    day, ts = date(2026, 6, 1), datetime(2026, 6, 1, 10)
    rows = [
        ("1", "WatchEvent", ts, day, 10, 100, "a", False, 9, "o/r", None, None, "{}"),
        ("2", "WatchEvent", ts, day, 10, 101, "b", False, 9, "o/r", None, None, "{}"),
        ("3", "PushEvent", ts, day, 10, 102, "c", False, 9, "o/r", None, None, "{}"),
        ("4", "PushEvent", ts, day, 10, 103, "bot", True, 9, "o/r", None, None, "{}"),
        ("5", "PullRequestEvent", ts, day, 10, 104, "d", False, 9, "o/r", "opened", None, "{}"),
        ("6", "PullRequestEvent", ts, day, 10, 105, "e", False, 9, "o/r", "merged", None, "{}"),
        ("7", "IssuesEvent", ts, day, 10, 106, "f", False, 9, "o/r", "opened", None, "{}"),
        ("8", "ReleaseEvent", ts, day, 10, 107, "g", False, 9, "o/r", None, None, "{}"),
    ]
    m = daily_repo_metrics(_events(spark, rows)).collect()[0]
    assert m.stars == 2
    assert m.pushes == 2
    assert m.prs_opened == 1
    assert m.prs_merged == 1
    assert m.issues_opened == 1
    assert m.releases == 1
    assert m.unique_actors == 8
    assert m.unique_human_actors == 7

def test_latest_repo_state_latest_name_and_language(spark):
    early, late, day = datetime(2026, 6, 1, 8), datetime(2026, 6, 1, 20), date(2026, 6, 1)
    payload = '{"pull_request":{"base":{"repo":{"language":"Rust"}}}}'
    rows = [
        ("1", "PushEvent", early, day, 8, 1, "a", False, 9, "old-org/tool", None, None, "{}"),
        ("2", "PullRequestEvent", late, day, 20, 1, "a", False, 9, "new-org/tool", "opened", None, payload),
    ]
    s = latest_repo_state(_events(spark, rows)).collect()[0]
    assert s.repo_name == "new-org/tool"
    assert s.owner == "new-org"
    assert s.language == "Rust"
    