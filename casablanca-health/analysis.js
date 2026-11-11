// Gap analysis: medical demand vs. laboratory supply on a hexagon grid.
// Shared by the map page and by `node analysis.js data.json` for a text summary.
(function (root) {
  const LAT0 = 33.57, LON0 = -7.6;
  const KX = Math.cos(LAT0 * Math.PI / 180) * 111320, KY = 110540;
  const toXY = (lat, lon) => [(lon - LON0) * KX, (lat - LAT0) * KY];
  const toLL = (x, y) => [y / KY + LAT0, x / KX + LON0];

  function bucketIndex(items, cell) {
    const m = new Map();
    for (const it of items) {
      const k = Math.floor(it.x / cell) + ',' + Math.floor(it.y / cell);
      if (!m.has(k)) m.set(k, []);
      m.get(k).push(it);
    }
    return {
      near(x, y, r) {
        const out = [], c0 = Math.floor((x - r) / cell), c1 = Math.floor((x + r) / cell);
        const d0 = Math.floor((y - r) / cell), d1 = Math.floor((y + r) / cell);
        for (let i = c0; i <= c1; i++) for (let j = d0; j <= d1; j++) {
          const b = m.get(i + ',' + j); if (!b) continue;
          for (const it of b) { const d = Math.hypot(it.x - x, it.y - y); if (d <= r) out.push([it, d]); }
        }
        return out;
      }
    };
  }

  // Default lab-test demand weight of each kind of prescriber (one GP cabinet = 1.2, see README "Formula").
  const WEIGHTS = { HP: 3, HU: 1, CS: 1, MC: 2, HD: 0.5, IM: 0, HL: 0.5, DG: 1.2, DS: 1.5, DL: 0.3, DU: 1, T: 0 };
  const SUB_LABEL = { L: 'Medical lab', LP: 'Pathology lab', HP: 'Private clinic', HL: 'Specialty clinic (eye, skin…)',
    HU: 'Public hospital', CS: 'Public health centre', MC: 'Medical centre / SOS médecins', HD: 'Dialysis centre',
    IM: 'Imaging centre', DG: 'General practitioner', DS: 'Specialist, many tests', DL: 'Specialist, few tests',
    DU: 'Doctor (specialty not stated)', T: 'Dentist' };

  function weightsFor(opts) {
    const w = Object.assign({}, WEIGHTS, opts.weights || {});
    if (opts.wH != null) w.HP = opts.wH;
    if (opts.wT != null) w.T = opts.wT ? 0.3 : 0;
    return w;
  }
  const isCompetitor = (p, opts) => p.c === 'L' && (p.s !== 'LP' || opts.includePatho);

  function points(data) {
    return data.pts.map(p => { const [x, y] = toXY(p[0], p[1]); return { lat: p[0], lon: p[1], c: p[2], name: p[3], cat: p[4], src: p[5], s: p[6] || p[2], x, y }; });
  }

  // opts: {hex (edge length m), radius (m), wH, wT, weights, minDemand, includePatho, province}
  function analyse(data, opts) {
    const pts = points(data);
    const wt = weightsFor(opts);
    const demandPts = pts.filter(p => p.c !== 'L' && (wt[p.s] || 0) > 0);
    const labs = pts.filter(p => isCompetitor(p, opts));
    const R = opts.radius;
    const di = bucketIndex(demandPts, 500), li = bucketIndex(labs, 500);
    const labsAll = bucketIndex(labs, 2000);
    const s = opts.hex, hw = Math.sqrt(3) * s;
    let xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
    for (const p of pts) { xmin = Math.min(xmin, p.x); xmax = Math.max(xmax, p.x); ymin = Math.min(ymin, p.y); ymax = Math.max(ymax, p.y); }
    const hexes = [];
    const r0 = Math.floor(ymin / (1.5 * s)) - 1, r1 = Math.ceil(ymax / (1.5 * s)) + 1;
    for (let r = r0; r <= r1; r++) {
      const y = r * 1.5 * s, off = (r & 1) ? hw / 2 : 0;
      for (let x = Math.floor(xmin / hw) * hw - hw + off; x <= xmax + hw; x += hw) {
        const near = di.near(x, y, R);
        if (!near.length) continue;
        let demand = 0; const n = { H: 0, D: 0, T: 0 };
        for (const [p] of near) { demand += wt[p.s] || 0; n[p.c]++; }
        const nl = li.near(x, y, R).length;
        // nearest lab distance (search widening)
        let nearest = Infinity;
        for (const rr of [R, 2500, 6000, 20000]) {
          const c = labsAll.near(x, y, rr);
          if (c.length) { nearest = Math.min(...c.map(v => v[1])); break; }
        }
        demand = Math.round(demand * 10) / 10;
        const score = demand / (nl + 1);
        const corners = [];
        for (let k = 0; k < 6; k++) { const a = Math.PI / 180 * (60 * k - 30); corners.push(toLL(x + s * Math.cos(a), y + s * Math.sin(a))); }
        const [lat, lon] = toLL(x, y);
        hexes.push({ x, y, lat, lon, demand, n, labs: nl, nearest, score, corners, qualifies: demand >= opts.minDemand });
      }
    }
    // Rank: greedy pick of best-scoring qualifying hexes, suppress overlapping catchments
    if (opts.province) for (const h of hexes) if (h.qualifies) h.prov = provinceOf(data, h.lat, h.lon);
    const cand = hexes.filter(h => h.qualifies && (!opts.province || h.prov === opts.province)).sort((a, b) => b.score - a.score || b.demand - a.demand);
    const picked = [];
    for (const h of cand) {
      if (picked.some(p => Math.hypot(p.x - h.x, p.y - h.y) < 1.6 * R)) continue;
      picked.push(h);
      if (picked.length >= (opts.topN || 15)) break;
    }
    return { hexes, top: picked, demandCount: demandPts.length, labCount: labs.length, pts };
  }

  // ---------------------------------------------------------------------------------------------------------
  // Site model (the "Best sites" tab): expected demand a NEW lab would capture at each candidate location.
  //   resident demand at z   R_z = residents_z · (1 + g_z)^years · (affluence_z / 100)^γ · age_z
  //     affluence_z: commune income proxy (HCP fiches communales 2024; 100 = regional average)
  //     age_z: commune test-use index from its age structure (under 15 ×0.4, 15–59 ×1, 60+ ×2.5; regional mean 1)
  //   prescriber demand at z P_z = k · prescriber weight_z      (k: both channels have the same regional total)
  //   pull at distance d     f(d) = max(d, 300 m)^−β            (or drive minutes, see data.drive)
  //   share won from z       P_cz = f(d_cz) / ( f(d_cz) + Σ_j A_j f(d_jz) + f(D0) )            (Huff model)
  //     A_j = incumbent strength (1 by default; raise it to stand in for collection points and home sampling)
  //           for medical labs, 0.5 for public hospitals and 0.3 for private clinics (in-house labs)
  //     f(D0) = "outside option": as attractive as a lab 3 km away (going further, hospital, not testing)
  //   channels               cR_c = Σ_z R_z P_cz ,  cP_c = Σ_z P_z P_cz          over z within maxDist of c
  //   combined score         S_c = α · cR_c + (1 − α) · cP_c
  //   rank: 'combined' (S), 'residents' (cR), 'prescribers' (cP), or 'robust' (worse of the two percentile ranks)
  function siteModel(data, opts) {
    const o = Object.assign({ alpha: 0.6, beta: 2, years: 3, gamma: 1, age: true, incumbent: 1, rank: 'combined',
      maxDist: 6000, hex: 500, includePatho: false, topN: 15, outside: 3000, inHouse: { HU: 0.5, HP: 0.3 },
      drive: false }, opts);
    const pts = points(data), wt = weightsFor(o);
    const labs = pts.filter(p => isCompetitor(p, o));
    const com = data.communes || [];
    const affOf = ci => (com[ci] || {}).aff || 100, ageOf = ci => (com[ci] || {}).ageIdx || 1;
    const res = (data.popcells || []).map(c => {
      const [x, y] = toXY(c[0], c[1]), aff = affOf(c[4]);
      const v = c[2] * Math.pow(1 + (c[3] || 0) / 100, o.years) * Math.pow(aff / 100, o.gamma) * (o.age ? ageOf(c[4]) : 1);
      return { x, y, v, pop: c[2], g: c[3], aff, ci: c[4] };
    });
    const pre = pts.filter(p => p.c !== 'L' && (wt[p.s] || 0) > 0).map(p => ({ x: p.x, y: p.y, v: wt[p.s] }));
    const totR = res.reduce((a, r) => a + r.v, 0) || 1, totP = pre.reduce((a, r) => a + r.v, 0) || 1;
    const k = totR / totP;
    const li = bucketIndex(labs, 2000), ri = bucketIndex(res, 1000), pi = bucketIndex(pre, 1000);
    let cands = [];
    if (o.drive && data.drive) {
      // drive-time results computed offline (drivetime.py) for β, years and γ at their defaults
      const s = data.drive.hex, ag = o.age ? 2 : 3;
      cands = data.drive.cands.map(r => {
        const [x, y] = toXY(r[0], r[1]), corners = [];
        for (let q = 0; q < 6; q++) { const a = Math.PI / 180 * (60 * q - 30); corners.push(toLL(x + s * Math.cos(a), y + s * Math.sin(a))); }
        return { x, y, lat: r[0], lon: r[1], cR: r[ag], cP: r[4] * k / data.drive.k, minutes: r[5], labs10: r[6], corners };
      });
    } else {
      const rivals = labs.map(p => Object.assign({ A: o.incumbent }, p))
        .concat(pts.filter(p => o.inHouse[p.s]).map(p => Object.assign({ A: o.inHouse[p.s] }, p)));
      const demand = res.map(r => ({ x: r.x, y: r.y, v: r.v, kind: 'R' }))
        .concat(pre.map(p => ({ x: p.x, y: p.y, v: k * p.v, kind: 'P' })));
      const f = d => Math.pow(Math.max(d, 300) / 1000, -o.beta);
      const vi = bucketIndex(rivals, 2000), F0 = f(o.outside);
      for (const z of demand) { z.S = F0; for (const [j, d] of vi.near(z.x, z.y, o.maxDist)) z.S += j.A * f(d); }
      const di = bucketIndex(demand, 1000);
      let xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
      for (const z of demand) { xmin = Math.min(xmin, z.x); xmax = Math.max(xmax, z.x); ymin = Math.min(ymin, z.y); ymax = Math.max(ymax, z.y); }
      const s = o.hex, hw = Math.sqrt(3) * s;
      for (let r = Math.floor(ymin / (1.5 * s)) - 1; r <= Math.ceil(ymax / (1.5 * s)) + 1; r++) {
        const y = r * 1.5 * s, off = (r & 1) ? hw / 2 : 0;
        for (let x = Math.floor(xmin / hw) * hw - hw + off; x <= xmax + hw; x += hw) {
          const local = di.near(x, y, 1500);
          if (local.reduce((a, [z]) => a + z.v, 0) < 300) continue; // too little demand nearby to be worth scoring
          let cR = 0, cP = 0;
          for (const [z, d] of di.near(x, y, o.maxDist)) { const fc = f(d); const c = z.v * fc / (fc + z.S); if (z.kind === 'R') cR += c; else cP += c; }
          const corners = [];
          for (let q = 0; q < 6; q++) { const a = Math.PI / 180 * (60 * q - 30); corners.push(toLL(x + s * Math.cos(a), y + s * Math.sin(a))); }
          const [lat, lon] = toLL(x, y);
          cands.push({ x, y, lat, lon, cR, cP, corners });
        }
      }
    }
    for (const c of cands) { c.combined = o.alpha * c.cR + (1 - o.alpha) * c.cP; c.fromR = o.alpha * c.cR; }
    // percentile ranks of each channel (1 = best) for the robust ranking
    const pct = key => { const srt = cands.slice().sort((a, b) => a[key] - b[key]); srt.forEach((c, i) => { c['p' + key] = (i + 1) / srt.length; }); };
    pct('cR'); pct('cP');
    for (const c of cands) {
      c.robust = Math.min(c.pcR, c.pcP);
      c.score = o.rank === 'residents' ? c.cR : o.rank === 'prescribers' ? c.cP : o.rank === 'robust' ? c.robust : c.combined;
    }
    // context for each candidate (only computed for the shortlist and on demand)
    const describe = c => {
      let pop = 0, pop14w = 0, gsum = 0, asum = 0;
      for (const [r] of ri.near(c.x, c.y, 2000)) { pop += r.pop; asum += r.aff * r.pop; if (r.g != null) { gsum += r.g * r.pop; pop14w += r.pop; } }
      const labs1 = li.near(c.x, c.y, 1000).length, labs2 = li.near(c.x, c.y, 2000).length;
      let nearest = Infinity;
      for (const rr of [2000, 6000, 20000]) { const n = li.near(c.x, c.y, rr); if (n.length) { nearest = Math.min(...n.map(v => v[1])); break; } }
      const presc = pi.near(c.x, c.y, 1000).reduce((a, [p]) => a + p.v, 0);
      return Object.assign(c, { pop2km: pop, growth: pop14w ? gsum / pop14w : null, aff2km: pop ? asum / pop : null, labs1, labs2, nearest, presc1km: Math.round(presc * 10) / 10 });
    };
    if (o.province) for (const c of cands) c.prov = provinceOf(data, c.lat, c.lon);
    const pool = cands.filter(c => !o.province || c.prov === o.province).sort((a, b) => b.score - a.score);
    const top = [];
    for (const c of pool) {
      if (top.some(t => Math.hypot(t.x - c.x, t.y - c.y) < 2500)) continue; // one pick per 2.5 km
      top.push(describe(c));
      if (top.length >= o.topN) break;
    }
    return { cands, top, describe, k, labs: labs.length };
  }

  function nearestLabel(labels, lat, lon, types, maxDist = Infinity) {
    let best = null, bd = maxDist;
    const [x1, y1] = toXY(lat, lon);
    for (const l of labels) {
      if (!types.includes(l.t) || /^(Pr[ée]fecture|Arrondissement|Pachalik|Province|Cercle|Caïdat|Commune)/i.test(l.n)) continue;
      const [x2, y2] = toXY(l.lat, l.lon);
      const d = Math.hypot(x1 - x2, y1 - y2);
      if (d < bd) { bd = d; best = l; }
    }
    return best ? best.n : '';
  }

  // point-in-polygon on [lon, lat] rings; polys = [[outer, hole...], ...]
  function inPolys(polys, lat, lon) {
    for (const poly of polys) {
      let inside = false;
      poly.forEach((ring, ri) => {
        let c = false;
        for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
          const [xi, yi] = ring[i], [xj, yj] = ring[j];
          if ((yi > lat) !== (yj > lat) && lon < (xj - xi) * (lat - yi) / (yj - yi) + xi) c = !c;
        }
        if (ri === 0) inside = c; else if (c) inside = false;
      });
      if (inside) return true;
    }
    return false;
  }

  function provinceOf(data, lat, lon) {
    for (const p of data.provinces || []) if (inPolys(p.p, lat, lon)) return p.n;
    return '';
  }

  // Human label for a zone: nearby neighbourhood if there is one, else the nearest town; district = province
  // (or the arrondissement inside the Casablanca prefecture).
  function zoneName(data, lat, lon) {
    const prov = provinceOf(data, lat, lon);
    const hood = nearestLabel(data.labels, lat, lon, ['neighborhood', 'microhood'], 1500)
      || nearestLabel(data.labels, lat, lon, ['locality', 'neighborhood', 'microhood']);
    let district = prov;
    if (/casablanca/i.test(prov)) district = nearestLabel(data.labels, lat, lon, ['macrohood'], 6000) || prov;
    return { hood, district: district === hood ? prov : district, prov };
  }
  // index into data.communes of the commune containing a point (-1 if none)
  function communeOf(data, lat, lon) {
    const cs = data.communes || [];
    for (let i = 0; i < cs.length; i++) if (inPolys(cs[i].p, lat, lon)) return i;
    return -1;
  }

  const api = { analyse, siteModel, WEIGHTS, SUB_LABEL, nearestLabel, zoneName, provinceOf, communeOf, inPolys, toXY, toLL };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.GapAnalysis = api;

  if (typeof require !== 'undefined' && typeof module !== 'undefined' && require.main === module) {
    const data = JSON.parse(require('fs').readFileSync(process.argv[2] || 'data.json', 'utf8'));
    const sm = siteModel(data, { province: process.argv[3] || '' });
    console.log(`SITE MODEL (alpha .6, beta 2, 3 years, gamma 1): ${sm.cands.length} candidates, ${sm.labs} competing labs`);
    sm.top.forEach((c, i) => {
      const z = zoneName(data, c.lat, c.lon);
      console.log(`${i + 1}. ${z.hood} (${z.district}) ${c.lat.toFixed(4)},${c.lon.toFixed(4)} combined ${Math.round(c.combined)} (residents ${Math.round(c.cR)}, prescribers ${Math.round(c.cP)}, robust ${c.robust.toFixed(2)}) | pop 2km ${Math.round(c.pop2km)} affluence ${c.aff2km ? Math.round(c.aff2km) : '?'} growth ${c.growth == null ? '?' : c.growth.toFixed(1)}%/yr | labs 1km ${c.labs1} 2km ${c.labs2} nearest ${Math.round(c.nearest)}m | prescribers 1km ${c.presc1km}`);
    });
    console.log('ZONES (prescriber gap):');
    const res = analyse(data, { hex: 400, radius: 1000, wH: 3, wT: 0, minDemand: 10, province: process.argv[3] || '' });
    console.log(`demand points ${res.demandCount}, labs ${res.labCount}, hexes ${res.hexes.length}, qualifying ${res.hexes.filter(h => h.qualifies).length}`);
    res.top.forEach((h, i) => {
      const z = zoneName(data, h.lat, h.lon);
      console.log(`${i + 1}. ${z.hood} (${z.district}) ${h.lat.toFixed(4)},${h.lon.toFixed(4)}  demand=${h.demand} [H${h.n.H} D${h.n.D}] labs1km=${h.labs} nearestLab=${Math.round(h.nearest)}m score=${h.score.toFixed(1)}`);
    });
  }
})(this);
