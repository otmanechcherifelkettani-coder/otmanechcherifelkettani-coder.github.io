"""Fetch base-map context for Casablanca from Overture: district polygons and major roads.

Output: context.json with {"areas": [...], "roads": [...]} as simplified lon/lat coordinate lists.
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import fsspec
import pyarrow.parquet as pq
import requests
from shapely import wkb
from shapely.geometry import box, mapping

RELEASE = sys.argv[1] if len(sys.argv) > 1 else "2026-10-21.0"
OUT = sys.argv[2] if len(sys.argv) > 2 else "context.json"
BUCKET = "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com"
XMIN, YMIN, XMAX, YMAX = (map(float, os.environ["BBOX"].split(",")) if os.environ.get("BBOX")
                          else (-7.75, 33.45, -7.40, 33.66))  # BBOX="xmin,ymin,xmax,ymax"
CLIP = box(XMIN, YMIN, XMAX, YMAX)
LARGE = (XMAX - XMIN) > 1  # region-scale: lighter roads, coarser polygons
fs = fsspec.filesystem("http", block_size=4 * 1024 * 1024)


def keys(theme, typ):
    txt = requests.get(f"{BUCKET}/?list-type=2&prefix=release/{RELEASE}/theme={theme}/type={typ}/", timeout=60).text
    return re.findall(r"<Key>([^<]+\.parquet)</Key>", txt)


def read_bbox(key, cols, row_filter):
    with fs.open(f"{BUCKET}/{key}", "rb") as f:
        pf = pq.ParquetFile(f)
        md, s = pf.metadata, pf.metadata.schema
        ix = {p: next(i for i in range(len(s)) if s.column(i).path == f"bbox.{p}") for p in ("xmin", "xmax", "ymin", "ymax")}
        groups = []
        for g in range(md.num_row_groups):
            st = {p: md.row_group(g).column(i).statistics for p, i in ix.items()}
            if (st["xmax"].max >= XMIN and st["xmin"].min <= XMAX and st["ymax"].max >= YMIN and st["ymin"].min <= YMAX):
                groups.append(g)
        if not groups:
            return []
        rows = pf.read_row_groups(groups, columns=cols + ["bbox"]).to_pylist()
    out = []
    for r in rows:
        b = r["bbox"]
        if b["xmax"] < XMIN or b["xmin"] > XMAX or b["ymax"] < YMIN or b["ymin"] > YMAX:
            continue
        if row_filter(r):
            out.append(r)
    return out


def coords(geom, tol):
    g = geom.intersection(CLIP).simplify(tol, preserve_topology=True)
    if g.is_empty:
        return None
    m = mapping(g)
    rnd = lambda c: [round(c[0], 5), round(c[1], 5)]
    if m["type"] == "Polygon":
        return [[[rnd(c) for c in ring] for ring in m["coordinates"]]]
    if m["type"] == "MultiPolygon":
        return [[[rnd(c) for c in ring] for ring in poly] for poly in m["coordinates"]]
    if m["type"] == "LineString":
        return [[rnd(c) for c in m["coordinates"]]]
    if m["type"] == "MultiLineString":
        return [[rnd(c) for c in line] for line in m["coordinates"]]
    return None


# District polygons (arrondissements and surrounding communes)
area_rows = []
with ThreadPoolExecutor(4) as ex:
    for rs in ex.map(lambda k: read_bbox(k, ["names", "subtype", "class", "geometry"],
                                         lambda r: r["subtype"] in ("macrohood", "localadmin", "locality", "county")),
                     keys("divisions", "division_area")):
        area_rows.extend(rs)
areas = []
for r in area_rows:
    n = r["names"] or {}
    name = dict(n.get("common") or {}).get("fr") or n.get("primary")
    c = coords(wkb.loads(r["geometry"]), 0.001 if LARGE else 0.0004)
    if c:
        areas.append({"name": name, "subtype": r["subtype"], "polys": c})
print(f"{len(areas)} areas", flush=True)

# Major roads
ROAD = {"motorway", "trunk", "primary"} if LARGE else {"motorway", "trunk", "primary", "secondary"}
road_rows = []
with ThreadPoolExecutor(6) as ex:
    for rs in ex.map(lambda k: read_bbox(k, ["class", "subtype", "geometry"],
                                         lambda r: r["subtype"] == "road" and r["class"] in ROAD),
                     keys("transportation", "segment")):
        road_rows.extend(rs)
roads = []
for r in road_rows:
    c = coords(wkb.loads(r["geometry"]), 0.0006 if LARGE else 0.0002)
    if c:
        roads.append({"cls": r["class"], "lines": c})
print(f"{len(roads)} road segments", flush=True)

json.dump({"areas": areas, "roads": roads}, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
