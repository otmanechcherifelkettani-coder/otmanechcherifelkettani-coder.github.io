"""Parse HCP 'Population légale ... RGPH 2014, Direction Casablanca-Settat' (pop_legal_2014.pdf) and add 2014
population + annual growth 2014-2024 to communes.json (in place).

Join: geographic code (2014 '06.141.01.01.' == 2024 '61410101'), else same name within the same province code
(rural communes whose 'cercle' number changed between censuses).
Usage: python3 hcp_2014.py pop_legal_2014.pdf communes.json
"""
import json
import re
import sys
import unicodedata

import pdfplumber

PDF, COMMUNES = sys.argv[1:3]


def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\((arrond|mun)\.\)", "", s)
    s = re.sub(r"^(commune|arrondissement|municipalite)\s+(?:(?:de la|du|des|de)\s+|d['’]|de l['’])?", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


p14 = {}
with pdfplumber.open(PDF) as pdf:
    for pg in pdf.pages:
        for tb in pg.extract_tables():
            for r in tb:
                if not (r and r[0] and re.match(r"^06\.", r[0].strip())):
                    continue
                segs = [s for s in r[0].strip().split(".") if s]
                if len(segs) != 4:
                    continue  # region / province / cercle / "dont centre" rows
                code = str(int(segs[0])) + segs[1] + segs[2] + segs[3]
                p14[code] = {"name": (r[1] or "").replace("\n", " "), "pop": int(r[3].replace(",", "")),
                             "hh": int(r[2].replace(",", ""))}

communes = json.load(open(COMMUNES))
by_name = {}
for code, v in p14.items():
    by_name.setdefault((code[:4], norm(v["name"])), []).append(code)
used, how = set(), {"code": 0, "name": 0, "none": 0}
for c in communes:
    code = c["code"]
    hit = code if code in p14 else None
    if hit:
        how["code"] += 1
    else:
        cands = [k for k in by_name.get((code[:4], norm(c["name"])), []) if k not in used]
        hit = cands[0] if cands else None
        how["name" if hit else "none"] += 1
    if hit:
        used.add(hit)
        c["pop14"], c["hh14"] = p14[hit]["pop"], p14[hit]["hh"]
        c["growth"] = round(((c["pop"] / c["pop14"]) ** 0.1 - 1) * 100, 2)  # % per year, 2014-2024
    else:
        c["pop14"] = c["hh14"] = c["growth"] = None
print("joined:", how, "| unmatched:", [c["name"] for c in communes if c["pop14"] is None])
json.dump(communes, open(COMMUNES, "w"), ensure_ascii=False, separators=(",", ":"))
