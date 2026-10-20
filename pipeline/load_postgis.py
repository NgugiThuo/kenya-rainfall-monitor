"""Load county boundaries and the anomaly table into PostGIS.

Usage:
    python pipeline/load_postgis.py --counties data/kenya_counties.geojson --name-col shapeName
Reads DATABASE_URL from the environment (see .env.example).
"""
import argparse
import os

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--counties", required=True)
    ap.add_argument("--name-col", required=True)
    ap.add_argument("--rainfall", default="data/rainfall_anomalies.csv")
    args = ap.parse_args()

    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))

    counties = gpd.read_file(args.counties).to_crs(4326)[[args.name_col, "geometry"]]
    counties = counties.rename(columns={args.name_col: "county"}).rename_geometry("geom")
    counties.to_postgis("counties", engine, if_exists="replace", index=False)

    rain = pd.read_csv(args.rainfall)
    missing = set(rain["county"]) - set(counties["county"])
    if missing:
        raise SystemExit(f"County names missing from boundaries file: {sorted(missing)}")
    rain.to_sql("rainfall", engine, if_exists="replace", index=False)

    with engine.begin() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS rainfall_ym ON rainfall (year, month)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS rainfall_county ON rainfall (county)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS counties_geom ON counties USING GIST (geom)"))
    print(f"Loaded {len(counties)} counties and {len(rain)} rainfall rows")


if __name__ == "__main__":
    main()
