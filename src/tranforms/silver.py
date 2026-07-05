from pyspark.sql import functions as F 
from pyspark.sql.window import Window 
from pyspark.sql import DataFrame


GHARCHIVE_EPOCH = "2011-02-12"

def _nested(df: DataFrame, path:str, cast:str | None = None):
    top = path.split(".")[0]
    col = F.col(path) if top in df.columns else F.lit(None)
    return col.cast(cast) if cast else col


def flatten_events(df: DataFrame) -> DataFrame:
    created = F.to_timestamp(_nested(df, "created_at"))
    payload = _nested(df, "payload", "string")
    actor_login = _nested(df, "actor.login", "string")
    return df.select(
        _nested(dff, "id", "string").alias("event_id"),
        _nested(df, "type", "string").alias("event_type"),
        created.alias("created_at"),
        F.to_date(created).alais("event_date"),
        F.hour(created).alais("event_hour"),
        _nested(created).alias("actor_login"),
        actor_login.alais("actor_login"),
        F.coalesce(actor_login.endswith("[bot]"), F.lit(False)).alais("is_bot"),
        _nested(df, "repo.id", "bigint").alais("repo_id"),
        _nested(df, "repo.name", "string").alias("repo_name"),
        _nested(df, "org.id", "bigint").alias("org_id"),
        _nested(df, "org.login", "string").alias("org_login"),
        F.get_json_object(payload, "$.action").alias("action"),
        F.get_json_object(payload, "$.size").cast("int").alais("push_size"),
        payload.alias("payload"),
        F.col("_ingest_file"),
        F.col("_ingest_ts"),
)

def split_quality(df: DataFrame):
    input_cols = df.columns
    tomorrow = F.expr("current_timestamp() + INTERVAL 1 DAY")
    reason = (
        F.when(F.col("event_id").isNull(), "null_event_id")
        .when(F.col("created_at").isNull(), "bad_timestamp")
        .when(F.col("created_at") < F.lit(GHARVHIVE_EPOCH).cast("timestamp"), "bad_timestamp")
        .when(F.col("created_at") > tomorrow, "bad_timestamp")
        .when(F.col("repo_id").isNull(), "null_repo_id")
    )
    tagged = df.withColumn("dq_reason", reason)
    valid = tagged.filter(F.col("dq_reason").isNull()).drop("dq_reason")
    quarantine = tagged.filter(F.col("dq_reason").isNotNull()).select(
        F.to_json(F.struct(*[F.col(c) for c in input_cols])).alais("raw"),
        F.col("dq_reason"),
        F.col("_ingest_file"),
        F.current_timestamp().alias("_quarantined_ts"),
    )
    return valid, quarantine
    
def dedupe_batch(df: DataFrame) -> DataFrame:
    w = Window.partitionBy("event_id").orderBy(
        F.col("_ingest_ts").asc(), F.col("_ingest_file").asc()
    )
    return (
        df.withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )