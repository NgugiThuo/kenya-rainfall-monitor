import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from build_anomalies import build  # noqa: E402


def make_raw():
    rows = []
    for year in range(1991, 2021):  # baseline period: every January is 100 mm
        rows.append({"county": "Turkana", "year": year, "month": 1, "rain_mm": 100.0})
        rows.append({"county": "Turkana", "year": year, "month": 2, "rain_mm": 0.0})
    rows.append({"county": "Turkana", "year": 2025, "month": 1, "rain_mm": 50.0})
    rows.append({"county": "Turkana", "year": 2025, "month": 2, "rain_mm": 5.0})
    return pd.DataFrame(rows)


def test_percent_of_normal_and_anomaly():
    out = build(make_raw())
    jan = out[(out.year == 2025) & (out.month == 1)].iloc[0]
    assert jan.baseline_mm == 100.0
    assert jan.pct_of_normal == 50.0
    assert jan.anomaly_mm == -50.0


def test_zero_baseline_gives_no_percent():
    out = build(make_raw())
    feb = out[(out.year == 2025) & (out.month == 2)].iloc[0]
    assert pd.isna(feb.pct_of_normal)
    assert feb.anomaly_mm == 5.0


def test_baseline_ignores_years_outside_period():
    out = build(make_raw())
    # The 2025 row must not leak into the baseline
    assert out[out.month == 1].baseline_mm.nunique() == 1
    assert out[out.month == 1].baseline_mm.iloc[0] == 100.0
