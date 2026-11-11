"""Build a drivable road graph for a bbox from Overture transportation segments (no routing server needed).

Each segment lists its connectors (junctions) with their position along the line; consecutive connectors become an
edge whose travel time = length / speed. Speeds are typical Moroccan driving speeds by road class, slowed down in
dense urban communes (congestion). Roads are treated as two-way.
Output roads.npz: node lon/lat arrays and edge arrays (u, v, seconds).
Usage: BBOX=... python3 fetch_roads.py roads.npz [communes.json]
"""
import json
import math
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import fsspec
import numpy as np
import pyarrow.parquet as pq
import requests
from shapely import wkb

OUT = sys.argv[1]
COMMUNES = sys.argv[2] if len(sys.argv) > 2 else None
RELEASE = "2026-10-21.0"
B = "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com"
XMIN, YMIN, XMAX, YMAX = map(float, os.environ.get("BBOX", "-9.07,32.29,-6.75,33.84").split(","))
KX, KY = math.cos(math.radians(33.0)) * 111320, 110540
# km/h, free-flow; urban congestion applied below
SPEED = {"motorway": 100, "trunk": 80, "primary": 60, "secondary": 50, "tertiary": 40, "unclassified": 30,
         "residential": 25, "living_street": 15, "service": 15, "unknown": 25}
URBAN_FACTOR = 0.6   # speed multiplier inside dense communes (≥ 3,000 residents per km²)

keys = re.findall(r"<Key>([^<]+\.parquet)</Key>", requests.get(
    f"{B}/?list-type=2&prefix=release/{RELEASE}/theme=transportation/type=segment/", timeout=60).text)
fs = fsspec.filesystem("http", block_size=4 << 20)


def read(k):
    pf = pq.ParquetFile(fs.open(f"{B}/{k}", "rb"))
    md, s = pf.metadata, pf.metadata.schema
    ix = {c: next(i for i in range(len(s)) if s.column(i).path == f"bbox.{c}") for c in ("xmin", "xmax", "ymin", "ymax")}
    groups = [j for j in range(md.num_row_groups)
              if (lambda st: st["xmax"].max >= XMIN and st["xmin"].min <= XMAX and st["ymax"].max >= YMIN
                  and st["ymin"].min <= YMAX)({c: md.row_group(j).column(i).statistics for c, i in ix.items()})]
    out = []
    if not groups:
        return out
    for r in pf.read_row_groups(groups, columns=["subtype", "class", "connectors", "geometry", "bbox"]).to_pylist():
        b = r["bbox"]
        if r["subtype"] != "road" or r["class"] not in SPEED or b["xmax"] < XMIN or b["xmin"] > XMAX \
                or b["ymax"] < YMIN or b["ymin"] > YMAX or not r["connectors"] or len(r["connectors"]) < 2:
            continue
        out.append((r["class"], [(c["connector_id"], c["at"]) for c in r["connectors"]], r["geometry"]))
    return out


segs = []
with ThreadPoolExecutor(8) as ex:
    for rows in ex.map(read, keys):
        segs.extend(rows)
print(len(segs), "drivable segments", flush=True)

# dense communes (congestion)
dense = None
if COMMUNES:
    from shapely.geometry import Point, shape
    from shapely.prepared import prep
    from shapely.ops import unary_union
    polys = []
    for c in json.load(open(COMMUNES)):
        if not c.get("polys"):
            continue
        g = shape({"type": "MultiPolygon", "coordinates": c["polys"]}).buffer(0)
        area_km2 = g.area * KX * KY / 1e6
        if area_km2 > 0 and c["pop"] / area_km2 >= 3000:
            polys.append(g)
    dense = prep(unary_union(polys)) if polys else None
    print(len(polys), "dense communes slowed by", URBAN_FACTOR, flush=True)

node_id, lon, lat = {}, [], []
U, V, T = [], [], []


def nid(key, x, y):
    i = node_id.get(key)
    if i is None:
        i = node_id[key] = len(lon)
        lon.append(x)
        lat.append(y)
    return i


for cls, conns, geom in segs:
    line = wkb.loads(geom)
    length = sum(math.hypot((x2 - x1) * KX, (y2 - y1) * KY) for (x1, y1), (x2, y2) in zip(line.coords, line.coords[1:]))
    mid = line.interpolate(0.5, normalized=True)
    speed = SPEED[cls] * (URBAN_FACTOR if dense is not None and cls not in ("motorway",) and dense.contains(mid) else 1)
    conns = sorted(conns, key=lambda c: c[1])
    pts = []
    for cid, at in conns:
        p = line.interpolate(at, normalized=True)
        pts.append((nid(cid, p.x, p.y), at))
    for (a, at1), (b, at2) in zip(pts, pts[1:]):
        if a == b:
            continue
        U.append(a)
        V.append(b)
        T.append(max(1.0, (at2 - at1) * length / (speed / 3.6)))

np.savez_compressed(OUT, lon=np.array(lon), lat=np.array(lat), u=np.array(U, dtype=np.int32),
                    v=np.array(V, dtype=np.int32), t=np.array(T, dtype=np.float32))
print(len(lon), "nodes,", len(U), "edges")
