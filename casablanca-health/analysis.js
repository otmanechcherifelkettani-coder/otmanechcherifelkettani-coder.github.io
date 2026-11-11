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

  // opts: {hex (edge length m), radius (m), wH, wD, wT, minDemand}
  function analyse(data, opts) {
    const pts = data.pts.map(p => { const [x, y] = toXY(p[0], p[1]); return { lat: p[0], lon: p[1], c: p[2], name: p[3], cat: p[4], x, y }; });
    const w = { H: opts.wH, D: opts.wD, T: opts.wT, L: 0 };
    const demandPts = pts.filter(p => p.c !== 'L' && w[p.c] > 0);
    const labs = pts.filter(p => p.c === 'L');
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
        for (const [p] of near) { demand += w[p.c]; n[p.c]++; }
        const nl = li.near(x, y, R).length;
        // nearest lab distance (search widening)
        let nearest = Infinity;
        for (const rr of [R, 2500, 6000, 20000]) {
          const c = labsAll.near(x, y, rr);
          if (c.length) { nearest = Math.min(...c.map(v => v[1])); break; }
        }
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

  const api = { analyse, nearestLabel, zoneName, provinceOf, communeOf, inPolys, toXY, toLL };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.GapAnalysis = api;

  if (typeof require !== 'undefined' && typeof module !== 'undefined' && require.main === module) {
    const data = JSON.parse(require('fs').readFileSync(process.argv[2] || 'data.json', 'utf8'));
    const res = analyse(data, { hex: 400, radius: 1000, wH: 3, wD: 1, wT: 0, minDemand: 10, province: process.argv[3] || '' });
    console.log(`demand points ${res.demandCount}, labs ${res.labCount}, hexes ${res.hexes.length}, qualifying ${res.hexes.filter(h => h.qualifies).length}`);
    res.top.forEach((h, i) => {
      const z = zoneName(data, h.lat, h.lon);
      console.log(`${i + 1}. ${z.hood} (${z.district}) ${h.lat.toFixed(4)},${h.lon.toFixed(4)}  demand=${h.demand} [H${h.n.H} D${h.n.D}] labs1km=${h.labs} nearestLab=${Math.round(h.nearest)}m score=${h.score.toFixed(1)}`);
    });
  }
})(this);
