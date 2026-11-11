# Casablanca Lab Gap Map

Finds zones in Casablanca with many doctors, clinics and hospitals but few medical laboratories.

Open `index.html` (served by GitHub Pages at `/casablanca-health/`).

## Data

[Overture Maps](https://overturemaps.org) release `2026-10-21.0`: Places, Divisions and Transportation themes,
read straight from the public S3 bucket with HTTP range requests (only row groups overlapping Casablanca are downloaded).

## Rebuild

```bash
pip install pyarrow fsspec aiohttp requests shapely
python3 fetch_overture.py 2026-10-21.0 places.json      # health and other places in the bbox
python3 fetch_context.py 2026-10-21.0 context.json      # district polygons + major roads
# divisions.json (neighbourhood names) comes from the same bucket: theme=divisions/type=division
python3 build.py places.json divisions.json context.json  # classify, write data.json, index.html, artifact.html
node analysis.js data.json                               # text summary of the top zones
```

## Method

- Places are classified as lab, hospital/clinic, doctor or dentist by Overture category and by name
  (French, English and Arabic patterns). Vets, aesthetics, physiotherapy and pharmacies are excluded; duplicate listings are merged.
- 400 m hexagon grid. For each hexagon: demand = clinics × weight (default 3) + doctors (+ dentists, optional)
  within the catchment radius (default 1 km); gap score = demand ÷ (labs within the radius + 1).
- Zones are ranked by score with one zone per catchment.

## Limits

Overture under-counts Moroccan cabinets and labs, especially outside central districts, so treat scores as relative
signals and verify against directories (DabaDoc, Med.ma) or on the ground. Large hospitals usually have in-house labs.
Population, income and rent are not modelled.
