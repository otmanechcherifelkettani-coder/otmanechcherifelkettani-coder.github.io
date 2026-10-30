// Runs the full pipeline (simulated provider + guardrails) over all 5,000 cases and compares
// with (a) silver scenario labels for all cases and (b) the hand-labelled gold set.
// Writes validation/results.json and prints a summary. `npm run evaluate`
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { triageAll } from '../src/triage.js';
import { silverLabels } from '../validation/silver.mjs';
import { rank } from '../src/policy.js';

const cases = JSON.parse(readFileSync(new URL('../data/candidate_cases.json', import.meta.url), 'utf8'));
const t0 = performance.now();
const rec = triageAll(cases);
const ms = performance.now() - t0;
const silver = silverLabels(cases);

const cnt = (arr, f) => arr.reduce((m, x) => ((m[f(x)] = (m[f(x)] || 0) + 1), m), {});
const all = [...rec.values()];
const summary = {
  cases: all.length, ms: Math.round(ms),
  tiers: cnt(all, (r) => r.predicted_tier), actions: cnt(all, (r) => r.predicted_action), lanes: cnt(all, (r) => r.lane),
  alerts: all.filter((r) => r.alert).length, auto_resolved: all.filter((r) => r.auto_resolved).length,
  flags: cnt(all.flatMap((r) => r.flags), (f) => f),
};

function compare(labels) {
  const m = { n: 0, tier_exact: 0, under: 0, over: 0, unsafe_auto: 0, l4_recall: [0, 0], l3plus_recall: [0, 0], action_exact: 0, confusion: {}, errors: [] };
  for (const [id, L] of labels) {
    const r = rec.get(id); if (!r || !L.tier) continue;
    m.n++;
    const d = rank(r.predicted_tier) - rank(L.tier);
    if (d === 0) m.tier_exact++; else if (d < 0) m.under++; else m.over++;
    if (r.predicted_action === L.action) m.action_exact++;
    if (r.auto_resolved && L.tier !== 'L1') m.unsafe_auto++;
    if (L.tier === 'L4') { m.l4_recall[1]++; if (r.predicted_tier === 'L4') m.l4_recall[0]++; }
    if (rank(L.tier) >= 3) { m.l3plus_recall[1]++; if (rank(r.predicted_tier) >= 3) m.l3plus_recall[0]++; }
    const key = `${L.tier}->${r.predicted_tier}`; m.confusion[key] = (m.confusion[key] || 0) + 1;
    if (d !== 0) m.errors.push({ id, scenario: L.scenario, label: L.tier, got: r.predicted_tier, lang: cases.find((c) => c.case_id === id).language, cat: r.ai.category });
  }
  return m;
}
const silverRes = compare(silver);
const bySc = {};
for (const e of silverRes.errors) { const k = `${e.scenario} ${e.label}->${e.got}`; bySc[k] = (bySc[k] || 0) + 1; }
// L1 handling: share of silver-L1 cases auto-resolved vs sent to humans
const l1 = [...silver].filter(([, L]) => L.tier === 'L1');
const l1Auto = l1.filter(([id]) => rec.get(id).auto_resolved).length;

let gold = null;
const goldPath = new URL('../validation/gold_labels.json', import.meta.url);
if (existsSync(goldPath)) {
  const g = JSON.parse(readFileSync(goldPath, 'utf8'));
  gold = compare(new Map(g.map((x) => [x.case_id, x])));
  gold.rows = g.map((x) => { const r = rec.get(x.case_id); return { ...x, predicted_tier: r.predicted_tier, predicted_action: r.predicted_action, confidence: r.confidence, flags: r.flags, ai_category: r.ai.category }; });
}

const out = { generated_at: new Date().toISOString(), summary, silver: { ...silverRes, errors_by_scenario: bySc, errors: silverRes.errors.slice(0, 400), l1_total: l1.length, l1_auto: l1Auto }, gold };
writeFileSync(new URL('../validation/results.json', import.meta.url), JSON.stringify(out, null, 1));
const pct = (a, b) => (b ? ((100 * a) / b).toFixed(1) + '%' : 'n/a');
console.log(JSON.stringify(summary, null, 1));
console.log(`SILVER n=${silverRes.n} tier-exact ${pct(silverRes.tier_exact, silverRes.n)} under ${silverRes.under} over ${silverRes.over} | L4 recall ${silverRes.l4_recall.join('/')} | L3+ recall ${silverRes.l3plus_recall.join('/')} | unsafe auto-resolve ${silverRes.unsafe_auto} | L1 auto ${l1Auto}/${l1.length}`);
console.log(bySc);
if (gold) console.log(`GOLD n=${gold.n} tier-exact ${pct(gold.tier_exact, gold.n)} action-exact ${pct(gold.action_exact, gold.n)} under ${gold.under} over ${gold.over} unsafe-auto ${gold.unsafe_auto}`);
