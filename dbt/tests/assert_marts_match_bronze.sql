-- Réconciliation bronze -> marts.
-- Recompte les courses directement dans la couche bronze, en appliquant les mêmes
-- filtres que le staging et en excluant les zones inconnues comme le fait le mart,
-- sans passer par les modèles dbt. Puis compare avec le total du mart.
-- Le test échoue si l'écart dépasse 0,5 % : jointure qui multiplie des lignes,
-- filtre modifié par erreur, données manquantes...

with expected as (
    select count(*) as n
    from {{ source('bronze', 'yellow_trips') }} t
    join {{ source('bronze', 'taxi_zones') }} z
        on t."PULocationID" = z.locationid
    where t."tpep_pickup_datetime" >= '2024-01-01'
      and t."tpep_pickup_datetime" <  '2024-04-01'
      and t."tpep_dropoff_datetime" > t."tpep_pickup_datetime"
      and datediff('hour', t."tpep_pickup_datetime", t."tpep_dropoff_datetime") < 24
      and t."trip_distance" > 0
      and t."fare_amount" > 0
      and t."total_amount" > 0
      and z.borough not in ('Unknown', 'N/A')
),

actual as (
    select sum(nb_trips) as n
    from {{ ref('mart_demand_by_hour_borough') }}
)

select
    e.n as courses_attendues,
    a.n as courses_dans_le_mart,
    round(100 * abs(a.n - e.n) / nullif(e.n, 0), 3) as ecart_pct
from expected e
cross join actual a
where coalesce(e.n, 0) = 0
   or a.n is null
   or abs(a.n - e.n) > 0.005 * e.n
