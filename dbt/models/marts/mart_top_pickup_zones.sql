select
    pickup_borough,
    pickup_zone,
    count(*)                    as nb_trips,
    round(sum(total_amount), 0) as total_revenue,
    round(avg(total_amount), 2) as avg_total_amount
from {{ ref('int_trips_enriched') }}
where pickup_borough not in ('Unknown', 'N/A')
group by 1, 2