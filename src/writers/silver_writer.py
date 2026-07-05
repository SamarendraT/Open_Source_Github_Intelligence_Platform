from src.tranforms.silver import dedupe_batch, flatten_events, split_quality

def make_upsert(catalog: str):

    def upsert_events(microbatch_df, batch_id: int) -> None:
        spark = microbatch_df.sparkSession

        flat = flatten_events(microbatch_df)
        valid, quarantine = split_quality(flat)
        staged = dedupe_batch(valid)

        staged.createOrReplaceTempView("silver_batch")
        spark.sql(
            f"""
            MERGE INTO {catalog}.silver.events AS t
            USING silver_batch AS s
            ON t.events_id = s.events_id
            WHEN NOT MATCHED THEN INSERT *
            """
        )

        quarantine.write.mode("append").saveAsTable(
            f"{catalog}.silver.events_quarantine"
        )

    return upsert_events
    