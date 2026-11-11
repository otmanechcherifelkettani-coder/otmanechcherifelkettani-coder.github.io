"""Spread each commune's census population over a 400 m grid in proportion to building footprint area.

Buildings: Overture `buildings` theme (only bbox + class are read, so footprint ≈ bbox area; non-residential
classes are down-weighted). Population: communes.json (HCP RGPH 2024 + growth 2014-2024).
Output popcells.json: [[lat, lon, residents_2024, annual_growth_pct, commune_index], ...]
Overture building coverage is uneven (some growing communes have very few mapped buildings), so each commune's
population is split 50/50 between two shares: building footprint, and the density of all Overture places
(shops, cafés, schools ...: a proxy for where people live and go). If a commune has too few of either, its
population is spread evenly over the commune's grid cells.
Usage: BBOX=... python3 fetch_buildings.py communes.json places.json popcells.json
"""
import json
import math
import os
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import fsspec
import pyarrow.parquet as pq
import requests
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

COMMUNES, PLACES, OUT = sys.argv[1:4]
RELEASE = "2026-10-21.0"
B = "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com"
XMIN, YMIN, XMAX, YMAX = map(float, os.environ.get("BBOX", "-9.07,32.29,-6.75,33.84").split(","))
CELL = 400.0  # metres
KX, KY = math.cos(math.radians(33.0)) * 111320, 110540
# where people do not live: count these buildings at a tenth of their area
NON_RES = {"commercial", "industrial", "warehouse", "office", "retail", "school", "university", "hospital",
           "religious", "mosque", "transportation", "agricultural", "farm", "greenhouse", "parking", "civic",
           "government", "military", "service", "sports_hall", "stadium", "hangar", "factory"}

keys = re.findall(r"<Key>([^<]+\.parquet)</Key>", requests.get(
    f"{B}/?list-type=2&prefix=release/{RELEASE}/theme=buildings/type=building/", timeout=60).text)
fs = fsspec.filesystem("http", block_size=4 << 20)


def read(k):
    pf = pq.ParquetFile(fs.open(f"{B}/{k}", "rb"))
    md, s = pf.metadata, pf.metadata.schema
    ix = {c: next(i for i in range(len(s)) if s.column(i).path == f"bbox.{c}") for c in ("xmin", "xmax", "ymin", "ymax")}
    groups = [j for j in range(md.num_row_groups)
              if (lambda st: st["xmax"].max >= XMIN and st["xmin"].min <= XMAX and st["ymax"].max >= YMIN
                  and st["ymin"].min <= YMAX)({c: md.row_group(j).column(i).statistics for c, i in ix.items()})]
    if not groups:
        return []
    cols = ["bbox", "class"] if "class" in pf.schema_arrow.names else ["bbox"]
    out = []
    for r in pf.read_row_groups(groups, columns=cols).to_pylist():
        b = r["bbox"]
        x, y = (b["xmin"] + b["xmax"]) / 2, (b["ymin"] + b["ymax"]) / 2
        if XMIN <= x <= XMAX and YMIN <= y <= YMAX:
            area = (b["xmax"] - b["xmin"]) * KX * (b["ymax"] - b["ymin"]) * KY
            w = 0.1 if (r.get("class") or "") in NON_RES else 1.0
            out.append((x, y, min(area, 5000) * w))  # cap: huge bboxes are usually factories or bad shapes
    return out


bld = []
with ThreadPoolExecutor(8) as ex:
    for rows in ex.map(read, keys):
        bld.extend(rows)
print(len(bld), "buildings in bbox", flush=True)

communes = json.load(open(COMMUNES))
idx = [i for i, c in enumerate(communes) if c.get("polys")]
geoms = [shape({"type": "MultiPolygon", "coordinates": communes[i]["polys"]}).buffer(0) for i in idx]
tree = STRtree(geoms)

def assign(points):
    """points: iterable of (x, y, w) -> {commune: {(gx, gy): w}}"""
    out = defaultdict(lambda: defaultdict(float))
    for x, y, w in points:
        pt = Point(x, y)
        hits = [h for h in tree.query(pt) if geoms[h].contains(pt)]
        if not hits:
            continue
        ci = idx[min(hits, key=lambda h: geoms[h].area)]
        out[ci][(int(((x + 7.6) * KX) // CELL), int(((y - 33.0) * KY) // CELL))] += w
    return out


by_bld = assign(bld)
plc = [(p["lon"], p["lat"], 1.0) for p in json.load(open(PLACES))]
by_plc = assign(plc)
print(len(plc), "Overture places used as activity proxy", flush=True)


def shares(d):
    t = sum(d.values())
    return {k: v / t for k, v in d.items()} if t else {}


def grid_cells(geom):
    """all grid cells whose centre falls inside the commune"""
    x0, y0, x1, y1 = geom.bounds
    gx0, gx1 = int(((x0 + 7.6) * KX) // CELL), int(((x1 + 7.6) * KX) // CELL)
    gy0, gy1 = int(((y0 - 33.0) * KY) // CELL), int(((y1 - 33.0) * KY) // CELL)
    out = []
    for gx in range(gx0, gx1 + 1):
        for gy in range(gy0, gy1 + 1):
            lon, lat = (gx + 0.5) * CELL / KX - 7.6, (gy + 0.5) * CELL / KY + 33.0
            if geom.contains(Point(lon, lat)):
                out.append((gx, gy))
    return out


cells, method = [], defaultdict(int)
for k, ci in enumerate(idx):
    c = communes[ci]
    sb, sp = shares(by_bld.get(ci, {})), shares(by_plc.get(ci, {}))
    if len(sb) >= 5 and len(sp) >= 5:
        w = {key: 0.5 * sb.get(key, 0) + 0.5 * sp.get(key, 0) for key in set(sb) | set(sp)}
        method["buildings+places"] += 1
    elif len(sb) >= 5 or len(sp) >= 5:
        w = sb if len(sb) >= len(sp) else sp
        method["one proxy only"] += 1
    else:
        g = grid_cells(geoms[k]) or [(int(((geoms[k].representative_point().x + 7.6) * KX) // CELL),
                                      int(((geoms[k].representative_point().y - 33.0) * KY) // CELL))]
        method["spread evenly (sparse data)"] += 1
        blocks = defaultdict(list)  # evenly spread population: 1.6 km blocks are enough and keep the page light
        for gx, gy in g:
            blocks[(gx // 4, gy // 4)].append((gx, gy))
        for members in blocks.values():
            share = len(members) / len(g)
            mx = sum(m[0] for m in members) / len(members)
            my = sum(m[1] for m in members) / len(members)
            cells.append([round((my + 0.5) * CELL / KY + 33.0, 5), round((mx + 0.5) * CELL / KX - 7.6, 5),
                          round(c["pop"] * share), c.get("growth"), ci])
        continue
    for (gx, gy), share in w.items():
        pop = c["pop"] * share
        if pop < 1:
            continue
        cells.append([round((gy + 0.5) * CELL / KY + 33.0, 5), round((gx + 0.5) * CELL / KX - 7.6, 5),
                      round(pop), c.get("growth"), ci])

json.dump(cells, open(OUT, "w"), separators=(",", ":"))
print(dict(method))
print(len(cells), "population cells; residents placed:", sum(c[2] for c in cells),
      "; densest cell:", max(c[2] for c in cells))
