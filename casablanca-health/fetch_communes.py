"""Join HCP RGPH 2024 legal population (communes + Casablanca arrondissements) to Overture boundary polygons.

Inputs : HCP Excel "Population légale du Royaume du Maroc selon les résultats du RGPH 2024"
         (https://www.hcp.ma/reg-casablanca/attachment/2664423/), region.json from fetch_region.py
Output : communes.json  [{code, name, province, pop, households, matched, polys}]
Usage  : BBOX=... python3 fetch_communes.py pop2024.xlsx region.json communes.json
"""
import difflib
import json
import os
import re
import sys
import unicodedata

import fsspec
import openpyxl
import pyarrow.parquet as pq
import requests
from shapely import wkb
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

XLSX, REGION, OUT = sys.argv[1:4]
RELEASE = "2026-10-21.0"
B = "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com"
XMIN, YMIN, XMAX, YMAX = map(float, os.environ.get("BBOX", "-9.07,32.29,-6.75,33.84").split(","))


def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"^(commune|arrondissement|municipalite|pachalik|caidat)\s+(de la|de l'|du|des|de|d'|d’)?\s*", "", s)
    s = re.sub(r"\b(ouled|oulad|ould)\b", "oulad", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    return s.replace("ou", "u").replace("ch", "sh").replace("ee", "e")


# ---- HCP table ----
ws = openpyxl.load_workbook(XLSX, read_only=True, data_only=True).worksheets[0]
rows = list(ws.iter_rows(values_only=True))
prov_name = {str(r[6]): r[0] for r in rows if r[6] and len(str(r[6])) == 4}
hcp, seen = [], set()
for r in rows:
    code = str(r[6] or "")
    if len(code) == 8 and code.startswith("6") and re.match(r"^(Commune|Arrondissement|Municipalit)", r[0] or "") \
            and code not in seen:
        seen.add(code)
        hcp.append({"code": code, "name": r[0], "name_ar": r[5], "pop": r[3], "households": r[4],
                    "province": re.sub(r"^(Province|Préfecture)\s+(de la|de l'|du|des|de|d'|d’)\s*", "",
                                       prov_name.get(code[:4], ""))})
print(len(hcp), "HCP units, population", sum(h["pop"] for h in hcp))

# ---- Overture candidate polygons ----
keys = re.findall(r"<Key>([^<]+\.parquet)</Key>", requests.get(
    f"{B}/?list-type=2&prefix=release/{RELEASE}/theme=divisions/type=division_area/", timeout=60).text)
fs = fsspec.filesystem("http", block_size=4 << 20)
cands = []
for k in keys:
    pf = pq.ParquetFile(fs.open(f"{B}/{k}", "rb"))
    md, s = pf.metadata, pf.metadata.schema
    ix = {c: next(i for i in range(len(s)) if s.column(i).path == f"bbox.{c}") for c in ("xmin", "xmax", "ymin", "ymax")}
    groups = [j for j in range(md.num_row_groups)
              if (lambda st: st["xmax"].max >= XMIN and st["xmin"].min <= XMAX and st["ymax"].max >= YMIN
                  and st["ymin"].min <= YMAX)({c: md.row_group(j).column(i).statistics for c, i in ix.items()})]
    if not groups:
        continue
    for r in pf.read_row_groups(groups, columns=["names", "subtype", "country", "geometry", "bbox"]).to_pylist():
        if r["country"] != "MA" or r["subtype"] not in ("localadmin", "locality", "neighborhood", "macrohood"):
            continue
        b = r["bbox"]
        if b["xmax"] < XMIN or b["xmin"] > XMAX or b["ymax"] < YMIN or b["ymin"] > YMAX:
            continue
        n = r["names"] or {}
        names = {n.get("primary")} | set(dict(n.get("common") or {}).values())
        g = wkb.loads(r["geometry"])
        if g.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        cands.append({"names": [x for x in names if x], "subtype": r["subtype"], "geom": g})
print(len(cands), "candidate polygons")

reg = json.load(open(REGION))
provs = [(re.sub(r"^(Province|Préfecture)\s+(de la|de l'|du|des|de|d'|d’)\s*", "", p["name"]), shape(p["geom"]))
         for p in reg["provinces"]]


def prov_of(g):
    c = g.representative_point()
    for n, pg in provs:
        if pg.contains(c):
            return n
    return ""


for c in cands:
    c["prov"] = prov_of(c["geom"])
    c["keys"] = {norm(x) for x in c["names"]}

RANK = {"localadmin": 0, "macrohood": 1, "neighborhood": 1, "locality": 2}


def same_prov(a, b):
    a, b = norm(a), norm(b)
    return a == b or a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= 0.8


# names that differ between HCP and the boundary data
ALIASES = {"sharrate": "sherrat", "assukhurassawda": "roshesnoires", "eshshallalate": "shellalate"}


out, unmatched = [], []
for h in hcp:
    k = norm(h["name"])
    k = ALIASES.get(k, k)
    pool = [c for c in cands if same_prov(c["prov"], h["province"])]
    exact = [c for c in pool if k in c["keys"]]
    best, how = None, ""
    if exact:
        best, how = sorted(exact, key=lambda c: RANK[c["subtype"]])[0], "exact"
    else:
        scored = [(max(difflib.SequenceMatcher(None, k, kk).ratio() for kk in c["keys"]), -RANK[c["subtype"]], i)
                  for i, c in enumerate(pool) if c["keys"]]
        if scored:
            sc, _, i = max(scored)
            if sc >= 0.82:
                best, how = pool[i], f"fuzzy {sc:.2f} -> {pool[i]['names'][0]}"
    rec = dict(h, matched=how)
    if best is not None:
        g = best["geom"].simplify(0.0008, preserve_topology=True)
        m = mapping(g)
        polys = [m["coordinates"]] if m["type"] == "Polygon" else m["coordinates"]
        rec["polys"] = [[[[round(x, 4), round(y, 4)] for x, y in ring] for ring in poly] for poly in polys]
    else:
        unmatched.append(h["name"] + " / " + h["province"])
    out.append(rec)

print("matched", sum(1 for o in out if "polys" in o), "of", len(out))
print("fuzzy:", [o["name"] + " ~ " + o["matched"] for o in out if o["matched"].startswith("fuzzy")])
print("unmatched:", unmatched)
json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
