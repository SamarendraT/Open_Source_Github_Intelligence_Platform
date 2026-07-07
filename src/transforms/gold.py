from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F 
from pyspark.sql.window import Window

def build_dim_date(spark: SparkSession, start_date: str, end_date:str) -> DataFrame:
    
    dates = spark.range(1).select(
        F.explode(
            F.sequence(
                F.to_date(F.lit(start_date)),
                F.to_date(F.lit(end_date)),
                F.expr("interval 1 day"),
            )
        ).alias("date")
    )
    
    return dates.select(
            F.date_format("date", "yyyyMMdd").cast("int").alias("date_key"),
            F.col("date"),
            F.year("date").alias("year"),
            F.quarter("date").alias("quarter"),
            F.month("date").alias("month"),
            F.dayofmonth("date").alias("day"),
            F.dayofweek("date").alias("day_of_week"),
            F.date_format("date", "EEEE").alias("day_name"),
            F.dayofweek("date").isin(1, 7).alias("is_weekend"),
        )

def latest_actor_state(events: DataFrame) -> DataFrame:
    w = Window.partitionBy("actor_id").orderBy(F.col("created_at").desc())
    latest = (
        events.filter(F.col("actor_id").isNotNull())
        .withColumn("_rn", F.row_number().over(w))
        .filter("_rn = 1")
        .select("actor_id", "actor_login", "is_bot")
    )
    seen = (
        events.filter(F.col("actor_id").isNotNull())
        .groupBy("actor_id")
        .agg(
            F.min("event_date").alias("first_seen_date"),
            F.max("event_date").alias("last_seen_date")
        )
    )
    return latest.join(seen, "actor_id")

    
def event_type_dim(events: DataFrame) -> DataFrame:
    return events.select("event_type").distinct().filter(F.col("event_type").isNotNull())
    

def latest_repo_state(events: DataFrame) -> DataFrame:
    base = events.filter(F.col("repo_id").isNotNull())
    w = Window.partitionBy("repo_id").orderBy(F.col("created_at").desc())

    latest = (
        base.withColumn("_rn", F.row_number().over(w))
        .filter("_rn = 1")
        .select(
            "repo_id",
            "repo_name",
            F.split("repo_name", "/").getItem(0).alias("owner"),
            F.col("created_at").alias("observed_at"),
        )
    )
    first = base.groupBy("repo_id").agg(F.min("created_at").alias("first_seen_ts"))
    lang = (
        base.filter(F.col("event_type") == "PullRequestEvent")
        .withColumn("language", F.get_json_object("payload", "$.pull_request.base.repo.language"))
        .filter(F.col("language").isNotNull())
        .withColumn("_rn", F.row_number().over(w))
        .filter("_rn = 1")
        .select("repo_id", "language")
    )

    return latest.join(first, "repo_id").join(lang, "repo_id", "left")

def build_fact_events(events: DataFrame) -> DataFrame:
    return events.select(
        "event_id",
        F.date_format("event_date", "yyyyMMdd").cast("int").alias("date_key"),
        "event_type",
        "actor_id",
        "repo_id",
        "event_hour",
        "action",
        "event_date",
    )

def daily_repo_metrics(events: DataFrame) -> DataFrame:
    merged = F.get_json_object("payload", "$.pull_request.merged")
    is_pr = F.col("event_type") == "PullRequestEvent"
    return (
        events.filter(F.col("repo_id").isNotNull())
        .groupBy("repo_id", "event_date")
        .agg(
            F.count("*").alias("events_total"),
            F.sum(F.when(F.col("event_type") == "WatchEvent", 1).otherwise(0)).alias("stars"),
            F.sum(F.when(F.col("event_type") == "ForkEvent", 1).otherwise(0)).alias("forks"),
            F.sum(F.when(F.col("event_type") == "PushEvent", 1).otherwise(0)).alias("pushes"),
            F.coalesce(F.sum(F.when(F.col("event_type") == "PushEvent", F.col("push_size"))), F.lit(0)).alias("commits_pushed"),
            F.sum(F.when(is_pr & (F.col("action") == "opened"), 1).otherwise(0)).alias("prs_opened"),
            F.sum(F.when(is_pr & (F.col("action") == "merged"), 1).otherwise(0)).alias("prs_merged"),
            F.sum(F.when((F.col("event_type") == "IssuesEvent") & (F.col("action") == "opened"), 1).otherwise(0)).alias("issues_opened"),
            F.sum(F.when(F.col("event_type") == "ReleaseEvent",1).otherwise(0)).alias("releases"),
            F.countDistinct("actor_id").alias("unique_actors"),
            F.countDistinct(F.when(~F.col("is_bot"), F.col("actor_id"))).alias("unique_human_actors"),
        )
        .withColumn("date_key", F.date_format("event_date", "yyyyMMdd").cast("int"))
    )

def language_trends(events: DataFrame, dim_repo: DataFrame) -> DataFrame:
    current = (
        dim_repo.filter("is_current = true")
        .select("repo_id", "language")
        .filter(F.col("language").isNotNull())
    )

    joined = events.filter(F.col("repo_id").isNotNull()).join(current, "repo_id")
    per_day = joined.groupBy("event_date", "language").agg(
        F.countDistinct("repo_id").alias("active_repos"),
        F.count("*").alias("events"),
    )
    day_total = Window.partitionBy("event_date")
    return (
        per_day.withColumn("date_key", F.date_format("event_date", "yyyyMMdd").cast("int"))
        .withColumn("share_of_events", F.col("events") / F.sum("events").over(day_total))
    )
    

