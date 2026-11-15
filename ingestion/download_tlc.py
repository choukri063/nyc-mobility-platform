from pathlib import Path
import requests

BASE = "https://d37ci6vzurychx.cloudfront.net"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

FILES = [
    f"{BASE}/trip-data/yellow_tripdata_2024-{m:02d}.parquet" for m in (1, 2, 3)
] + [f"{BASE}/misc/taxi_zone_lookup.csv"]

for url in FILES:
    dest = RAW / url.split("/")[-1]
    if dest.exists():
        print(f"déjà là : {dest.name}")
        continue
    print(f"téléchargement : {dest.name}")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)