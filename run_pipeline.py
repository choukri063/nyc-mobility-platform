"""Lance tout le pipeline : téléchargement, stage, bronze, dbt.

Usage (depuis la racine du projet) :
    py -3.14 -m poetry run python run_pipeline.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STEPS = [
    ("1/4 Téléchargement des données TLC", [sys.executable, "ingestion/download_tlc.py"]),
    ("2/4 Envoi des fichiers vers le stage Snowflake", [sys.executable, "ingestion/upload_to_stage.py"]),
    ("3/4 Chargement du stage vers les tables Bronze", [sys.executable, "ingestion/load_to_bronze.py"]),
    # "python -m dbt.cli.main" évite de dépendre du PATH de Windows
    ("4/4 dbt build (modèles + tests)", [sys.executable, "-m", "dbt.cli.main", "build", "--project-dir", "dbt"]),
]


def run(cmd):
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"\n❌ Échec à l'étape : {' '.join(cmd)}")
        sys.exit(result.returncode)


if __name__ == "__main__":
    for label, cmd in STEPS:
        print(f"\n===== {label} =====")
        run(cmd)
    print("\n✅ Pipeline terminé avec succès.")