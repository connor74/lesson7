import datetime
import pyspark.sql.functions as F
from pyspark.sql.window import Window
 
def input_event_paths(date, depth):
    dt = datetime.datetime.strptime(date, '%Y-%m-%d')
    return [f"/user/dbt8181/data/events/date={(dt-datetime.timedelta(days=x)).strftime('%Y-%m-%d')}" for x in range(depth)]
 
def tag_tops(date, depth, spark):
    message_paths = input_event_paths(date, depth)
    result = spark.read \
        .option("basePath", "/user/dbt8181/data/events")\
        .parquet(*message_paths)\
        .where("event_type = 'message'")\
        .where("event.message_channel_to is not null")\
        .select(
            F.col("event.message_id").alias("message_id"),
            F.col("event.message_from").alias("user_id"),
            F.explode(F.col("event.tags")).alias("tag")
        )\
        .groupBy("user_id", "tag")\
        .agg(F.count("*").alias("tag_count"))\
        .withColumn("rank", F.row_number().over(Window.partitionBy("user_id")\
        .orderBy(F.desc("tag_count"), F.desc("tag"))))\
        .where("rank <= 3")\
        .groupBy("user_id")\
        .pivot("rank", [1, 2, 3])\
        .agg(F.first("tag"))\
        .withColumnRenamed("1", "tag_top_1")\
        .withColumnRenamed("2", "tag_top_2")\
        .withColumnRenamed("3", "tag_top_3")
 
    return result

tag_tops('2022-06-04', 5, spark).repartition(1).write.parquet('/user/dbt8181/data/tmp/tag_tops_06_04_5')
tag_tops('2022-05-04', 5, spark).repartition(1).write.parquet('/user/dbt8181/data/tmp/tag_tops_05_04_5')
tag_tops('2022-05-04', 1, spark).repartition(1).write.parquet('/user/dbt8181/data/tmp/tag_tops_05_04_1')
