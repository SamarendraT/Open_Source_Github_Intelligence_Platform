from src.transforms.silver import dedupe_batch, flatten_events, tag_quality
from pyspark.sql import functions as F
def make_upsert(catalog: str):

    def upsert_events(microbatch_df, batch_id: int) -> None:
        spark = microbatch_df.sparkSession
        staging = f"{catalog}.silver._batch_staging"

        tagged = tag_quality(flatten_events(microbatch_df))
        tagged.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(staging)

        staged_tbl = spark.table(staging)

        valid = dedupe_batch(staged_tbl.filter("dq_reason IS NULL").drop("dq_reason"))
        valid.createOrReplaceTempView("silver_batch")
        spark.sql(
            f"""
            MERGE INTO {catalog}.silver.events AS t
            USING silver_batch AS s
            ON t.event_id = s.event_id
            WHEN NOT MATCHED THEN INSERT *
            """
        )

        bad = staged_tbl.filter("dq_reason IS NOT NULL")
        data_cols = [c for c in bad.columns if c != "dq_reason"]
        (
            bad.select(
                F.to_json(F.struct(*[F.col(c) for c in data_cols])).alias("raw"),
                F.col("dq_reason"),
                F.col("_ingest_file"),
                F.current_timestamp().alias("_quarantined_ts"),
            )
            .write.mode("append")
            .saveAsTable(f"{catalog}.silver.events_quarantine")
        )
    return upsert_events
    