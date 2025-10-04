# FarmSim Backend (Flask) — NASA Integrations

This backend exposes **verifiable NASA data** for the FarmSim app.

## Endpoints

### 1) Health
`GET /api/health`

### 2) NASA POWER — Daily Point
`GET /api/power/daily?lat=53.42&lon=-7.93&start=2025-10-01&end=2025-10-04&parameters=T2M,PRECTOT,RH2M`

- **Source:** NASA POWER API — https://power.larc.nasa.gov/docs/services/api/
- Returns JSON with meteorology (temperature, precipitation, humidity, etc.).

### 3) NASA GIBS — MODIS NDVI Tiles
`GET /api/gibs/ndvi-tile?date=2025-09-30&z=4&x=7&y=5`

- **Layer:** `MODIS_Terra_NDVI_16Day`
- **Source:** NASA GIBS — https://wiki.earthdata.nasa.gov/display/GIBS
- Returns a **tile URL** to use as a map layer (imagery).

### 4) SMAP — Availability Helper
`GET /api/smap/availability?date=2025-01-01`

- **Product:** `SPL3SMP_E.005`
- **DAAC:** NSIDC (NASA) — https://nsidc.org/data/SPL3SMP_E
- Provides the official data directory URL and guidance to download with Earthdata auth.

## Run locally

```bash
cd src
python app.py
# or: flask --app app run --host 0.0.0.0 --port 5000 --debug
```

## Install
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Notes
- **POWER** and **GIBS** are open endpoints (no credentials needed).
- **SMAP** soil moisture files require **Earthdata login** or **AppEEARS** to download; we provide the official directory path for verification.
- Keep all outbound responses annotated with `"meta.source"` so judges can see the NASA origin in API responses.
