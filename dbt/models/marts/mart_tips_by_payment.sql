select
    case payment_type
        when 1 then 'Carte'
        when 2 then 'Especes'
        when 3 then 'Sans frais'
        when 4 then 'Litige'
        else 'Autre'
    end                                                          as payment_method,
    count(*)                                                     as nb_trips,
    round(avg(tip_amount), 2)                                    as avg_tip,
    round(100 * sum(tip_amount) / nullif(sum(fare_amount), 0), 1) as tip_pct_of_fare
from {{ ref('int_trips_enriched') }}
group by 1