import io
import os
import json
import datetime as dt
from typing import Optional, Tuple

import numpy as np
import h5py
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

EARTHDATA_USER = os.getenv("mans00rahmed")
EARTHDATA_PASS = os.getenv("Asterisks123*")

app = Flask(__name__)
CORS(app)

# ---------- helpers ----------

def ok(data, status=200):
    return jsonify({"ok": True, **data}), status

def err(msg, status=400):
    return jsonify({"ok": False, "error": msg}), status

def ymd(date: dt.date) -> str:
    return date.strftime("%Y%m%d")

def iso(date: dt.date) -> str:
    return date.isoformat()

def make_earthdata_session() -> Optional[requests.Session]:
    """Create an authenticated session for NSIDC/Earthdata.
       Returns None if creds missing (we'll still allow POWER/GIBS)."""
    if not EARTHDATA_USER or not EARTHDATA_PASS:
        return None
    s = requests.Session()
    s.auth = HTTPBasicAuth(EARTHDATA_USER, EARTHDATA_PASS)
    s.headers.update({"User-Agent": "FarmSparkGrow/1.0"})
    return s

# ---------- POWER (no auth required) ----------

@app.get("/api/power/daily")
def power_daily():
    """Proxy NASA POWER daily point API for agro community (AG)."""
    try:
        lat = float(request.args["lat"])
        lon = float(request.args["lon"])
        start = request.args["start"]  # yyyymmdd
        end = request.args["end"]      # yyyymmdd
    except Exception:
        return err("lat, lon, start (yyyymmdd), end (yyyymmdd) are required", 422)

    params = "T2M,PRECTOTCORR,RH2M,WS10M"
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters={params}"
        f"&community=AG"
        f"&longitude={lon}&latitude={lat}"
        f"&start={start}&end={end}"
        f"&format=JSON"
    )
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return ok({"source": "NASA POWER", "data": r.json()})
    except requests.HTTPError as e:
        return err(f"POWER error: {e.response.status_code} {e.response.text}", 502)
    except Exception as e:
        return err(f"POWER exception: {e}", 502)

# ---------- GIBS (imagery tiles helper; no auth) ----------

@app.get("/api/gibs/wmts-template")
def gibs_template():
    """Return a WMTS REST tile template for GIBS. Frontend uses this in Leaflet/Mapbox."""
    layer = request.args.get("layer", "MODIS_Terra_CorrectedReflectance_TrueColor")
    date_iso = request.args.get("date", dt.date.today().isoformat())
    # Web Mercator pyramid for web maps
    base = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"
    template = f"{base}/{layer}/default/{date_iso}/GoogleMapsCompatible_Level9/{{z}}/{{y}}/{{x}}.jpg"
    return ok({"template": template, "layer": layer, "date": date_iso})

# ---------- SMAP soil moisture (needs Earthdata login) ----------

CMR_SEARCH = "https://cmr.earthdata.nasa.gov/search/granules.json"
# Product: SPL3SMP_E v006 (9 km daily, enhanced EASE-2 grid)
SMAP_COLLECTION_CONCEPT_ID = "C1908344279-NSIDC_ECS"  # SPL3SMP_E v006 (stable as of 2025)

def find_smap_granule(date: dt.date) -> Optional[Tuple[str, str]]:
    """Use CMR to find the HTTPS download URL for the given date's SMAP SPL3SMP_E granule."""
    params = {
        "collection_concept_id": SMAP_COLLECTION_CONCEPT_ID,
        "temporal": f"{date.isoformat()}T00:00:00Z,{date.isoformat()}T23:59:59Z",
        "page_size": 10,
        "sort_key": "-start_date"
    }
    r = requests.get(CMR_SEARCH, params=params, timeout=30, headers={"User-Agent": "FarmSparkGrow/1.0"})
    r.raise_for_status()
    js = r.json()
    items = js.get("feed", {}).get("entry", [])
    for it in items:
        links = it.get("links", [])
        for lk in links:
            href = lk.get("href", "")
            # Prefer HTTPS data.nsidc.earthdatacloud URLs
            if href.endswith(".h5") and href.startswith("https://"):
                return href, it.get("time_start", "")
    return None

def sample_smap_point(h5_bytes: bytes, lat: float, lon: float) -> Optional[dict]:
    """Open SMAP HDF5 and return nearest-pixel soil moisture and metadata."""
    with h5py.File(io.BytesIO(h5_bytes), "r") as f:
        # typical groups: Soil_Moisture_Retrieval_Data_AM / PM
        for grp in ("Soil_Moisture_Retrieval_Data_AM", "Soil_Moisture_Retrieval_Data_PM"):
            if grp not in f:
                continue
            ds = f[f"{grp}/soil_moisture"]
            # SMAP EASE-2 grid lat/lon lookup (some files include 2D arrays)
            # Common paths for lat/lon:
            lat_name = None
            lon_name = None
            for cand in [
                "/EASE2_grid/map_latitude",
                "/EASE2_grid/map_equatorial_latitude",
                f"/{grp}/latitude",
            ]:
                if cand in f:
                    lat_name = cand
                    break
            for cand in [
                "/EASE2_grid/map_longitude",
                "/EASE2_grid/map_equatorial_longitude",
                f"/{grp}/longitude",
            ]:
                if cand in f:
                    lon_name = cand
                    break
            if not lat_name or not lon_name:
                continue

            lats = f[lat_name][:]
            lons = f[lon_name][:]

            # ensure 2D compatibility
            if lats.ndim == 1 and lons.ndim == 1:
                # create mesh
                lons, lats = np.meshgrid(lons, lats)

            # nearest pixel
            ij = np.unravel_index(np.argmin((lats - lat) ** 2 + (lons - lon) ** 2), lats.shape)
            val = float(ds[ij])
            meta_date = f[grp].attrs.get("Start_time") or f.attrs.get("RangeBeginningDate") or ""
            return {
                "soilMoisture": val,
                "units": "m3/m3",
                "group": grp,
                "h5_date_attr": meta_date.decode() if isinstance(meta_date, (bytes, bytearray)) else str(meta_date),
                "pixel": {"i": int(ij[0]), "j": int(ij[1])}
            }
    return None

@app.get("/api/smap/soil-moisture")
def smap_soil_moisture():
    """Return SMAP SPL3SMP_E soil moisture at a lat/lon for a given date (YYYY-MM-DD).
       Requires EARTHDATA_USER/PASS env vars to be set.
    """
    # inputs
    try:
        lat = float(request.args["lat"])
        lon = float(request.args["lon"])
        date_iso = request.args["date"]  # YYYY-MM-DD
        date = dt.date.fromisoformat(date_iso)
    except Exception:
        return err("lat, lon, date (YYYY-MM-DD) required", 422)

    sess = make_earthdata_session()
    if sess is None:
        return err("Earthdata credentials missing. Set EARTHDATA_USER and EARTHDATA_PASS.", 401)

    # find the granule for the date (prefer same day; SMAP may lag — caller can pass yesterday)
    try:
        found = find_smap_granule(date)
        if not found:
            return err("No SMAP granule found for date (try a nearby date).", 404)
        href, time_start = found
        resp = sess.get(href, timeout=90, allow_redirects=True)
        if resp.status_code == 401:
            return err("Earthdata auth failed. Check EARTHDATA_USER/PASS.", 401)
        resp.raise_for_status()
        sample = sample_smap_point(resp.content, lat, lon)
        if not sample:
            return err("Unable to read soil moisture from granule.", 500)
        return ok({
            "source": "SMAP SPL3SMP_E v006",
            "date": date_iso,
            "time_start": time_start,
            **sample
        })
    except requests.HTTPError as e:
        return err(f"SMAP HTTP error: {e.response.status_code} {e.response.text[:200]}", 502)
    except Exception as e:
        return err(f"SMAP exception: {e}", 502)

# ---------- health ----------

@app.get("/health")
def health():
    return ok({"service": "FarmSparkGrow NASA backend", "time": dt.datetime.utcnow().isoformat() + "Z"})

# ---------- entry ----------

if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    app.run(host=host, port=port, debug=True)
