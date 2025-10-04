# 🌾 Farm-Spark-Grow NASA Backend

> Flask API backend for **Farm-Spark-Grow**, integrating verified **NASA open-data sources** — POWER, GIBS, and SMAP — to power real-world agricultural insights for the [NASA Space Apps Challenge 2025](https://www.spaceappschallenge.org/2025/challenges/nasa-farm-navigators-using-nasa-data-exploration-in-agriculture/).

---

## 🚀 Overview

This backend connects to three official NASA data services:

| Dataset | Purpose | Official Source |
|----------|----------|-----------------|
| **NASA POWER** | Daily agro-climatic parameters (temperature, rainfall, humidity, wind) | [https://power.larc.nasa.gov/api](https://power.larc.nasa.gov/api) |
| **NASA GIBS** | MODIS satellite imagery tiles for farm map visualization | [https://gibs.earthdata.nasa.gov/wmts](https://gibs.earthdata.nasa.gov/wmts) |
| **NASA SMAP (via NSIDC / Earthdata)** | Global soil-moisture dataset (SPL3SMP_E v006) | [https://data.nsidc.earthdatacloud.nasa.gov](https://data.nsidc.earthdatacloud.nasa.gov) |

These APIs feed live environmental and soil data to the Angular frontend dashboard.

---

## 📂 Folder Structure

```
backend/
├── app.py               # Main Flask app (NASA integration)
├── requirements.txt     # Dependencies
├── .env.sample          # Example env vars for Earthdata login
└── README.md            # This file
```

---

## ⚙️ Setup

### 1. Clone & install dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.sample .env
```

Edit `.env`:

```bash
EARTHDATA_USER=your_earthdata_username
EARTHDATA_PASS=your_earthdata_password
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

Create a free account at [https://urs.earthdata.nasa.gov/](https://urs.earthdata.nasa.gov/).

### 3. Run the backend

```bash
python app.py
```

Visit [http://localhost:5000/health](http://localhost:5000/health) to check.

---

## 🔗 API Endpoints

### 1. NASA POWER (Daily Agro-Climate)

**GET** `/api/power/daily?lat=53.4239&lon=-7.9407&start=20250927&end=20251004`

Response:
```json
{
  "ok": true,
  "source": "NASA POWER",
  "data": { ... }
}
```

### 2. NASA GIBS (Imagery Tiles)

**GET** `/api/gibs/wmts-template?layer=MODIS_Terra_CorrectedReflectance_TrueColor&date=2025-10-03`

Response:
```json
{
  "ok": true,
  "template": "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/.../{z}/{y}/{x}.jpg"
}
```

### 3. NASA SMAP (Soil Moisture)

**GET** `/api/smap/soil-moisture?lat=53.4239&lon=-7.9407&date=2025-10-03`

Response:
```json
{
  "ok": true,
  "source": "SMAP SPL3SMP_E v006",
  "soilMoisture": 0.23,
  "units": "m3/m3"
}
```

---

## ✅ Data Provenance

| Dataset | NASA Source | Endpoint | Auth |
|----------|--------------|-----------|------|
| POWER | NASA LaRC | `/api/temporal/daily/point` | No |
| GIBS | NASA GSFC | `/wmts/epsg3857/best` | No |
| SMAP | NASA NSIDC | `SPL3SMP_E v006` | Yes (Earthdata Login) |

---

## 🧾 License

MIT License © 2025 Mansoor Ahmed  
Data © NASA / U.S. Government — Public Domain.

---

### 🌍 “Real NASA data. Real insight. Smarter, sustainable farming.”
