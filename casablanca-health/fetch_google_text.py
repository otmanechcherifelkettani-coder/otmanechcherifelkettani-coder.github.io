"""Second Google Places pass by *keyword* (Text Search), to catch places Google files under a generic category
(e.g. "LABORATOIRE D'ANALYSES MEDICALES DAR BOUAZZA" is typed `service`, so a medical_lab category search misses it).

Same adaptive grid as fetch_google.py: a cell whose search returns the 20-result page maximum is split in four.
Usage: BBOX=... STEP=8000 REGION=region.json python3 fetch_google_text.py out.json [max_requests]
"""
import json
import math
import os
import sys
import time

import requests
from shapely.geometry import box, shape

OUT = sys.argv[1]
MAX_REQ = int(sys.argv[2]) if len(sys.argv) > 2 else 2500
KEY = os.environ["places_key"]
XMIN, YMIN, XMAX, YMAX = map(float, os.environ.get("BBOX", "-9.07,32.29,-6.75,33.84").split(","))
STEP = float(os.environ.get("STEP", 8000))
REGION = shape(json.load(open(os.environ["REGION"]))["region"]["geom"]).buffer(0.01) if os.environ.get("REGION") else None
KX, KY = math.cos(math.radians(33.0)) * 111320, 110540
QUERIES = {
    "lab_fr": "laboratoire d'analyses médicales",
    "lab_ar": "مختبر التحليلات الطبية",
    "clinic": "clinique",
}
FIELDS = "places.id,places.displayName,places.location,places.primaryType,places.types,places.businessStatus"
nreq, places = 0, {}


import threading
LOCK = threading.Lock()


def search(q, x0, y0, x1, y1):
    global nreq
    with LOCK:
        nreq += 1
    lo = lambda x: x / KX - 7.6
    la = lambda y: y / KY + 33.0
    body = {"textQuery": q, "pageSize": 20,
            "locationRestriction": {"rectangle": {"low": {"latitude": la(y0), "longitude": lo(x0)},
                                                  "high": {"latitude": la(y1), "longitude": lo(x1)}}}}
    for attempt in range(7):
        r = requests.post("https://places.googleapis.com/v1/places:searchText", json=body, timeout=30,
                          headers={"X-Goog-Api-Key": KEY, "X-Goog-FieldMask": FIELDS})
        if r.status_code == 200:
            return r.json().get("places", [])
        if r.status_code in (429, 500, 503):
            time.sleep(2 ** attempt)
            continue
        raise SystemExit(f"Places API error {r.status_code}: {r.text[:300]}")
    raise SystemExit("Places API kept failing")


def cell(tag, q, x0, y0, x1, y1):
    if nreq >= MAX_REQ:
        return False
    ll = box(x0 / KX - 7.6, y0 / KY + 33.0, x1 / KX - 7.6, y1 / KY + 33.0)
    if REGION is not None and not REGION.intersects(ll):
        return True
    res = search(q, x0, y0, x1, y1)
    for p in res:
        e = places.setdefault(p["id"], {"id": p["id"], "name": p.get("displayName", {}).get("text"),
                                       "lat": p["location"]["latitude"], "lon": p["location"]["longitude"],
                                       "primary": p.get("primaryType"), "types": p.get("types", []),
                                       "status": p.get("businessStatus"), "streams": []})
        if tag not in e["streams"]:
            e["streams"].append(tag)
    if len(res) >= 20 and (x1 - x0) > 150:
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        ok = True
        for a, b, c, d in ((x0, y0, mx, my), (mx, y0, x1, my), (x0, my, mx, y1), (mx, my, x1, y1)):
            ok = cell(tag, q, a, b, c, d) and ok
        return ok
    return True


# resume: keep places and finished queries from an earlier, interrupted run
done = set()
if os.path.exists(OUT):
    prev = json.load(open(OUT))
    places.update({p["id"]: p for p in prev["places"]})
    done = set(prev.get("done", []))
    nreq = prev.get("requests", 0)
    print("resuming; done:", sorted(done), "requests so far", nreq, flush=True)

complete = True
X0, Y0, X1, Y1 = (XMIN + 7.6) * KX, (YMIN - 33.0) * KY, (XMAX + 7.6) * KX, (YMAX - 33.0) * KY
for tag, q in QUERIES.items():
    if tag in done:
        continue
    tops, y = [], Y0
    while y < Y1:
        x = X0
        while x < X1:
            tops.append((x, y, min(x + STEP, X1), min(y + STEP, Y1)))
            x += STEP
        y += STEP
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(4) as ex:  # top-level cells in parallel (more trips Google's rate limit)
        for ok in ex.map(lambda t: cell(tag, q, *t), tops):
            complete = ok and complete
    done.add(tag)
    json.dump({"requests": nreq, "complete": complete, "done": sorted(done), "places": list(places.values())},
              open(OUT, "w"), ensure_ascii=False)  # checkpoint after each query
    print(f"{tag}: requests so far {nreq}, places {len(places)}", flush=True)

json.dump({"requests": nreq, "complete": complete, "done": sorted(done), "places": list(places.values())},
          open(OUT, "w"), ensure_ascii=False)
print(f"requests {nreq}, complete={complete}, places {len(places)}")
