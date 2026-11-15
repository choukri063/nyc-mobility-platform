# NYC Mobility Platform

Pipeline de données de bout en bout sur les courses de taxis jaunes de New York (NYC TLC, janvier à mars 2024) : ingestion, stockage dans Snowflake, transformations avec dbt, contrôles qualité et dashboard Streamlit.

## Architecture

```
NYC TLC (fichiers Parquet + CSV)
        |  Python : téléchargement
        v
Stage Snowflake (RAW_STAGE)
        |  COPY INTO
        v
BRONZE     données brutes          YELLOW_TRIPS, TAXI_ZONES
        |  dbt
        v
STAGING    nettoyage, renommage    stg_yellow_trips, stg_taxi_zones
        v
INTERMEDIATE  jointure avec les zones   int_trips_enriched
        v
MARTS      tables d'analyse        mart_demand_by_hour_borough
                                   mart_top_pickup_zones
                                   mart_tips_by_payment
        |
        v
Dashboard Streamlit
```

| Couche | Rôle | Où |
|---|---|---|
| Bronze | Données brutes, telles que reçues | `NYC_MOBILITY.BRONZE` |
| Staging | Typage, renommage, filtre des courses incohérentes | `NYC_MOBILITY.DBT_DEV` (vues) |
| Intermediate | Courses enrichies avec quartier et zone | `NYC_MOBILITY.DBT_DEV` (vue) |
| Marts | Agrégats prêts pour l'analyse | `NYC_MOBILITY.DBT_DEV` (tables) |

## Technologies

Python 3.12, Poetry, Snowflake, dbt-snowflake, Streamlit, Plotly.

## Prérequis

- Un compte Snowflake (l'essai gratuit suffit) avec le rôle `ACCOUNTADMIN`
- Python 3.12 et Poetry

## Installation

```powershell
py -3.14 -m poetry install
```

Crée un fichier `.env` à la racine du projet (ne jamais le publier) :

```
SNOWFLAKE_ACCOUNT=votre_identifiant_de_compte
SNOWFLAKE_USER=votre_utilisateur
SNOWFLAKE_PASSWORD=votre_mot_de_passe
```

Crée le profil dbt dans `~/.dbt/profiles.yml` :

```yaml
nyc_mobility:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: votre_identifiant_de_compte
      user: votre_utilisateur
      password: votre_mot_de_passe
      role: ACCOUNTADMIN
      warehouse: NYC_WH
      database: NYC_MOBILITY
      schema: DBT_DEV
      threads: 4
```

## Lancer le pipeline

Une seule commande enchaîne les quatre étapes :

```powershell
py -3.14 -m poetry run python run_pipeline.py
```

| Étape | Script | Action |
|---|---|---|
| 1 | `ingestion/download_tlc.py` | Télécharge les fichiers TLC dans `data/raw` |
| 2 | `ingestion/upload_to_stage.py` | Envoie les fichiers vers le stage Snowflake |
| 3 | `ingestion/load_to_bronze.py` | Crée l'infrastructure et charge les tables Bronze |
| 4 | `dbt build` | Exécute les modèles et les tests |

Chaque exécution est un rechargement complet : les tables Bronze sont vidées puis rechargées, ce qui évite les doublons.

## Dashboard

```powershell
py -3.14 -m poetry run streamlit run dashboard\app.py
```

Quatre onglets : vue d'ensemble, analyse temporelle, zones, pourboires. Les filtres de la barre latérale portent sur les quartiers et les mois.

## Qualité des données

Le pipeline exécute 13 tests dbt.

| Type | Test | Objectif |
|---|---|---|
| Staging | `unique`, `not_null` sur `location_id` | Zones sans doublon |
| Staging | `not_null` sur `pickup_at`, `pickup_zone_id`, `total_amount` | Champs essentiels présents |
| Staging | `accepted_values` sur `payment_type` | Codes de paiement valides |
| Marts | `not_null` sur zone et nombre de courses ; `unique`, `not_null` sur le mode de paiement | Tables d'analyse cohérentes |
| Réconciliation | `assert_bronze_matches_stage` | Le nombre de lignes de Bronze égale celui des fichiers sources |
| Réconciliation | `assert_marts_match_bronze` | Les marts correspondent à un recomptage indépendant depuis Bronze (tolérance 0,5 %) |
| Cohérence | `assert_marts_consistent` | Les marts sont cohérents entre eux |

Documentation et graphe de lignage dbt :

```powershell
py -3.14 -m poetry run dbt docs generate --project-dir dbt
py -3.14 -m poetry run dbt docs serve --project-dir dbt
```

## Règles de nettoyage (staging)

Une course est conservée si :

- sa prise en charge a lieu entre le 1er janvier et le 31 mars 2024 ;
- la dépose est postérieure à la prise en charge, et la durée est inférieure à 24 h ;
- la distance, le tarif et le montant total sont strictement positifs.

Environ 96 % des lignes sont conservées. Les zones sans quartier (`Unknown`, `N/A`) sont exclues des marts.

## Limites connues

- Les pourboires en espèces ne sont pas enregistrés par les taximètres : ils valent 0 dans les données et ne sont pas comparables aux paiements par carte.
- Le revenu par mois affiché dans le dashboard est estimé à partir des paniers moyens arrondis.
- Les tables Silver et Gold du dossier `snowflake/` sont le prototype SQL initial. La version de référence est celle de dbt, dans le schéma `DBT_DEV`.

## Structure du projet

```
NYC_MOBILITY/
|-- run_pipeline.py          orchestration des 4 étapes
|-- pyproject.toml           dépendances (Poetry)
|-- ingestion/               téléchargement, envoi vers le stage, chargement Bronze
|-- dbt/                     modèles, tests, sources
|   |-- models/staging
|   |-- models/intermediate
|   |-- models/marts
|   `-- tests/               tests de réconciliation
|-- dashboard/app.py         application Streamlit
|-- snowflake/               scripts SQL d'infrastructure et prototype
|-- data/raw/                fichiers téléchargés (non versionnés)
`-- .env                     identifiants (non versionnés)
```
