import os
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv

load_dotenv()
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

conn = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    password=os.environ["SNOWFLAKE_PASSWORD"],
    role="ACCOUNTADMIN",
    warehouse="NYC_WH",
    database="NYC_MOBILITY",
    schema="BRONZE",
)
cur = conn.cursor()

# Idempotent : le stage est créé s'il n'existe pas encore
cur.execute("CREATE STAGE IF NOT EXISTS RAW_STAGE")

files = sorted(RAW.glob("yellow_tripdata_2024-0[1-3].parquet")) + [RAW / "taxi_zone_lookup.csv"]

try:
    for f in files:
        print("envoi :", f.name)
        cur.execute(f"PUT 'file://{f.as_posix()}' @RAW_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE")
        print(cur.fetchall())

    cur.execute("LIST @RAW_STAGE")
    for row in cur.fetchall():
        print(row[0], row[1])
finally:
    cur.close()
    conn.close()