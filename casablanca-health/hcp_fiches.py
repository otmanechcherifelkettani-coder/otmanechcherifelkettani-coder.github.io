"""Extract socio-economic indicators per commune from HCP "Fiches communales RGPH 2024" (Casablanca-Settat)
and add them to communes.json, together with an affluence index (income proxy).

HCP does not publish household income by commune. The index combines the commune indicators that track
income most directly (higher education, share living in apartments or villas, slums, multidimensional poverty,
unemployment, illiteracy). Each indicator is standardised across the region's communes (z-score), signed so that higher =
better off, averaged, and rescaled so the population-weighted regional mean is 100.

Usage: python3 hcp_fiches.py <dir with downloaded fiche PDFs> communes.json
"""
import glob
import json
import re
import statistics
import sys
import unicodedata

import pdfplumber

DIR, COMMUNES = sys.argv[1:3]
NUM = r"(\d+(?:[.,]\d+)?)"
PATTERNS = {
    "pop": r"population l[ée]gale de (?:la commune|l.arrondissement|la municipalit[ée]) de .*? est de (\d+)",
    "illiteracy": r"10 ans et plus, " + NUM + r"\s*% sont\s+analphab",
    "age_u15": r"Selon l.[âa]ge, " + NUM + r"\s*% ont moins de 15 ans",
    "age_60p": r"et " + NUM + r"\s*% ont 60 ans et plus",
    "higher_edu": NUM + r"\s*% le niveau sup[ée]rieur",
    "unemployment": r"taux de ch[ôo]mage.*?il est de " + NUM + r"\s*%",
    "owners": NUM + r"\s*% sont propri[ée]taires",
    "apartments": NUM + r"\s*% habitent des appartements",
    "villas": NUM + r"\s*% vivent dans des\s+villas",
    "slums": NUM + r"\s*% (?:occupent des maisons sommaires|des m[ée]nages vivent dans des logements de type sommaire)",
    "moroccan_house": NUM + r"\s*% (?:des m[ée]nages de la commune r[ée]sident dans des maisons marocaines|habitent des maisons marocaines)",
    "rural_house": NUM + r"\s*% (?:se logent dans des habitats de type rural|des m[ée]nages de la commune r[ée]sident dans des logements\s+de type rural)",
    "poverty": r"pauvret[ée] multidimensionnelle au niveau de (?:la commune|l.arrondissement|la municipalit[ée])\s+s.est [ée]tabli [àa] " + NUM,
    "poverty14": r"pauvret[ée] multidimensionnelle.*?\(contre " + NUM + r"\s*% en 2014\)",
    "establishments": r"(\d[\d  ]*) [ée]tablissements [àa] but lucratif",
}


def num(s):
    return float(s.replace(",", ".").replace(" ", "").replace(" ", ""))


def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"^(commune|arrondissement|municipalite)\s+(?:(?:de la|du|des|de)\s+|d['’]|de l['’])?", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


fiches = {}
for path in sorted(glob.glob(DIR + "/*.pdf")):
    with pdfplumber.open(path) as pdf:
        name = None
        for pg in pdf.pages:
            full = pg.extract_text() or ""
            m = re.search(r"\n((?:Commune|Arrondissement|Municipalit[ée])\s+[^\n]+)\nDirection R[ée]gionale", full)
            if m:
                name = m.group(1).strip()
                continue
            if name and "CARACT" in full:
                w = pg.width
                text = " ".join((pg.crop((0, 0, w / 2, pg.height)).extract_text() or "",
                                 pg.crop((w / 2, 0, w, pg.height)).extract_text() or ""))
                text = re.sub(r"\s+", " ", text)
                rec = {"fiche_name": name, "file": path.split("/")[-1]}
                for key, pat in PATTERNS.items():
                    mm = re.search(pat, text, re.I)
                    rec[key] = num(mm.group(1)) if mm else None
                # apartments + villas: read directly (urban sheets) or as the remainder (rural sheets)
                if rec["apartments"] is not None and rec["villas"] is not None:
                    rec["modern_housing"] = rec["apartments"] + rec["villas"]
                elif None not in (rec["moroccan_house"], rec["slums"], rec["rural_house"]):
                    rec["modern_housing"] = max(0.0, 100 - rec["moroccan_house"] - rec["slums"] - rec["rural_house"])
                else:
                    rec["modern_housing"] = None
                fiches[norm(name)] = rec
                name = None
print(len(fiches), "commune sheets parsed")

communes = json.load(open(COMMUNES))
matched = 0
for c in communes:
    rec = fiches.get(norm(c["name"]))
    if rec is None:  # small spelling differences (e.g. "Ain Chock" vs "Aïn Chock")
        import difflib
        best = difflib.get_close_matches(norm(c["name"]), list(fiches), n=1, cutoff=0.85)
        rec = fiches.get(best[0]) if best else None
    c["socio"] = {k: v for k, v in (rec or {}).items() if k not in ("fiche_name", "file")} if rec else None
    if rec:
        matched += 1
        if rec.get("pop") and abs(rec["pop"] - c["pop"]) > 1:
            print("population differs for", c["name"], rec["pop"], c["pop"])
print("matched", matched, "of", len(communes), "| without sheet:", [c["name"] for c in communes if not c["socio"]])

# ---- affluence index ----
SIGNS = {"higher_edu": 1, "modern_housing": 1, "slums": -1, "poverty": -1, "unemployment": -1, "illiteracy": -1}
stats = {}
for k in SIGNS:
    vals = [c["socio"][k] for c in communes if c["socio"] and c["socio"].get(k) is not None]
    stats[k] = (statistics.mean(vals), statistics.pstdev(vals) or 1)
for c in communes:
    s = c["socio"]
    if not s:
        c["affluence_z"] = None
        continue
    zs = [SIGNS[k] * (s[k] - stats[k][0]) / stats[k][1] for k in SIGNS if s.get(k) is not None]
    c["affluence_z"] = sum(zs) / len(zs) if zs else None
have = [c for c in communes if c["affluence_z"] is not None]
wmean = sum(c["affluence_z"] * c["pop"] for c in have) / sum(c["pop"] for c in have)
spread = statistics.pstdev([c["affluence_z"] for c in have]) or 1
for c in communes:
    # 100 = population-weighted regional mean; ±1 standard deviation across communes = ±25 points
    c["affluence"] = round(100 + 25 * (c["affluence_z"] - wmean) / spread, 1) if c["affluence_z"] is not None else None
json.dump(communes, open(COMMUNES, "w"), ensure_ascii=False, separators=(",", ":"))
top = sorted(have, key=lambda c: -c["affluence"])
print("most affluent:", [(c["name"], c["affluence"]) for c in top[:8]])
print("least affluent:", [(c["name"], c["affluence"]) for c in top[-5:]])
