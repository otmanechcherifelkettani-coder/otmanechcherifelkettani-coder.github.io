import { test } from 'node:test';
import assert from 'node:assert/strict';
import { get, cases } from './helpers.mjs';
import { redactForAI, redactText, containsObviousPII, maskPhone, maskName } from '../src/pii.js';
import { Store, toCSV, EXPORT_COLUMNS } from '../src/store.js';
import { finalize } from '../src/triage.js';
import { simulateTriage } from '../src/simulated.js';
import { answerPolicyLocally } from '../src/policyqa.js';
import { validateTriage } from '../src/ai.js';

const mem = () => { const m = new Map(); return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, v) }; };

test('redactForAI removes every structured PII value, including when it appears in free text', () => {
  for (const c of cases.slice(0, 500)) {
    const out = JSON.stringify(redactForAI(c));
    const p = c.pii;
    for (const v of [p.reporter?.name, p.reporter?.phone, p.reporter?.email, p.reported_party?.name, p.reported_party?.phone, p.reported_party?.email, p.reported_party?.vehicle_plate, p.pickup_address, p.dropoff_address].filter(Boolean)) {
      assert.ok(!out.includes(v), `${c.case_id} leaked ${v}`);
    }
    assert.ok(!out.includes(c.reporter_id) && !out.includes(c.trip_id));
    assert.equal(containsObviousPII(redactForAI(c)), false);
  }
});

test('free-text PII (names, phone, email) is redacted', () => {
  const c = get('SC-0001');
  c.report_text = `It was ${c.pii.reported_party.name}, call me on +61 491 570 999 or mail x.y@example.test. Plate ${c.pii.reported_party.vehicle_plate}.`;
  const s = redactText(c.report_text, c);
  assert.ok(!s.includes(c.pii.reported_party.name.split(' ')[0]));
  assert.match(s, /\[PHONE\]/); assert.match(s, /\[EMAIL\]/); assert.match(s, /\[PLATE\]/);
});

test('masking hides most of each value', () => {
  assert.equal(maskName('Hao Huang'), 'H•• H••••');
  assert.ok(maskPhone('+61 491 570 476').endsWith('476'));
  assert.ok(!maskPhone('+61 491 570 476').includes('491'));
});

test('decisions require a reason; agents cannot decide L3/L4; only duty managers can downgrade SP-7 cases', () => {
  const s = new Store(mem());
  const l4 = finalize(get('SC-0001'), simulateTriage(get('SC-0001')));
  assert.equal(s.decide(l4, { decision: 'approve', reason: '' }, 'specialist').ok, false);
  assert.equal(s.decide(l4, { decision: 'approve', reason: 'Confirmed, police called' }, 'agent').ok, false);
  assert.equal(s.decide(l4, { decision: 'override', tier: 'L2', action: 'ROUTE_L2_REVIEW', reason: 'Rider confirmed safe' }, 'specialist').ok, false);
  assert.equal(s.decide(l4, { decision: 'override', tier: 'L2', action: 'ROUTE_L2_REVIEW', reason: 'Rider confirmed safe by phone' }, 'duty').ok, true);
  const l1 = finalize(get('SC-0009'), simulateTriage(get('SC-0009')));
  const r = s.decide(l1, { decision: 'escalate', reason: 'Tone suggests more than lateness' }, 'agent');
  assert.equal(r.ok, true); assert.equal(r.decision.final_tier, 'L3');
  assert.ok(s.state.audit.some((e) => e.event === 'decision' && e.case_id === 'SC-0009'));
});

test('export contains the minimum columns and no PII', () => {
  const s = new Store(mem());
  const rows = cases.slice(0, 50).map((c) => s.row(finalize(c, simulateTriage(c))));
  const csv = toCSV(rows);
  for (const col of ['case_id', 'predicted_tier', 'predicted_action', 'confidence', 'flags', 'rationale', 'human_decision', 'human_reason', 'decided_at']) assert.ok(EXPORT_COLUMNS.includes(col));
  assert.ok(csv.split('\n')[0].startsWith('case_id,predicted_tier,predicted_action,confidence,flags,rationale,human_decision,human_reason,decided_at'));
  for (const c of cases.slice(0, 50)) assert.ok(!csv.includes(c.pii.reporter.email) && !csv.includes(c.pii.reporter.name));
});

test('retention purges expired audit events and decisions', () => {
  const store = mem();
  let now = Date.parse('2026-03-07T00:00:00Z');
  const s = new Store(store, () => now);
  s.log('agent', 'open_case', 'SC-0001');
  now += 401 * 864e5;
  const s2 = new Store(store, () => now);
  assert.equal(s2.state.audit.length, 0);
});

test('policy Q&A cites clauses, and says "Not covered" when the policy is silent', () => {
  const a = answerPolicyLocally('Is a cleaning fee for a stain over 50 USD property damage?');
  assert.equal(a.covered, true); assert.ok(a.citations.includes('SP-2'));
  const b = answerPolicyLocally('Can a driver refuse a service animal?');
  assert.equal(b.covered, false); assert.match(b.answer, /Not covered/);
  const d = answerPolicyLocally('What is the refund amount for airport tolls?');
  assert.equal(d.covered, false);
});

test('invalid model output falls back to the safest values', () => {
  const v = validateTriage({ tier: 'L9', action: 'CLOSE_NOW', confidence: 'high', policy_refs: ['SP-1', 'IGNORE'], flags: ['ok_flag', 'DROP TABLE'] });
  assert.equal(v.tier, 'L3'); assert.equal(v.action, 'ROUTE_L3_REVIEW'); assert.equal(v.confidence, 0.3);
  assert.deepEqual(v.policy_refs, ['SP-1']); assert.ok(v.flags.includes('ai_output_invalid'));
});

test('L4 response: ordered, timestamped steps; cannot close until reporter handled; closes with reason', () => {
  let now = Date.parse('2026-03-01T00:00:00Z');
  const s = new Store(mem(), () => now);
  const l4 = finalize(get('SC-0001'), simulateTriage(get('SC-0001')));
  assert.equal(s.respond(l4, 'ack', {}, 'agent').ok, false);                       // agents cannot respond to L4
  assert.equal(s.respond(l4, 'contact', { value: 'reached' }, 'duty').ok, false);  // must acknowledge first
  assert.equal(s.respond(l4, 'ack', {}, 'duty').ok, true);
  now += 4 * 60e3;
  assert.equal(s.respond(l4, 'contact', { value: 'no_answer' }, 'duty').ok, true);
  assert.equal(s.respond(l4, 'emergency', { value: 'contacted' }, 'duty').ok, true);
  assert.equal(s.respond(l4, 'protect', { value: 'account_suspended' }, 'duty').ok, true);
  assert.equal(s.respond(l4, 'outcome', { value: 'action_taken', reason: 'Police attended, rider safe' }, 'duty').ok, false); // reporter not reached
  assert.equal(s.respond(l4, 'contact', { value: 'reached' }, 'duty').ok, true);
  assert.equal(s.respond(l4, 'outcome', { value: 'action_taken', reason: '' }, 'duty').ok, false);
  assert.equal(s.respond(l4, 'outcome', { value: 'action_taken', reason: 'Police attended, rider safe' }, 'duty').ok, true);
  assert.equal(s.state.decisions['SC-0001'].human_decision, 'l4_response_closed');
  assert.equal(s.state.decisions['SC-0001'].final_tier, 'L4');
  const row = s.row(l4);
  assert.equal(row.l4_acknowledged_at, '2026-03-01T00:00:00.000Z');
  assert.equal(row.l4_emergency_services, 'contacted');
  assert.equal(row.l4_outcome, 'action_taken');
  assert.equal(s.respond(l4, 'protect', { value: 'none_needed' }, 'duty').ok, false); // closed
  assert.ok(s.state.audit.some((e) => e.event === 'alert_ack'));
});

test('L4 response checklist does not apply to non-L4 cases', () => {
  const s = new Store(mem());
  const l1 = finalize(get('SC-0009'), simulateTriage(get('SC-0009')));
  assert.equal(s.respond(l1, 'ack', {}, 'duty').ok, false);
});
