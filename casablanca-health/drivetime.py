"""Drive-time version of the site model (offline; the page combines the two channels with its α slider).

Same Huff model as analysis.js siteModel, but with drive time on the road graph (fetch_roads.py) instead of
straight-line distance, so catchments shrink where roads are slow and grow where they are fast:
  f(t) = max(t, 2 min)^−β (β = 2), outside option = a lab 8 min away, competitors within 30 min,
  demand within 25 min of the candidate. Residents use growth (3 years), affluence (γ = 1) and, in one variant, age.
Output drive.json: {"hex": metres, "k": k, "cands": [[lat, lon, cR_age, cR_noage, cP, minutes_to_nearest_lab,
                                                      labs_within_10_min], ...]}
Usage: python3 drivetime.py roads.npz data.json drive.json
"""
import json
import math
import sys
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

ROADS, DATA, OUT = sys.argv[1:4]
BETA, TMIN, OUTSIDE, RIVAL_LIMIT, DEMAND_LIMIT = 2.0, 2.0, 8.0, 30.0, 25.0   # minutes
HEX = 750.0                                                                   # candidate hexagon edge, metres
YEARS, GAMMA = 3, 1.0
WEIGHTS = {"HP": 3, "HU": 1, "CS": 1, "MC": 2, "HD": 0.5, "IM": 0, "HL": 0.5, "DG": 1.2, "DS": 1.5, "DL": 0.3, "DU": 1, "T": 0}
IN_HOUSE = {"HU": 0.5, "HP": 0.3}
LAT0, LON0 = 33.57, -7.6
KX, KY = math.cos(math.radians(LAT0)) * 111320, 110540
xy = lambda lat, lon: ((lon - LON0) * KX, (lat - LAT0) * KY)

g = np.load(ROADS)
n = len(g["lon"])
G = coo_matrix((np.concatenate([g["t"], g["t"]]) / 60.0,
                (np.concatenate([g["u"], g["v"]]), np.concatenate([g["v"], g["u"]]))), shape=(n, n)).tocsr()
ncomp, lab = connected_components(G, directed=False)
main = np.argmax(np.bincount(lab))
keep = np.where(lab == main)[0]
print(f"graph: {n} nodes, largest connected part {len(keep)} ({100 * len(keep) / n:.0f}%)", flush=True)
nx, ny = xy(g["lat"][keep], g["lon"][keep])
tree = cKDTree(np.c_[nx, ny])


def snap(lat, lon):
    """nearest road node and the extra minutes to reach it (20 km/h for the last stretch)"""
    x, y = xy(np.asarray(lat), np.asarray(lon))
    d, i = tree.query(np.c_[x, y])
    return keep[i], d / (20000 / 60)


data = json.load(open(DATA))
com = data["communes"]
pts = data["pts"]

# ---- demand nodes ----
cells = data["popcells"]
lat = np.array([c[0] for c in cells]); lon = np.array([c[1] for c in cells])
node_r, extra_r = snap(lat, lon)
v_noage = np.array([c[2] * (1 + (c[3] or 0) / 100) ** YEARS * ((com[c[4]].get("aff") or 100) / 100) ** GAMMA
                    for c in cells])
v_age = v_noage * np.array([com[c[4]].get("ageIdx") or 1 for c in cells])
pre = [p for p in pts if p[2] != "L" and WEIGHTS.get(p[6], 0) > 0]
node_p, extra_p = snap([p[0] for p in pre], [p[1] for p in pre])
w_p = np.array([WEIGHTS[p[6]] for p in pre])
k = v_age.sum() / w_p.sum()
print(len(cells), "resident cells,", len(pre), "prescribers, k =", round(k, 1), flush=True)

dn = np.unique(np.concatenate([node_r, node_p]))          # demand nodes
pos = {v: i for i, v in enumerate(dn)}
R_age = np.zeros(len(dn)); R_no = np.zeros(len(dn)); P = np.zeros(len(dn)); EX = np.zeros(len(dn))
for nd, ex, va, vn in zip(node_r, extra_r, v_age, v_noage):
    i = pos[nd]; R_age[i] += va; R_no[i] += vn; EX[i] = max(EX[i], ex)
for nd, ex, w in zip(node_p, extra_p, w_p):
    i = pos[nd]; P[i] += k * w; EX[i] = max(EX[i], ex)

f = lambda t: np.maximum(t, TMIN) ** -BETA

# ---- competition at each demand node ----
rivals = [(p[0], p[1], 1.0) for p in pts if p[6] == "L"] + \
         [(p[0], p[1], IN_HOUSE[p[6]]) for p in pts if p[6] in IN_HOUSE]
r_node, r_ex = snap([r[0] for r in rivals], [r[1] for r in rivals])
r_A = np.array([r[2] for r in rivals])
S = np.full(len(dn), f(OUTSIDE))
t0 = time.time()
uniq, inv = np.unique(r_node, return_inverse=True)
for b in range(0, len(uniq), 64):
    batch = uniq[b:b + 64]
    D = dijkstra(G, indices=batch, limit=RIVAL_LIMIT)[:, dn]
    for j, row in enumerate(D):
        members = np.where(inv == b + j)[0]
        ok = np.isfinite(row)
        for m in members:
            S[ok] += r_A[m] * f(row[ok] + r_ex[m] + EX[ok])
print(f"competition computed from {len(uniq)} rival nodes in {time.time() - t0:.0f}s", flush=True)
lab_nodes = np.unique(np.array([nd for nd, r in zip(r_node, rivals) if r[2] == 1.0]))

# ---- candidates: hexagon centres (same grid convention as the page) near enough demand ----
dxy = np.c_[xy(np.concatenate([lat, [p[0] for p in pre]]), np.concatenate([lon, [p[1] for p in pre]]))]
dv = np.concatenate([v_age, k * w_p])
dtree = cKDTree(dxy)
hw = math.sqrt(3) * HEX
xmin, ymin = dxy.min(0); xmax, ymax = dxy.max(0)
cand = []
for r in range(int(ymin // (1.5 * HEX)) - 1, int(ymax // (1.5 * HEX)) + 2):
    y = r * 1.5 * HEX
    off = hw / 2 if r & 1 else 0
    x = math.floor(xmin / hw) * hw - hw + off
    while x <= xmax + hw:
        near = dtree.query_ball_point([x, y], 1500)
        if near and dv[near].sum() >= 300:
            cand.append((x, y))
        x += hw
cand = np.array(cand)
clat = cand[:, 1] / KY + LAT0; clon = cand[:, 0] / KX + LON0
c_node, c_ex = snap(clat, clon)
print(len(cand), "candidate sites", flush=True)

out = []
t0 = time.time()
for b in range(0, len(cand), 64):
    idx = np.arange(b, min(b + 64, len(cand)))
    Dall = dijkstra(G, indices=c_node[idx], limit=RIVAL_LIMIT)
    D = Dall[:, dn]
    DL = Dall[:, lab_nodes]
    for j, i in enumerate(idx):
        t = D[j] + c_ex[i] + EX
        ok = t <= DEMAND_LIMIT
        fc = f(t[ok])
        share = fc / (fc + S[ok])
        tl = DL[j] + c_ex[i]
        fin = tl[np.isfinite(tl)]
        out.append([round(float(clat[i]), 5), round(float(clon[i]), 5), round(float((R_age[ok] * share).sum()), 1),
                    round(float((R_no[ok] * share).sum()), 1), round(float((P[ok] * share).sum()), 1),
                    round(float(fin.min()), 1) if fin.size else None, int((fin <= 10).sum())])
    if b % 640 == 0:
        print(f"  {b + len(idx)}/{len(cand)} candidates, {time.time() - t0:.0f}s", flush=True)

json.dump({"hex": HEX, "k": k, "params": {"beta": BETA, "outside_min": OUTSIDE, "demand_limit_min": DEMAND_LIMIT,
                                          "years": YEARS, "gamma": GAMMA}, "cands": out},
          open(OUT, "w"), separators=(",", ":"))
print("wrote", len(out), "candidates")
