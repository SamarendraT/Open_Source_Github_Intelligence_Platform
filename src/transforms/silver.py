from pyspark.sql import functions as F 
from pyspark.sql.window import Window 
from pyspark.sql import DataFrame
from pyspark.sql.types import StructType

GHARCHIVE_EPOCH = "2011-02-12"

def _nested(df: DataFrame, path:str, cast:str | None = None):
    parts = path.split(".", 1)
    top = parts[0]
    if top not in df.columns:
        col = F.lit(None)
    elif len(parts) == 1:
        col = F.col(top)
    elif isinstance(df.schema[top].dataType, StructType):
        col = F.col(path)
    else:
        col = F.get_json_object(F.col(top).cast("string"), "$." + parts[1])
    return col.cast(cast) if cast else col


def flatten_events(df: DataFrame) -> DataFrame:
    created = F.to_timestamp(_nested(df, "created_at"))
    payload = _nested(df, "payload", "string")
    actor_login = _nested(df, "actor.login", "string")
    return df.select(
        _nested(df, "id", "string").alias("event_id"),
        _nested(df, "type", "string").alias("event_type"),
        created.alias("created_at"),
        F.to_date(created).alias("event_date"),
        F.hour(created).alias("event_hour"),
        _nested(df, "actor.id", "bigint").alias("actor_id"),
        actor_login.alias("actor_login"),
        (
            F.coalesce(actor_login.endswith("[bot]"), F.lit(False)) 
            | F.coalesce(F.lower(actor_login).endswith("-bot"), F.lit(False))
        ).alias("is_bot"),
        _nested(df, "repo.id", "bigint").alias("repo_id"),
        _nested(df, "repo.name", "string").alias("repo_name"),
        _nested(df, "org.id", "bigint").alias("org_id"),
        _nested(df, "org.login", "string").alias("org_login"),
        F.get_json_object(payload, "$.action").alias("action"),
        F.get_json_object(payload, "$.size").cast("int").alias("push_size"),
        payload.alias("payload"),
        F.col("_ingest_file"),
        F.col("_ingest_ts"),
)

def tag_quality(df: DataFrame) -> DataFrame:
    tomorrow = F.expr("current_timestamp() + INTERVAL 1 DAY")
    reason = (
        F.when(F.col("event_id").isNull(), "null_event_id")
        .when(F.col("created_at").isNull(), "bad_timestamp")
        .when(F.col("created_at") < F.lit(GHARCHIVE_EPOCH).cast("timestamp"), "bad_timestamp")
        .when(F.col("created_at") > tomorrow, "bad_timestamp")
        .when(F.col("repo_id").isNull(), "null_repo_id")
    )
    return df.withColumn("dq_reason", reason)
    
def dedupe_batch(df: DataFrame) -> DataFrame:
    w = Window.partitionBy("event_id").orderBy(
        F.col("_ingest_ts").asc(), F.col("_ingest_file").asc()
    )
    return (
        df.withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )