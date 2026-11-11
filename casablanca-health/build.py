"""Merge Overture, OpenStreetMap and (optionally) Google places, classify them with classify.py, and build the map page.

Usage: python3 build.py <places.json> <divisions.json> <context.json>
Writes data.json (classified points + base map) and index.html (template.html with data inlined).
"""
import json
import re
import sys
from pathlib import Path

places_p, divs_p, ctx_p = sys.argv[1:4]
HERE = Path(__file__).parent

places = json.load(open(places_p))
divs = json.load(open(divs_p))
ctx = json.load(open(ctx_p))

# ---------- classification (shared rules in classify.py) ----------
import os
from classify import classify as classify_place, MAIN

# point layout: [lat, lon, main class, name, source category, source, sub class]  (+ commune index appended later)
pts = []
counts = {}


def add(lat, lon, name, cats, catlabel, source):
    r = classify_place(name, cats)
    if not r:
        return
    main, sub = r
    counts[source + ":" + sub] = counts.get(source + ":" + sub, 0) + 1
    pts.append([round(lat, 5), round(lon, 5), main, name or "(sans nom)", catlabel or "", source, sub])


for r in places:
    if (r.get("status") or "").lower() == "closed":
        continue
    add(r["lat"], r["lon"], r.get("name"), {r.get("primary")} | set(r.get("alternate") or []), r.get("primary"),
        "Overture")

# ---------- OpenStreetMap (optional 4th argument: Overpass JSON) ----------
if len(sys.argv) > 4:
    for e in json.load(open(sys.argv[4]))["elements"]:
        t = e.get("tags", {})
        name = t.get("name") or t.get("name:fr") or t.get("name:ar") or ""
        cats = {t.get("amenity"), t.get("healthcare")} | set(re.split(r"[;,]", t.get("healthcare:speciality", "")))
        lat, lon = (e["lat"], e["lon"]) if "lat" in e else (e["center"]["lat"], e["center"]["lon"])
        spec = t.get("healthcare:speciality")
        add(lat, lon, name, cats, (t.get("healthcare") or t.get("amenity") or "") + (f" · {spec}" if spec else ""), "OSM")

# ---------- Google Places (optional, env GOOGLE_PLACES=path[,path...]) ----------
# Kept out of the public repo build: Google's terms restrict storing and redistributing Places content.
if os.environ.get("GOOGLE_PLACES"):
    seen_ids = set()
    for path in os.environ["GOOGLE_PLACES"].split(","):
        for p in json.load(open(path))["places"]:
            if p["id"] in seen_ids or p.get("status") in ("CLOSED_PERMANENTLY", "CLOSED_TEMPORARILY"):
                continue
            seen_ids.add(p["id"])
            cats = {p.get("primary")} | set(p.get("types") or [])
            if any(st.startswith("lab") for st in p.get("streams") or []):
                cats.add("lab_search")  # found by the "laboratoire d'analyses médicales" keyword search
            add(p["lat"], p["lon"], p.get("name"), cats, p.get("primary"), "Google")

from collections import Counter
print("classified by source:sub:", dict(sorted(counts.items())))
# drop duplicate listings: same class, same normalised name, within 200 m
import math, unicodedata


def norm(n):
    latin = re.sub(r"[\u0600-\u06ff]+", " ", n)
    if re.search(r"[A-Za-z]{3}", latin):
        n = latin  # bilingual names: compare the Latin part only
    n = unicodedata.normalize("NFKD", n.lower())
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = re.sub(r"\b(clinique|clinic|clinica|polyclinique|cabinet|laboratoire|laboratory|labo|lab|centre|center|"
               r"medical|medicale|medicales|analyses?|dr|docteur|de|du|la|le|d|l|des|et|casablanca|maroc|clinical|hospital|"
               r"hopital|medico|chirurgicale|multidisciplinaire|privee?|international|internationale)\b", " ", n)
    return re.sub(r"[^a-z0-9\u0600-\u06ff]+", "", n)


def same_name(a, b):
    if not a or not b:
        return False
    a, b = a.rstrip("s"), b.rstrip("s")
    if a == b or (min(len(a), len(b)) >= 5 and (a in b or b in a)):
        return True
    # tolerate small spelling differences between sources
    import difflib
    return min(len(a), len(b)) >= 6 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.85


def metres(p, q):
    return math.hypot((p[0] - q[0]) * 110540, (p[1] - q[1]) * 92800)


# drop duplicates: same class and matching name within 300 m (1.5 km for labs), or an unnamed point within 40 m
kept = []
for p in pts:
    k = norm(p[3]) if p[3] != "(sans nom)" else ""
    dup = False
    for q in kept:
        if q[2] != p[2] or abs(q[0] - p[0]) > 0.015 or abs(q[1] - p[1]) > 0.018:
            continue
        kq = norm(q[3]) if q[3] != "(sans nom)" else ""
        d = metres(p, q)
        # lab names are distinctive and sources place them up to ~1 km apart; other types: 300 m
        reach = 1500 if p[2] == "L" and min(len(k), len(kq)) >= 5 else 300
        if (d <= reach and same_name(k, kq)) or ((not k or not kq) and d <= 40):
            dup = True
            if q[5] != p[5] and p[5] not in q[5]:
                q[5] = q[5] + "+" + p[5]
            if q[6] in ("DU", "MC") and p[6] not in ("DU",):
                q[6] = p[6]  # keep the more specific label
            break
    if not dup:
        kept.append(p)
print("duplicates removed:", len(pts) - len(kept))
from collections import Counter
print("by source:", Counter(p[5] for p in kept))
pts = kept
counts = Counter(p[6] for p in pts)
print("after de-duplication:", dict(sorted(counts.items())))

# ---------- region clip (optional env REGION=region.json from fetch_region.py) ----------
provinces, region_outline = [], None
if os.environ.get("REGION"):
    from shapely.geometry import shape, Point, mapping
    from shapely.prepared import prep
    reg = json.load(open(os.environ["REGION"]))
    rgeom = shape(reg["region"]["geom"])
    rprep = prep(rgeom.buffer(0.005))
    before = len(pts)
    pts = [p for p in pts if rprep.contains(Point(p[1], p[0]))]
    print("outside region removed:", before - len(pts))

    def rings(g):
        m = mapping(g.simplify(0.003))
        polys = [m["coordinates"]] if m["type"] == "Polygon" else m["coordinates"]
        return [[[[round(c[0], 4), round(c[1], 4)] for c in ring] for ring in poly] for poly in polys]

    for p in reg["provinces"]:
        nm = re.sub(r"^(Province|Préfecture)\s+(de la|de l'|du|des|de|d'|d’)\s*", "", p["name"])
        provinces.append({"n": nm, "p": rings(shape(p["geom"]))})
    region_outline = rings(rgeom)
    counts = Counter(p[6] for p in pts)
    print("in region:", dict(sorted(counts.items())))

labels = [{"n": d["name"], "t": d["subtype"], "lat": round(d["lat"], 5), "lon": round(d["lon"], 5)}
          for d in divs if d["subtype"] in ("neighborhood", "macrohood", "microhood", "locality") and d["name"]]

# merge road segments by class into fewer multi-lines
roads = {}
for rd in ctx["roads"]:
    roads.setdefault(rd["cls"], []).extend(rd["lines"])
# keep the arrondissement / commune polygons (drop prefecture-scale 'county' shapes, keep for outline)
areas = [{"n": a["name"], "t": a["subtype"], "p": a["polys"]} for a in ctx["areas"]]

# ---------- communes with HCP RGPH 2024 population (optional env COMMUNES=communes.json) ----------
communes = []
if os.environ.get("COMMUNES"):
    from shapely.geometry import Point, shape
    from shapely.strtree import STRtree
    raw = [c for c in json.load(open(os.environ["COMMUNES"])) if c.get("polys")]
    geoms = [shape({"type": "MultiPolygon", "coordinates": c["polys"]}).buffer(0) for c in raw]
    tree = STRtree(geoms)
    tally = [{"H": 0, "D": 0, "T": 0, "L": 0, "sub": {}} for _ in raw]
    unassigned = 0
    for p in pts:
        pt = Point(p[1], p[0])
        hits = [i for i in tree.query(pt) if geoms[i].contains(pt)]
        if not hits:
            unassigned += 1
            p.append(-1)
            continue
        i = int(min(hits, key=lambda j: geoms[j].area))  # smallest unit wins where boundaries overlap
        tally[i][p[2]] += 1
        tally[i]["sub"][p[6]] = tally[i]["sub"].get(p[6], 0) + 1
        p.append(i)
    print("points outside any commune polygon:", unassigned)
    for c, t in zip(raw, tally):
        communes.append({"n": re.sub(r"^(Commune|Arrondissement|Municipalité)\s+(de la|de l'|du|des|de|d'|d’)?\s*", "", c["name"]),
                         "full": c["name"], "ar": c.get("name_ar"), "code": c["code"], "prov": c["province"],
                         "pop": c["pop"], "hh": c["households"], "pop14": c.get("pop14"),
                         "growth": c.get("growth"), **t, "p": c["polys"]})

# residents on a 400 m grid (fetch_buildings.py): [lat, lon, residents 2024, growth %/yr, commune index]
popcells = json.load(open(os.environ["POPCELLS"])) if os.environ.get("POPCELLS") else []

data = {"pts": pts, "labels": labels, "roads": roads, "areas": areas, "provinces": provinces, "region": region_outline,
        "communes": communes, "popcells": popcells,
        "meta": {"source": "Overture Maps Foundation, Places + Divisions + Transportation, release 2026-10-21.0",
                 "counts": dict(counts)}}
OUTDIR = Path(os.environ.get("OUT_DIR", HERE))
OUTDIR.mkdir(parents=True, exist_ok=True)
(OUTDIR / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))

tpl = (HERE / "template.html").read_text()
page = (tpl.replace("/*__LEAFLET_CSS__*/", (HERE / "vendor" / "leaflet.css").read_text())
        .replace("/*__ANALYSIS__*/", (HERE / "analysis.js").read_text())
        .replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")))
# artifact.html: bare body content (the artifact host adds the document skeleton)
(OUTDIR / "artifact.html").write_text(page)
# index.html: standalone document for GitHub Pages
(OUTDIR / "index.html").write_text(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<style>body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n' + page + '\n</body>\n</html>\n')
print("wrote", OUTDIR, (OUTDIR / "index.html").stat().st_size // 1024, "KB")
