select
    "VendorID"                  as vendor_id,
    "tpep_pickup_datetime"      as pickup_at,
    "tpep_dropoff_datetime"     as dropoff_at,
    "passenger_count"           as passenger_count,
    "trip_distance"             as trip_distance_mi,
    "PULocationID"              as pickup_zone_id,
    "DOLocationID"              as dropoff_zone_id,
    "payment_type"              as payment_type,
    "fare_amount"               as fare_amount,
    "tip_amount"                as tip_amount,
    "tolls_amount"              as tolls_amount,
    "total_amount"              as total_amount
from {{ source('bronze', 'yellow_trips') }}
where "tpep_pickup_datetime" >= '2024-01-01'
  and "tpep_pickup_datetime" <  '2024-04-01'
  and "tpep_dropoff_datetime" > "tpep_pickup_datetime"
  and datediff('hour', "tpep_pickup_datetime", "tpep_dropoff_datetime") < 24
  and "trip_distance" > 0
  and "fare_amount" > 0
  and "total_amount" > 0