select
    t.*,
    datediff('minute', t.pickup_at, t.dropoff_at) as duration_min,
    pu.borough  as pickup_borough,
    pu.zone     as pickup_zone,
    dz.borough  as dropoff_borough,
    dz.zone     as dropoff_zone
from {{ ref('stg_yellow_trips') }} t
left join {{ ref('stg_taxi_zones') }} pu on t.pickup_zone_id  = pu.location_id
left join {{ ref('stg_taxi_zones') }} dz on t.dropoff_zone_id = dz.location_id