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
    