"""Harvest Google Places (New) Nearby Search results for Casablanca with an adaptive grid.

Each cell is searched with a circle covering it; when a search returns the 20-result maximum the cell is split
into four, so dense areas are fully enumerated. The API key is read from the `places_key` environment variable.

Usage: python3 fetch_google.py out.json [max_requests]
Note: Google Maps Platform terms limit storing Places content; keep the output private and refresh it rather
than archiving it, and check the terms before displaying it on a non-Google map.
"""
import json
import math
import os
import sys
import time

import requests

OUT = sys.argv[1]
MAX_REQ = int(sys.argv[2]) if len(sys.argv) > 2 else 2500
KEY = os.environ["places_key"]
XMIN, YMIN, XMAX, YMAX = -7.75, 33.45, -7.40, 33.66
KX, KY = math.cos(math.radians(33.57)) * 111320, 110540
STREAMS = {
    "lab": ["medical_lab"],
    "care": ["doctor", "hospital", "general_hospital", "medical_clinic", "medical_center"],
}
FIELDS = "places.id,places.displayName,places.location,places.primaryType,places.types,places.businessStatus"
nreq = 0
places = {}


def search(types, lat, lon, radius):
    global nreq
    nreq += 1
    body = {"includedTypes": types, "maxResultCount": 20, "rankPreference": "DISTANCE",
            "locationRestriction": {"circle": {"center": {"latitude": lat, "longitude": lon}, "radius": radius}}}
    for attempt in range(4):
        r = requests.post("https://places.googleapis.com/v1/places:searchNearby", json=body, timeout=30,
                          headers={"X-Goog-Api-Key": KEY, "X-Goog-FieldMask": FIELDS})
        if r.status_code == 200:
            return r.json().get("places", [])
        if r.status_code in (429, 500, 503):
            time.sleep(2 ** attempt)
            continue
        raise SystemExit(f"Places API error {r.status_code}: {r.text[:300]}")
    raise SystemExit("Places API kept failing")


def cell(stream, x0, y0, x1, y1, depth=0):
    if nreq >= MAX_REQ:
        return False
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    radius = math.hypot(x1 - x0, y1 - y0) / 2
    res = search(STREAMS[stream], cy / KY + 33.57, cx / KX - 7.6, radius)
    for p in res:
        e = places.setdefault(p["id"], {"id": p["id"], "name": p.get("displayName", {}).get("text"),
                                       "lat": p["location"]["latitude"], "lon": p["location"]["longitude"],
                                       "primary": p.get("primaryType"), "types": p.get("types", []),
                                       "status": p.get("businessStatus"), "streams": []})
        if stream not in e["streams"]:
            e["streams"].append(stream)
    if len(res) >= 20 and (x1 - x0) > 120:
        mx, my = cx, cy
        ok = True
        for a, b, c, d in ((x0, y0, mx, my), (mx, y0, x1, my), (x0, my, mx, y1), (mx, my, x1, y1)):
            ok = cell(stream, a, b, c, d, depth + 1) and ok
        return ok
    return True


complete = True
for stream in STREAMS:
    X0, Y0 = (XMIN + 7.6) * KX, (YMIN - 33.57) * KY
    X1, Y1 = (XMAX + 7.6) * KX, (YMAX - 33.57) * KY
    step = 2000
    y = Y0
    while y < Y1:
        x = X0
        while x < X1:
            complete = cell(stream, x, y, min(x + step, X1), min(y + step, Y1)) and complete
            x += step
        y += step
    print(f"{stream}: done, requests so far {nreq}, places {len(places)}", flush=True)

out = [p for p in places.values() if XMIN <= p["lon"] <= XMAX and YMIN <= p["lat"] <= YMAX]
json.dump({"requests": nreq, "complete": complete, "places": out}, open(OUT, "w"), ensure_ascii=False)
print(f"requests {nreq}, complete={complete}, places in bbox {len(out)}")
