// Evaluation of the CURRENT operating model (Workbench intake + routing) on all 5,000 cases.
//   npm run evaluate   -> prints a summary and writes validation/results.json
// Reference sets, kept separate:
//   silver   : scenario-level labels for all 5,000 (validation/silver.mjs) — AI-assisted, candidate to review
//   ai_draft : 30 case-level labels drafted by AI (reference_labels_ai_drafted.json) — NOT independent
//   adjudicated : rows the candidate has filled in candidate_adjudication.json (none until reviewed)
import { readFileSync, writeFileSync } from 'node:fs';
import { Workbench } from '../src/domain/workbench.js';
import { automationEligibility } from '../src/domain/routing.js';
import { silverLabels } from '../validation/silver.mjs';

const R = { L1: 1, L2: 2, L3: 3, L4: 4 };
const cases = JSON.parse(readFileSync(new URL('../data/candidate_cases.json', import.meta.url), 'utf8'));
const mem = () => ({ append() {}, readAll: () => [] });
const t0 = performance.now();
const wb = new Workbench({ cases, log: mem(), audit: mem(), now: () => Date.parse('2026-03-08T08:00:00Z') });
const bootMs = Math.round(performance.now() - t0);
const S = (id) => wb.states.get(id);

function compare(labels) {
  const m = { n: 0, tier_exact: 0, under: 0, over: 0, l4_to_manager: [0, 0], l3plus_recall: [0, 0], automation_eligible_but_not_L1: 0, misses: [] };
  for (const L of labels) {
    if (!L.tier) continue;
    const s = S(L.case_id); m.n++;
    const d = R[s.severity.current] - R[L.tier];
    if (d === 0) m.tier_exact++; else if (d < 0) { m.under++; m.misses.push({ case_id: L.case_id, label: L.tier, got: s.severity.current, lane: s.lane, language: s.language, category: s.ai.category }); } else m.over++;
    if (L.tier === 'L4') { m.l4_to_manager[1]++; if (s.lane === 'manager') m.l4_to_manager[0]++; }
    if (R[L.tier] >= 3) { m.l3plus_recall[1]++; if (R[s.severity.current] >= 3) m.l3plus_recall[0]++; }
    if (automationEligibility(s).eligible && L.tier !== 'L1') m.automation_eligible_but_not_L1++;
  }
  return m;
}
const silver = [...silverLabels(cases)].map(([case_id, v]) => ({ case_id, ...v }));
const aiDraft = JSON.parse(readFileSync(new URL('../validation/reference_labels_ai_drafted.json', import.meta.url), 'utf8')).labels;
const adj = JSON.parse(readFileSync(new URL('../validation/candidate_adjudication.json', import.meta.url), 'utf8')).labels.filter((l) => l.tier);
const cnt = (f) => { const o = {}; for (const s of wb.states.values()) { const k = f(s); o[k] = (o[k] || 0) + 1; } return o; };
const shadow = { lanes: cnt((s) => s.lane), current: cnt((s) => s.severity.current), proposed: cnt((s) => s.severity.proposed), automation: cnt((s) => s.automation.state), alerts: [...wb.states.values()].filter((s) => s.danger.alerts.length).length };
const silverRes = compare(silver), draftRes = compare(aiDraft), adjRes = adj.length ? compare(adj) : null;
wb.setAutomationMode({ id: 'eval', role: 'duty_manager' }, 'enabled');
const enabled = { automation: cnt((s) => s.automation.state), resolved: cnt((s) => s.workflow).resolved || 0 };
const silverTier = new Map(silver.map((x) => [x.case_id, x.tier]));
enabled.automated_but_silver_not_L1 = [...wb.states.values()].filter((s) => ['completed', 'sent_to_review'].includes(s.automation.state) && silverTier.get(s.case_id) !== 'L1').length;
const out = { generated_at: new Date().toISOString(), boot_ms: bootMs, shadow_mode: shadow, demo_automation_enabled: enabled, silver: silverRes, ai_drafted_reference: draftRes, candidate_adjudicated: adjRes || 'none yet' };
writeFileSync(new URL('../validation/results.json', import.meta.url), JSON.stringify(out, null, 1));
const pct = (a, b) => `${((100 * a) / b).toFixed(1)}%`;
console.log(`boot ${bootMs} ms · lanes ${JSON.stringify(shadow.lanes)} · current ${JSON.stringify(shadow.current)}`);
console.log(`SILVER (n=${silverRes.n}): tier match ${pct(silverRes.tier_exact, silverRes.n)} · under ${silverRes.under} · over ${silverRes.over} · L4→manager ${silverRes.l4_to_manager.join('/')} · L3+ recall ${silverRes.l3plus_recall.join('/')} · eligible-but-not-L1 ${silverRes.automation_eligible_but_not_L1}`);
console.log(`AI-DRAFTED REFERENCE (n=${draftRes.n}, not independent): tier match ${draftRes.tier_exact}/${draftRes.n} · under ${draftRes.under} · over ${draftRes.over}`);
console.log(`CANDIDATE-ADJUDICATED: ${adjRes ? `${adjRes.tier_exact}/${adjRes.n}` : 'none yet'}`);
console.log(`Demo automation enabled: ${JSON.stringify(enabled)}`);
console.log('Under-triage:', silverRes.misses.map((m) => `${m.case_id} ${m.label}->${m.got}`).join(', '));
