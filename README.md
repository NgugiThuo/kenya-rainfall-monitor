# Kenya rainfall monitor

A small web map that shows how each Kenyan county's monthly rainfall compares with normal.
Built to practise the full path from satellite data to a deployed geospatial web app:
Earth Engine processing in Python, a PostGIS database, a FastAPI service that returns GeoJSON,
and a Leaflet front end, all run with Docker Compose.



## What it shows

- A choropleth of counties for any month since 1991, as **percent of normal** or **rainfall in mm**.
- A count of counties below 75% of normal for the selected month.
- A click-through chart per county: the last 36 months of rainfall against the long-term average.

## How it works

```
CHIRPS (Earth Engine) -> fetch_chirps.py -> build_anomalies.py -> load_postgis.py -> PostGIS
                                                                                       |
                                              Leaflet map  <-  FastAPI (GeoJSON)  <----+
```

| Step | File | What it does |
|------|------|--------------|
| 1 | `pipeline/fetch_chirps.py` | Sums CHIRPS daily rainfall into monthly totals and averages them over each county. Re-running it adds new months to the existing CSV. |
| 2 | `pipeline/build_anomalies.py` | Computes the 1991–2020 baseline for each county and calendar month, then anomaly (mm) and percent of normal. |
| 3 | `pipeline/load_postgis.py` | Loads county boundaries and the rainfall table into PostGIS with indexes. |
| 4 | `api/main.py` | Serves `/months`, `/rainfall?year=&month=` (GeoJSON) and `/counties/{name}/series`. |
| 5 | `web/index.html` | Leaflet map, month selector, metric toggle, legend and county popups. |

## Run it

You need Docker, Python 3.11+, and an Earth Engine account with a registered Cloud project.

```bash
# 1. County boundaries: put a GeoJSON of Kenya's 47 counties at data/kenya_counties.geojson
#    and note which column holds the county name (used as --name-col below).

# 2. Pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r pipeline/requirements.txt
earthengine authenticate
python pipeline/fetch_chirps.py --counties data/kenya_counties.geojson --name-col NAME --project YOUR_PROJECT
python pipeline/build_anomalies.py

# 3. Database, API and web server
docker compose up -d
export DATABASE_URL=postgresql+psycopg2://rain:rain@localhost:5432/rain
python pipeline/load_postgis.py --counties data/kenya_counties.geojson --name-col NAME

# 4. Open http://localhost:8080
```

Run the tests with `pytest`.

## Method and limits

- **Data:** CHIRPS, a blend of satellite estimates and station data, about 5 km resolution.
- **Baseline:** the 1991–2020 mean for each county and calendar month.
- **Percent of normal** is left empty where the baseline is zero, because the ratio is meaningless
  in months that are normally dry.
- County values are spatial averages, so they hide local variation, especially in large counties.
- The latest month's data can be revised after first release.
- This is a monitoring view of what has already fallen. It is not a forecast.

## Possible next steps

- Scheduled monthly refresh (GitHub Actions) and deployment to a small cloud host.
- Add a second indicator such as the Standardised Precipitation Index (SPI).
- Serve the layers through OGC services (WMS/WFS) as well as GeoJSON.

## Credits

Rainfall: Climate Hazards Center, UC Santa Barbara (CHIRPS). Basemap: OpenStreetMap contributors.
Colour scale: ColorBrewer (BrBG).
