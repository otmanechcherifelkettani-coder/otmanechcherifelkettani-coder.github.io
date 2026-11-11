"""Classify Overture places into labs / hospitals-clinics / doctors / dentists and build the map page.

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

# ---------- classification rules ----------
LAB_CATS = {"laboratory_testing", "b2b_clinical_lab", "medical_laboratory", "pathology_lab"}
LAB_NAME = re.compile(
    r"^\s*(laboratoire|labo)\b|analyses?\s+m[ée]dical|centre\s+de\s+biologie|\bbiolog|institut\s+pasteur|mختبر|مختبر",
    re.I)
LAB_EXCL = re.compile(
    r"dentaire|proth[eè]s|photo|zoopole|novovet|v[ée]t[ée]rin|sanofi|sterifil|fillmed|coudon|radiolog|neuroclinique|"
    r"\bhse\b|methc|complexe sportif|lpee|essais|structures|sols|roches|التجارب|تصوير|filorga|chlorophylle|lamapro|oculaire|cosm|pharmaceut|liman",
    re.I)

HOSP_CATS = {"hospital", "emergency_department", "surgery_center", "outpatient_care_facility", "medical_center",
             "dialysis_clinic", "maternity_center", "fertility_clinic", "blood_and_plasma_donation_center"}
HOSP_NAME = re.compile(r"\bclinique\b|polyclinique|h[oô]pital|\bchu\b|centre\s+hospitalier|مصحة|مستشفى", re.I)
DOC_CATS = {"doctors_office", "family_practice", "internal_medicine", "cardiology", "dermatology",
            "obstetrics_and_gynecology", "pediatric_clinic", "gastroenterology", "rheumatology",
            "ear_nose_and_throat", "pulmonology", "endocrinology", "oncology", "neurology", "urology", "nephrology",
            "psychiatry", "allergy_and_immunology", "orthopedics", "gerontology", "surgery",
            "plastic_and_reconstructive_surgery", "vision_or_eye_care_clinic", "reproductive_perinatal_and_womens_care",
            "prenatal_and_perinatal_care", "neuropathology", "behavioral_or_mental_health_clinic",
            "osteopathic_medicine", "radiology", "infectious_disease", "hematology", "anesthesiology",
            "sports_medicine", "pediatrics", "general_practice"}
DOC_NAME = re.compile(
    r"^\s*(dr\.?|docteur|pr\.?\s|professeur)\b|\bdr\.?\s|cabinet\s+(m[ée]dical|de\s+m[ée]decine|du\s+dr|de\s+dr|dr)|"
    r"centre\s+(de\s+sant[ée]|m[ée]dical)|الدكتور|طبيب",
    re.I)
DENT_CATS = {"dental_clinic", "cosmetic_dentistry", "general_dentistry", "orthodontics", "pediatric_dentistry",
             "prosthodontics", "periodontics", "oral_and_maxillofacial_surgery", "endodontics"}
DENT_NAME = re.compile(r"dentaire|dentiste|dental|orthodont", re.I)
# names that look medical but are not (vets, beauty, gadgets)
NOT_MED = re.compile(
    r"v[ée]t[ée]rin|\bvet\b|bijou|phone|stone|esth[ée]ti|aesthetic|botox|filler|beaut|spa\b|laser|amincis|media\b|"
    r"optique|pharmacie|\bpara\b|kin[ée]|r[ée][ée]ducation|physio|orthophon|hijama|حجامة|صيدلية|تلقيح|simulation|"
    r"psychanalyse|compl[ée]mentaire|التكميلي|looxwell", re.I)
NON_MED_PRIMARY = {"veterinarian", "beauty_salon", "spa", "eyewear_store", "mobile_phone_store", "clothing_store",
                   "public_relations", "janitorial_service", "electronic_equipment_supplier", "boat_dealer",
                   "pharmacy", "travel_and_transportation", "education", "nail_salon", "hair_salon"}


SPECIALTY = re.compile(
    r"dermato|ophtalm|gyn[ée]co|cardiolog|cardio\b|p[ée]diatr|endocrin|diab[ée]to|gastro|pneumo|n[ée]phro|neurolog|"
    r"urolog|rhumato|oncolog|canc[ée]ro|psychiatr|\borl\b|oto-rhino|traumato|orthop[ée]d|g[ée]n[ée]raliste|"
    r"m[ée]decine (g[ée]n[ée]rale|interne)|interniste|h[ée]matolog|infectiolog|allergolog|chirurgien(?! esth)|"
    r"maladies du sommeil|طبيب|أمراض", re.I)
VET = re.compile(r"v[ée]t[ée]rin|\bvet\b", re.I)


def classify(r):
    name = (r.get("name") or "").strip()
    prim = r.get("primary")
    hier = r.get("hierarchy") or []
    is_health = bool(hier) and hier[0] == "health_care"
    # labs
    if (prim in LAB_CATS or (LAB_NAME.search(name) and (is_health or prim is None))) and not LAB_EXCL.search(name):
        return "L"
    if prim in NON_MED_PRIMARY:
        return None
    if prim in DENT_CATS or (DENT_NAME.search(name) and (is_health or prim is None)):
        return "T"
    # a named medical specialty wins over aesthetic/laser wording (dermatologists, ophthalmologists ...)
    if SPECIALTY.search(name) and (is_health or prim is None) and not VET.search(name):
        return "H" if HOSP_NAME.search(name) else "D"
    if NOT_MED.search(name):
        return None
    medical = is_health or prim is None
    if HOSP_NAME.search(name) and medical:
        return "H"
    if DOC_NAME.search(name) and medical:
        return "D"
    if prim in HOSP_CATS:
        return "H"
    if prim in DOC_CATS:
        return "D"
    return None


pts = []
counts = {}
for r in places:
    c = classify(r)
    if not c:
        continue
    counts[c] = counts.get(c, 0) + 1
    pts.append([round(r["lat"], 5), round(r["lon"], 5), c, r.get("name") or "(sans nom)", r.get("primary") or "", "Overture"])
print("overture:", counts)

# ---------- OpenStreetMap (optional 4th argument: Overpass JSON) ----------
OSM_CLASS = {"laboratory": "L", "hospital": "H", "clinic": "H", "doctors": "D", "doctor": "D", "dentist": "T"}


def classify_osm(t):
    name = t.get("name") or t.get("name:fr") or t.get("name:ar") or ""
    kind = t.get("healthcare") or t.get("amenity")
    if kind in ("pharmacy", "veterinary") or t.get("amenity") in ("pharmacy", "veterinary"):
        return None, name
    if (LAB_NAME.search(name) or re.search(r"\w{3,}lab\b|^laboratory$", name, re.I)) and not LAB_EXCL.search(name):
        return "L", name  # the name says lab even when the OSM tag says clinic/doctor
    if kind in OSM_CLASS:
        c = OSM_CLASS[kind]
        if c != "L" and DENT_NAME.search(name):
            return "T", name
        if c != "L" and NOT_MED.search(name) and not SPECIALTY.search(name):
            return None, name
        if c == "L" and LAB_EXCL.search(name):
            return None, name
        if c == "H" and DOC_NAME.search(name) and not HOSP_NAME.search(name):
            c = "D"  # amenity=clinic used for a single doctor's cabinet
        return c, name
    # untagged or other healthcare values: fall back to the name rules
    return classify({"name": name, "primary": None, "hierarchy": []}), name


if len(sys.argv) > 4:
    osm_counts = {}
    for e in json.load(open(sys.argv[4]))["elements"]:
        t = e.get("tags", {})
        c, name = classify_osm(t)
        if not c:
            continue
        lat, lon = (e["lat"], e["lon"]) if "lat" in e else (e["center"]["lat"], e["center"]["lon"])
        osm_counts[c] = osm_counts.get(c, 0) + 1
        kind = t.get("healthcare") or t.get("amenity") or ""
        spec = t.get("healthcare:speciality")
        pts.append([round(lat, 5), round(lon, 5), c, name or "(sans nom)", kind + (f" · {spec}" if spec else ""), "OSM"])
    print("osm:", osm_counts)
# drop duplicate listings: same class, same normalised name, within 200 m
import math, unicodedata


def norm(n):
    n = unicodedata.normalize("NFKD", n.lower())
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = re.sub(r"\b(clinique|clinic|clinica|polyclinique|cabinet|laboratoire|laboratory|labo|lab|centre|center|"
               r"medical|medicale|medicales|analyses?|dr|docteur|de|du|la|le|d|l|des|et|casablanca|maroc)\b", " ", n)
    return re.sub(r"[^a-z0-9\u0600-\u06ff]+", "", n)


def same_name(a, b):
    if not a or not b:
        return False
    if a == b or (min(len(a), len(b)) >= 5 and (a in b or b in a)):
        return True
    # tolerate small spelling differences between sources
    import difflib
    return min(len(a), len(b)) >= 6 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.85


def metres(p, q):
    return math.hypot((p[0] - q[0]) * 110540, (p[1] - q[1]) * 92800)


# drop duplicates: same class and matching name within 300 m, or an unnamed point within 40 m of the same class
kept = []
for p in pts:
    k = norm(p[3]) if p[3] != "(sans nom)" else ""
    dup = False
    for q in kept:
        if q[2] != p[2] or abs(q[0] - p[0]) > 0.003 or abs(q[1] - p[1]) > 0.0035:
            continue
        kq = norm(q[3]) if q[3] != "(sans nom)" else ""
        d = metres(p, q)
        if (d <= 300 and same_name(k, kq)) or ((not k or not kq) and d <= 40):
            dup = True
            if q[5] != p[5] and p[5] not in q[5]:
                q[5] = q[5] + "+" + p[5]
            break
    if not dup:
        kept.append(p)
print("duplicates removed:", len(pts) - len(kept))
from collections import Counter
print("by source:", Counter(p[5] for p in kept))
pts = kept
counts = {}
for p in pts:
    counts[p[2]] = counts.get(p[2], 0) + 1
print("classified:", counts)

labels = [{"n": d["name"], "t": d["subtype"], "lat": round(d["lat"], 5), "lon": round(d["lon"], 5)}
          for d in divs if d["subtype"] in ("neighborhood", "macrohood", "microhood") and d["name"]]

# merge road segments by class into fewer multi-lines
roads = {}
for rd in ctx["roads"]:
    roads.setdefault(rd["cls"], []).extend(rd["lines"])
# keep the arrondissement / commune polygons (drop prefecture-scale 'county' shapes, keep for outline)
areas = [{"n": a["name"], "t": a["subtype"], "p": a["polys"]} for a in ctx["areas"]]

data = {"pts": pts, "labels": labels, "roads": roads, "areas": areas,
        "meta": {"source": "Overture Maps Foundation, Places + Divisions + Transportation, release 2026-10-21.0",
                 "counts": counts}}
(HERE / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))

tpl = (HERE / "template.html").read_text()
page = (tpl.replace("/*__LEAFLET_CSS__*/", (HERE / "vendor" / "leaflet.css").read_text())
        .replace("/*__ANALYSIS__*/", (HERE / "analysis.js").read_text())
        .replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")))
# artifact.html: bare body content (the artifact host adds the document skeleton)
(HERE / "artifact.html").write_text(page)
# index.html: standalone document for GitHub Pages
(HERE / "index.html").write_text(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<style>body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n' + page + '\n</body>\n</html>\n')
print("wrote index.html", (HERE / "index.html").stat().st_size // 1024, "KB")
