# Casablanca Lab Gap Map

Finds zones in the Casablanca-Settat region (Casablanca, Mohammédia, Nouaceur, Médiouna, Berrechid, Settat,
El Jadida, Sidi Bennour, Benslimane) with many doctors, clinics and hospitals but few medical laboratories.

Open `index.html` (served by GitHub Pages at `/casablanca-health/`).

## Data

[Overture Maps](https://overturemaps.org) release `2026-10-21.0`: Places, Divisions and Transportation themes,
read straight from the public S3 bucket with HTTP range requests (only row groups overlapping Casablanca are downloaded),
merged with OpenStreetMap health features from the Overpass API (`osm_health.json`, query in `osm_health.overpassql`).

## Formula (Best sites tab)

For a candidate site *c* and every demand point *z* within 6 km:

```
D_z   = α · residents_z · (1 + g_z)^years · (affluence_z/100)^γ  +  (1 − α) · k · prescriber_weight_z
f(d)  = max(d, 300 m)^−β                                                           pull of a site at distance d
P_cz  = f(d_cz) / ( f(d_cz) + Σ_j A_j · f(d_jz) + f(3 km) )                        share a NEW lab at c wins (Huff)
Score = Σ_z D_z · P_cz                                                             in residents captured
```

- residents_z: HCP RGPH 2024 commune population spread over a 400 m grid (building footprint + place density);
  g_z: the commune's annual growth 2014–2024; years: projection horizon (default 3).
- affluence_z: income proxy of the commune (100 = regional average, γ = 1 by default). HCP publishes no income by
  commune, so `hcp_fiches.py` builds it from the RGPH 2024 fiches communales: university education, share living in
  apartments or villas, makeshift housing / slums, multidimensional poverty, unemployment and illiteracy
  (each standardised across communes, averaged, ±1 SD = ±25 points).
- prescriber weights: private clinic 3, medical centre 2, high-test specialist 1.5, GP 1.2, unknown doctor 1,
  public hospital / health centre 1, eye-skin clinic and dialysis 0.5, low-test specialist 0.3, imaging and dentist 0.
  k rescales them so both channels have the same regional total; α = 0.6 by default.
- competitors j: medical labs A = 1, public hospitals 0.5 and private clinics 0.3 (in-house labs).
  f(3 km) is the outside option (travel further, hospital lab, home collection, no test). β = 2 by default.
- Revenue ≈ Score × tests per resident per year × average ticket. Validate the shortlist on the ground
  (rent, visibility, parking, catchment of nearby labs' collection points, insurance mix).

## Rebuild

```bash
pip install pyarrow fsspec aiohttp requests shapely
export BBOX="-9.07,32.29,-6.75,33.84"                    # Casablanca-Settat region
python3 fetch_region.py                                   # region + province boundaries -> region.json
python3 fetch_overture.py 2026-10-21.0 places.json
python3 fetch_divisions.py 2026-10-21.0 divisions.json   # neighbourhood and town names
python3 fetch_context.py 2026-10-21.0 context.json       # district polygons + major roads
curl -A "casablanca-health" https://overpass.openstreetmap.fr/api/interpreter --data-urlencode data@osm_health.overpassql -o osm_health.json
# HCP RGPH 2024 legal population (Excel from https://www.hcp.ma/reg-casablanca/attachment/2664423/)
python3 fetch_communes.py pop2024.xlsx region.json communes.json
# HCP 2014 legal population (https://www.hcp.ma/reg-casablanca/docs/docs/pop_legal_2014.pdf) -> growth 2014-24
python3 hcp_2014.py pop_legal_2014.pdf communes.json
python3 fetch_buildings.py communes.json places.json popcells.json   # residents on a 400 m grid
# HCP fiches communales RGPH 2024 (one PDF per province, hcp.ma/reg-casablanca) -> affluence index
python3 hcp_fiches.py fiches/ communes.json
REGION=region.json COMMUNES=communes.json POPCELLS=popcells.json python3 build.py places.json divisions.json context.json osm_health.json
node analysis.js data.json "Nouaceur"                    # text ranking, optionally for one province
```

Optional private Google Places layer (needs `places_key`; output stays out of the repo):

```bash
BBOX=$BBOX STEP=8000 REGION=region.json python3 fetch_google.py google.json 3500   # by category
REGION=region.json python3 fetch_google_text.py google_text.json 3300                 # by keyword (labs filed as "service")
GOOGLE_PLACES=google.json,google_text.json REGION=region.json COMMUNES=communes.json POPCELLS=popcells.json OUT_DIR=private python3 build.py places.json divisions.json context.json osm_health.json
```

## Method

- `classify.py` puts every place from every source into 14 types (medical lab, pathology lab, private clinic,
  specialty clinic, public hospital, health centre, medical centre, dialysis, imaging, GP, high-test specialist,
  low-test specialist, doctor of unknown specialty, dentist) by name and category in French, English and Arabic.
  Vets, pharmacies, physiotherapists, psychologists, opticians, aesthetic-only practices, suppliers and offices
  are excluded; duplicate listings across sources are merged.
- 400 m hexagon grid. For each hexagon: demand = clinics × weight (default 3) + doctors (+ dentists, optional)
  within the catchment radius (default 1 km); gap score = demand ÷ (labs within the radius + 1).
- Zones are ranked by score with one zone per catchment.

## Population

`communes.json` holds the official legal population and households of the region's 168 communes and Casablanca
arrondissements (HCP, RGPH 2024), joined to Overture boundaries (exact or fuzzy name match within the province; three
manual aliases: Charrate = Cherrat, Assoukhour Assawda = Roches Noires, Ech-Challalate = Chellalate). The Communes tab
ranks them by residents per lab.

## Limits

Overture under-counts Moroccan cabinets and labs, especially outside central districts, so treat scores as relative
signals and verify against directories (DabaDoc, Med.ma) or on the ground. Large hospitals usually have in-house labs.
Population, income and rent are not modelled.
