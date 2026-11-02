// Tests for the four ideas ported from the alternative build.
import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { JsonlLog } from '../server/eventlog.mjs';
import { createApp } from '../server/app.mjs';
import { redactForAI } from '../src/pii.js';
import { INJECTION, LEX } from '../src/lexicon.js';
import { automationEligibility } from '../src/domain/routing.js';
import { simulateTriage } from '../src/simulated.js';
import { cases, tmp, freshWb, U } from './helpers.mjs';

const DAY = 864e5;
const servers = [];
after(() => servers.forEach((s) => s.close()));

test('1 · access log is hash-chained: edits, deletions and insertions are detected', () => {
  const f = join(tmp(), 'access.jsonl');
  const log = new JsonlLog(f, { chained: true });
  for (let i = 0; i < 5; i++) log.append({ recorded_at: new Date().toISOString(), event: 'view_case', case_id: `SC-000${i}` });
  assert.equal(log.verify().ok, true);
  const lines = readFileSync(f, 'utf8').trim().split('\n');
  const edited = JSON.parse(lines[2]); edited.case_id = 'SC-9999';
  writeFileSync(f, [...lines.slice(0, 2), JSON.stringify(edited), ...lines.slice(3)].join('\n') + '\n');
  assert.deepEqual([log.verify().ok, log.verify().broken_at, log.verify().reason], [false, 2, 'entry content changed']);
  writeFileSync(f, [...lines.slice(0, 2), ...lines.slice(3)].join('\n') + '\n');
  assert.equal(log.verify().ok, false);
  writeFileSync(f, lines.join('\n') + '\n');
  assert.equal(log.verify().ok, true);
});

test('1b · retention purges only a prefix and the chain still verifies from its anchor', () => {
  const f = join(tmp(), 'access.jsonl');
  const now = Date.now();
  const log = new JsonlLog(f, { chained: true });
  for (let i = 0; i < 6; i++) log.append({ recorded_at: new Date(now - (6 - i) * 100 * DAY).toISOString(), event: 'e' + i });
  const later = new JsonlLog(f, { chained: true, retentionDays: 350, nowMs: () => now });
  const v = later.verify();
  assert.equal(v.ok, true); assert.equal(v.entries, 3); assert.equal(v.purged_by_retention, 3);
  later.append({ recorded_at: new Date(now).toISOString(), event: 'after purge' });
  assert.equal(later.verify().ok, true);
});

test('2 · case records are retained by tier after resolution, then replaced by a tombstone', async () => {
  const dir = tmp(); const t0 = Date.now();
  const a = createApp({ dataDir: dir, fixedNow: Date.parse('2026-03-08T08:00:00Z'), failPct: 0, realNow: () => t0 });
  const wb = a.wb; const agent = U['u-agent-emea'];
  const l1 = [...wb.states.values()].find((s) => s.region === 'EMEA' && s.lane === 'agent' && s.severity.current === 'L1' && !s.links.candidates.length);
  const l2 = [...wb.states.values()].find((s) => s.region === 'EMEA' && s.lane === 'agent' && s.severity.current === 'L2' && s.severity.max_held === 'L2' && !s.links.candidates.length);
  const open = [...wb.states.values()].find((s) => s.region === 'EMEA' && s.lane === 'agent' && s.severity.current === 'L1' && s !== l1);
  for (const s of [l1, l2]) { assert.equal(wb.command(agent, s.case_id, 'approve').ok, true); assert.equal(s.workflow, 'resolved'); }
  wb.command(agent, open.case_id, 'take');

  const b = createApp({ dataDir: dir, fixedNow: Date.parse('2026-03-08T08:00:00Z'), realNow: () => t0 + 200 * DAY });
  const p1 = b.wb.states.get(l1.case_id), p2 = b.wb.states.get(l2.case_id), o = b.wb.states.get(open.case_id);
  assert.ok(p1.flags.includes('retention_purged')); assert.equal(p1.decisions.length, 0); assert.equal(p1.executions.length, 0); assert.equal(p1.workflow, 'resolved');
  assert.ok(!p2.flags.includes('retention_purged')); assert.equal(p2.decisions.length, 1);   // L2 keeps 365 days
  assert.equal(o.owner, 'u-agent-emea');                                                     // open cases are never purged
  const ev = readFileSync(join(dir, 'events.jsonl'), 'utf8').split('\n').filter(Boolean).map(JSON.parse);
  assert.equal(ev.filter((e) => e.case_id === l1.case_id).map((e) => e.type).join(), 'record.purged');

  const c = createApp({ dataDir: dir, fixedNow: Date.parse('2026-03-08T08:00:00Z'), realNow: () => t0 + 400 * DAY });
  assert.ok(c.wb.states.get(l2.case_id).flags.includes('retention_purged'));
  assert.ok(c.audit.readAll().some((r) => r.event === 'retention_purge'));
  assert.equal(c.audit.verify().ok, true);
});

test('3 · instructions to the triage system are removed from model input; the threat text is kept', () => {
  const inj = cases.filter((c) => c.telematics_summary.startsWith('ETA slip'));
  assert.equal(inj.length, 50);
  for (const c of inj) {
    const p = redactForAI(c);
    assert.ok(!INJECTION.test(p.report_text), c.case_id); assert.ok(p.injection_removed > 0, c.case_id);
    assert.ok(!/mark (this|as)|resolved|classif|close (it|ticket)|low priority|ignore|disregard|olvida|ignora|escalate|auto-?close|L1\b|resuelve|arquive|forward/i.test(p.report_text), `${c.case_id} kept directive: ${p.report_text}`);
    const hadThreat = LEX.threatHarm.test(c.report_text) || LEX.threatWord.test(c.report_text);
    if (hadThreat) assert.ok(LEX.threatHarm.test(p.report_text) || LEX.threatWord.test(p.report_text), `${c.case_id} lost its threat`);
    assert.ok(p.report_text.includes(c.report_text.trim().slice(-6)), `${c.case_id} lost its ending`);
  }
  for (const c of cases.filter((x) => !x.telematics_summary.startsWith('ETA slip'))) assert.equal(redactForAI(c).injection_removed, 0, c.case_id);
  // the deterministic rules still see the original text
  const wb = freshWb();
  for (const c of inj) assert.ok(wb.states.get(c.case_id).flags.includes('injection_detected'), c.case_id);
});

test('4 · second key: text-only SP-1 cases need a live model to agree before automation', () => {
  const wb = freshWb();
  const states = [...wb.states.values()];
  const textOnly = states.find((s) => s.severity.current === 'L1' && automationEligibility(s).reasons.join() === 'text_only_needs_live_ai_confirmation');
  const systemBacked = states.find((s) => s.severity.current === 'L1' && automationEligibility(s).eligible);
  assert.ok(textOnly && systemBacked);
  assert.ok(systemBacked.policy.conditions.some((c) => c.policy === 'SP-1' && c.basis !== 'allegation'));
  // simulated agreement is not a second key
  assert.equal(automationEligibility({ ...textOnly, ai: { ...textOnly.ai, mode: 'simulated', severity: 'L1' } }).eligible, false);
  // a live model that agrees on L1 is
  wb.applyAssessment(textOnly.case_id, { ...simulateTriage(wb.raw.get(textOnly.case_id)), mode: 'live', model: 'test-live', tier: 'L1' });
  assert.equal(automationEligibility(wb.states.get(textOnly.case_id)).eligible, true);
  // a live model that disagrees is not
  const other = states.find((s) => s !== textOnly && s.severity.current === 'L1' && automationEligibility(s).reasons.join() === 'text_only_needs_live_ai_confirmation');
  wb.applyAssessment(other.case_id, { ...simulateTriage(wb.raw.get(other.case_id)), mode: 'live', model: 'test-live', tier: 'L2' });
  assert.equal(automationEligibility(wb.states.get(other.case_id)).eligible, false);
});

test('4b · /api/audit/verify reports an intact chain to duty managers only', async () => {
  const app = createApp({ dataDir: tmp(), fixedNow: Date.parse('2026-03-08T08:00:00Z') });
  await new Promise((r) => app.server.listen(0, r)); servers.push(app.server);
  const base = `http://127.0.0.1:${app.server.address().port}`;
  const tok = async (u) => (await (await fetch(base + '/api/session', { method: 'POST', body: JSON.stringify({ user_id: u }) })).json()).token;
  const dm = await tok('u-dm-1'), ag = await tok('u-agent-emea');
  assert.equal((await fetch(base + '/api/audit/verify', { headers: { authorization: `Bearer ${ag}` } })).status, 403);
  const v = await (await fetch(base + '/api/audit/verify', { headers: { authorization: `Bearer ${dm}` } })).json();
  assert.equal(v.ok, true); assert.ok(v.entries >= 2); assert.equal(v.retention_days.L1, 180);
});
