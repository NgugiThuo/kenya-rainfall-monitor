"""Fetch monthly CHIRPS rainfall totals per county from Google Earth Engine.

Usage:
    earthengine authenticate          # once
    python pipeline/fetch_chirps.py --counties data/kenya_counties.geojson \
        --name-col shapeName --project YOUR_GEE_PROJECT

Writes data/monthly_rainfall.csv with columns: county, year, month, rain_mm.
If the file already exists, new rows are merged in, so the same command can
be re-run monthly to refresh the data.
"""
import argparse
import datetime as dt
from pathlib import Path

import ee
import geopandas as gpd
import pandas as pd

CHIRPS = "UCSB-CHG/CHIRPS/DAILY"  # daily precipitation, mm/day
SCALE_M = 5566  # CHIRPS native resolution is about 0.05 degrees


def counties_to_fc(path: str, name_col: str) -> ee.FeatureCollection:
    gdf = gpd.read_file(path).to_crs(4326)[[name_col, "geometry"]]
    gdf = gdf.rename(columns={name_col: "county"})
    # Simplify so the payload sent to Earth Engine stays small (~100 m tolerance)
    gdf["geometry"] = gdf.geometry.simplify(0.001)
    return ee.FeatureCollection(gdf.__geo_interface__)


def fetch_year(fc: ee.FeatureCollection, year: int, months: list[int]) -> pd.DataFrame:
    """Mean of the monthly rainfall total over each county, for one year."""

    def per_month(m):
        m = ee.Number(m)
        start = ee.Date.fromYMD(year, m, 1)
        total = (
            ee.ImageCollection(CHIRPS)
            .filterDate(start, start.advance(1, "month"))
            .select("precipitation")
            .sum()
        )
        stats = total.reduceRegions(
            collection=fc, reducer=ee.Reducer.mean(), scale=SCALE_M
        )
        return stats.map(lambda f: f.set({"year": year, "month": m}))

    out = ee.FeatureCollection(ee.List(months).map(per_month)).flatten()
    out = out.select(["county", "year", "month", "mean"], None, False)
    rows = [f["properties"] for f in out.getInfo()["features"]]
    df = pd.DataFrame(rows).rename(columns={"mean": "rain_mm"})
    return df[["county", "year", "month", "rain_mm"]]


def last_complete_month(today: dt.date) -> tuple[int, int]:
    first = today.replace(day=1)
    prev = first - dt.timedelta(days=1)
    return prev.year, prev.month


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--counties", required=True, help="County boundaries (GeoJSON/shapefile)")
    ap.add_argument("--name-col", required=True, help="Column holding the county name")
    ap.add_argument("--project", help="Google Cloud project registered for Earth Engine")
    ap.add_argument("--start-year", type=int, default=1991)
    ap.add_argument("--out", default="data/monthly_rainfall.csv")
    args = ap.parse_args()

    ee.Initialize(project=args.project) if args.project else ee.Initialize()
    fc = counties_to_fc(args.counties, args.name_col)

    end_year, end_month = last_complete_month(dt.date.today())
    frames = []
    for year in range(args.start_year, end_year + 1):
        months = list(range(1, (end_month if year == end_year else 12) + 1))
        print(f"Fetching {year} ({len(months)} months)...")
        frames.append(fetch_year(fc, year, months))

    new = pd.concat(frames, ignore_index=True)
    out = Path(args.out)
    if out.exists():
        new = pd.concat([pd.read_csv(out), new], ignore_index=True)
    new = new.drop_duplicates(["county", "year", "month"], keep="last")
    new["rain_mm"] = new["rain_mm"].round(1)
    new.sort_values(["county", "year", "month"]).to_csv(out, index=False)
    print(f"Wrote {len(new)} rows to {out}")


if __name__ == "__main__":
    main()
