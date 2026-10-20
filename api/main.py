"""Small read-only API that serves county rainfall as GeoJSON."""
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)

app = FastAPI(title="Kenya Rainfall Monitor API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])

RAINFALL_GEOJSON = text(
    """
    SELECT jsonb_build_object(
        'type', 'FeatureCollection',
        'features', COALESCE(jsonb_agg(jsonb_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(c.geom, 4)::jsonb,
            'properties', jsonb_build_object(
                'county', c.county,
                'rain_mm', r.rain_mm,
                'baseline_mm', r.baseline_mm,
                'anomaly_mm', r.anomaly_mm,
                'pct_of_normal', r.pct_of_normal
            )
        )), '[]'::jsonb)
    ) AS fc
    FROM counties c
    JOIN rainfall r ON r.county = c.county
    WHERE r.year = :year AND r.month = :month
    """
)

SERIES = text(
    """
    SELECT year, month, rain_mm, baseline_mm, pct_of_normal
    FROM rainfall
    WHERE county = :county
    ORDER BY year DESC, month DESC
    LIMIT :n
    """
)


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/months")
def months():
    """Months that have data, newest first, as YYYY-MM strings."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT DISTINCT year, month FROM rainfall ORDER BY year DESC, month DESC")
        ).all()
    return [f"{y}-{m:02d}" for y, m in rows]


@app.get("/rainfall")
def rainfall(year: int = Query(..., ge=1981), month: int = Query(..., ge=1, le=12)):
    """County polygons with rainfall, baseline and anomaly for one month."""
    with engine.connect() as conn:
        fc = conn.execute(RAINFALL_GEOJSON, {"year": year, "month": month}).scalar_one()
    if not fc["features"]:
        raise HTTPException(404, f"No data for {year}-{month:02d}")
    return fc


@app.get("/counties/{county}/series")
def county_series(county: str, n: int = Query(36, ge=1, le=600)):
    """Recent monthly history for one county, oldest first."""
    with engine.connect() as conn:
        rows = conn.execute(SERIES, {"county": county, "n": n}).mappings().all()
    if not rows:
        raise HTTPException(404, f"Unknown county: {county}")
    return [dict(r) for r in reversed(rows)]
