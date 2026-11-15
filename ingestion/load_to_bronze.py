"""Charge les fichiers du stage RAW_STAGE dans les tables BRONZE de Snowflake.

Relançable sans risque (rechargement complet à chaque exécution) :
- les objets sont créés seulement s'ils n'existent pas ;
- les tables YELLOW_TRIPS et TAXI_ZONES sont vidées puis rechargées depuis le stage,
  ce qui évite tout doublon.
"""
import os

import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

conn = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    password=os.environ["SNOWFLAKE_PASSWORD"],
    role="ACCOUNTADMIN",
)
cur = conn.cursor()

STATEMENTS = [
    # --- Infrastructure ---
    ("Warehouse", """CREATE WAREHOUSE IF NOT EXISTS NYC_WH
                     WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE"""),
    ("Database", "CREATE DATABASE IF NOT EXISTS NYC_MOBILITY"),
    ("Schéma BRONZE", "CREATE SCHEMA IF NOT EXISTS NYC_MOBILITY.BRONZE"),
    ("Schéma SILVER", "CREATE SCHEMA IF NOT EXISTS NYC_MOBILITY.SILVER"),
    ("Schéma GOLD", "CREATE SCHEMA IF NOT EXISTS NYC_MOBILITY.GOLD"),
    ("Utiliser le warehouse", "USE WAREHOUSE NYC_WH"),
    ("Utiliser BRONZE", "USE SCHEMA NYC_MOBILITY.BRONZE"),
    ("Stage", "CREATE STAGE IF NOT EXISTS RAW_STAGE"),
    # --- Formats de fichier ---
    ("Format Parquet", "CREATE OR REPLACE FILE FORMAT PARQUET_FF TYPE = PARQUET USE_LOGICAL_TYPE = TRUE"),
    ("Format CSV", """CREATE OR REPLACE FILE FORMAT CSV_FF
                      TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"'"""),
    # --- Table des courses : colonnes et types déduits du Parquet ---
    ("Table YELLOW_TRIPS", """CREATE TABLE IF NOT EXISTS YELLOW_TRIPS USING TEMPLATE (
                                SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*))
                                FROM TABLE(INFER_SCHEMA(
                                  LOCATION => '@RAW_STAGE',
                                  FILE_FORMAT => 'PARQUET_FF',
                                  FILES => ('yellow_tripdata_2024-01.parquet')
                                ))
                              )"""),
    # Rechargement complet : les fichiers sont renvoyés à chaque exécution (OVERWRITE),
    # Snowflake les considère donc comme nouveaux et les rechargerait en double.
    ("Vider YELLOW_TRIPS", "TRUNCATE TABLE YELLOW_TRIPS"),
    ("COPY INTO YELLOW_TRIPS", """COPY INTO YELLOW_TRIPS
                                  FROM @RAW_STAGE
                                  FILE_FORMAT = (FORMAT_NAME = 'PARQUET_FF')
                                  MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
                                  PATTERN = '.*yellow_tripdata_.*[.]parquet'
                                  FORCE = TRUE"""),
    # --- Table de référence des zones (rechargée entièrement) ---
    ("Table TAXI_ZONES", """CREATE TABLE IF NOT EXISTS TAXI_ZONES (
                              LOCATIONID NUMBER, BOROUGH VARCHAR,
                              ZONE VARCHAR, SERVICE_ZONE VARCHAR)"""),
    ("Vider TAXI_ZONES", "TRUNCATE TABLE TAXI_ZONES"),
    ("COPY INTO TAXI_ZONES", """COPY INTO TAXI_ZONES
                                FROM @RAW_STAGE
                                FILE_FORMAT = (FORMAT_NAME = 'CSV_FF')
                                FILES = ('taxi_zone_lookup.csv')
                                FORCE = TRUE"""),
]

try:
    for label, sql in STATEMENTS:
        print(f"-> {label}")
        cur.execute(sql)
        if label.startswith("COPY"):
            for row in cur.fetchall():
                print("   ", row)

    cur.execute("SELECT COUNT(*) FROM YELLOW_TRIPS")
    print("Lignes dans YELLOW_TRIPS :", cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM TAXI_ZONES")
    print("Lignes dans TAXI_ZONES   :", cur.fetchone()[0])
finally:
    cur.close()
    conn.close()