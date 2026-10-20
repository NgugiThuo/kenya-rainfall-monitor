"""Turn raw monthly county rainfall into baseline and anomaly columns.

Baseline = mean rainfall for that county and calendar month over 1991-2020
(the current WMO standard climatological normal period).
"""
import argparse

import pandas as pd

BASE_START, BASE_END = 1991, 2020


def build(raw: pd.DataFrame, base_start: int = BASE_START, base_end: int = BASE_END) -> pd.DataFrame:
    base = (
        raw[raw["year"].between(base_start, base_end)]
        .groupby(["county", "month"], as_index=False)["rain_mm"]
        .mean()
        .rename(columns={"rain_mm": "baseline_mm"})
    )
    out = raw.merge(base, on=["county", "month"], how="left")
    out["anomaly_mm"] = out["rain_mm"] - out["baseline_mm"]
    # Percent of normal is undefined where the baseline is zero (dry-season months)
    out["pct_of_normal"] = (100 * out["rain_mm"] / out["baseline_mm"]).where(out["baseline_mm"] > 0)
    return out.round({"baseline_mm": 1, "anomaly_mm": 1, "pct_of_normal": 0})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="data/monthly_rainfall.csv")
    ap.add_argument("--out", default="data/rainfall_anomalies.csv")
    args = ap.parse_args()
    result = build(pd.read_csv(args.src))
    result.to_csv(args.out, index=False)
    print(f"Wrote {len(result)} rows to {args.out}")
