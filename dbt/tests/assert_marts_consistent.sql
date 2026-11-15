-- Cohérence interne des marts.
-- 1. La demande par heure et le top des zones excluent les mêmes zones inconnues :
--    leurs totaux de courses doivent être identiques.
-- 2. Les pourboires couvrent toutes les courses : leur total doit égaler
--    le nombre de lignes de la couche intermédiaire.

with demand as (
    select sum(nb_trips) as n from {{ ref('mart_demand_by_hour_borough') }}
),

zones as (
    select sum(nb_trips) as n from {{ ref('mart_top_pickup_zones') }}
),

tips as (
    select sum(nb_trips) as n from {{ ref('mart_tips_by_payment') }}
),

trips as (
    select count(*) as n from {{ ref('int_trips_enriched') }}
)

select
    demand.n as total_demande,
    zones.n  as total_zones,
    tips.n   as total_pourboires,
    trips.n  as total_intermediaire
from demand
cross join zones
cross join tips
cross join trips
where demand.n <> zones.n
   or tips.n <> trips.n
