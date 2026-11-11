# Casablanca Lab Gap Map

Finds zones in the Casablanca-Settat region (Casablanca, Mohammédia, Nouaceur, Médiouna, Berrechid, Settat,
El Jadida, Sidi Bennour, Benslimane) with many doctors, clinics and hospitals but few medical laboratories.

Open `index.html` (served by GitHub Pages at `/casablanca-health/`).

## Data

[Overture Maps](https://overturemaps.org) release `2026-10-21.0`: Places, Divisions and Transportation themes,
read straight from the public S3 bucket with HTTP range requests (only row groups overlapping Casablanca are downloaded),
merged with OpenStreetMap health features from the Overpass API (`osm_health.json`, query in `osm_health.overpassql`).

## Rebuild

```bash
pip install pyarrow fsspec aiohttp requests shapely
export BBOX="-9.07,32.29,-6.75,33.84"                    # Casablanca-Settat region
python3 fetch_region.py                                   # region + province boundaries -> region.json
python3 fetch_overture.py 2026-10-21.0 places.json
python3 fetch_divisions.py 2026-10-21.0 divisions.json   # neighbourhood and town names
python3 fetch_context.py 2026-10-21.0 context.json       # district polygons + major roads
curl -A "casablanca-health" https://overpass.openstreetmap.fr/api/interpreter --data-urlencode data@osm_health.overpassql -o osm_health.json
REGION=region.json python3 build.py places.json divisions.json context.json osm_health.json
node analysis.js data.json "Nouaceur"                    # text ranking, optionally for one province
```

Optional private Google Places layer (needs `places_key`; output stays out of the repo):

```bash
BBOX=$BBOX STEP=8000 REGION=region.json python3 fetch_google.py google.json 3500
GOOGLE_PLACES=google.json REGION=region.json OUT_DIR=private python3 build.py places.json divisions.json context.json osm_health.json
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
