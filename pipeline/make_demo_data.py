"""Generate SYNTHETIC monthly county rainfall so the pipeline, API and map can be
tested end to end without Earth Engine.

This is made-up data. It has a rough two-rainy-seasons pattern and is drier in the
north and east, but it is not real rainfall. Never publish it as real, and don't use
a screenshot of it in the README. Replace it with fetch_chirps.py output.

Usage:
    python pipeline/make_demo_data.py --counties data/Shapefile/ke_county.shp --name-col county

Writes data/demo_monthly_rainfall.csv (county, year, month, rain_mm), the same shape
fetch_chirps.py produces, so build_anomalies.py and load_postgis.py work unchanged.
"""
import argparse
import datetime as dt

import numpy as np
import pandas as pd

# Typical monthly rainfall (mm) for a wetter county; scaled down for drier ones.
MONTHLY_MEAN = [60, 55, 110, 190, 150, 60, 40, 45, 50, 100, 140, 90]


def generate(counties: pd.DataFrame, start_year: int = 1991, seed: int = 42) -> pd.DataFrame:
    """counties needs columns: county, lat, lon (a point inside each county)."""
    rng = np.random.default_rng(seed)
    today = dt.date.today()
    last = (today.replace(day=1) - dt.timedelta(days=1))

    # Drier towards the north and east
    dryness = (
        np.clip(counties["lat"] / 4, 0, 1) * 0.5
        + np.clip((counties["lon"] - 38) / 4, 0, 1) * 0.3
    )
    factor = dict(zip(counties["county"], 1.2 - dryness + rng.normal(0, 0.05, len(counties))))

    rows = []
    for year in range(start_year, last.year + 1):
        for month in range(1, 13):
            if (year, month) > (last.year, last.month):
                break
            # A shared wet/dry swing for the whole country, so counties move together
            national = max(rng.normal(1.0, 0.25), 0.1)
            for name in counties["county"]:
                local = rng.gamma(shape=6, scale=1 / 6)  # mean 1, county-level noise
                rain = MONTHLY_MEAN[month - 1] * factor[name] * national * local
                rows.append((name, year, month, round(float(rain), 1)))
    return pd.DataFrame(rows, columns=["county", "year", "month", "rain_mm"])


def main() -> None:
    import geopandas as gpd

    ap = argparse.ArgumentParser()
    ap.add_argument("--counties", required=True)
    ap.add_argument("--name-col", required=True)
    ap.add_argument("--out", default="data/demo_monthly_rainfall.csv")
    args = ap.parse_args()

    g = gpd.read_file(args.counties).to_crs(4326)
    pts = g.geometry.representative_point()
    counties = pd.DataFrame({"county": g[args.name_col], "lat": pts.y, "lon": pts.x})
    df = generate(counties)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows ({counties.shape[0]} counties) to {args.out}")
    print("This is SYNTHETIC demo data, not real rainfall.")


if __name__ == "__main__":
    main()
