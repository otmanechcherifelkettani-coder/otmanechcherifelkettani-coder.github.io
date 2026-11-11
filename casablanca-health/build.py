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
    r"\bhse\b|methc|complexe sportif|lpee|essais|filorga|chlorophylle|lamapro|oculaire|cosm|pharmaceut|liman",
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
    pts.append([round(r["lat"], 5), round(r["lon"], 5), c, r.get("name") or "(sans nom)", r.get("primary") or ""])
# drop duplicate listings: same class, same normalised name, within 200 m
import math, unicodedata


def norm(n):
    n = unicodedata.normalize("NFKD", n.lower())
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = re.sub(r"\b(clinique|clinic|cabinet|laboratoire|labo|dr|docteur|de|du|la|le|d|l|des|casablanca)\b", " ", n)
    return re.sub(r"[^a-z0-9\u0600-\u06ff]+", "", n)


kept = []
for p in pts:
    k = norm(p[3])
    dup = False
    for q in kept:
        if q[2] == p[2] and abs(q[0] - p[0]) < 0.002 and abs(q[1] - p[1]) < 0.0025:
            kq = norm(q[3])
            if k and kq and (k == kq or (min(len(k), len(kq)) >= 5 and (k in kq or kq in k))):
                dup = True
                break
    if not dup:
        kept.append(p)
print("duplicates removed:", len(pts) - len(kept))
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
