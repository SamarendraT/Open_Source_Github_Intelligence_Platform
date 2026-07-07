import pytest
from pyspark.sql import SparkSession

@pytest.fixture(scope="session")
def spark():
    session = (
        SparkSession.builder.master("local[1]")
        .appname("gh-intel-tests")
        .config("spark.sql.shuffle.partitions","1")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield session
    session.stop()