select
    date_trunc('month', pickup_at)  as month,
    dayname(pickup_at)              as day_of_week,
    hour(pickup_at)                 as hour_of_day,
    pickup_borough,
    count(*)                        as nb_trips,
    round(avg(trip_distance_mi), 2) as avg_distance_mi,
    round(avg(duration_min), 1)     as avg_duration_min,
    round(avg(total_amount), 2)     as avg_total_amount
from {{ ref('int_trips_enriched') }}
where pickup_borough not in ('Unknown', 'N/A')
group by 1, 2, 3, 4