// Acceptance tests for the operating model (domain level). Numbers refer to the spec's §13 list.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cases, freshWb, sharedWb, U, NOW, ackAndOwn } from './helpers.mjs';
import { applyFilters, overview, exportRow, EXPORT_COLUMNS, caseView } from '../src/domain/views.js';
import { automationEligibility } from '../src/domain/routing.js';
import { slaStatus, dueAt } from '../src/domain/sla.js';
import { extractSignals } from '../src/signals.js';
import { simulateTriage } from '../src/simulated.js';
import { viewLevel } from '../src/domain/permissions.js';

const states = (wb) => [...wb.states.values()];
const SOS = cases.find((c) => /SOS emergency button pressed/.test(c.safety_toolkit_log || '')).case_id;
const sum = (o) => Object.values(o).reduce((a, b) => a + b, 0);

test('1 · all 5,000 original records load and are triaged at intake', () => {
  const wb = sharedWb();
  assert.equal(wb.states.size, 5000);
  for (const s of states(wb)) { assert.ok(s.lane, s.case_id); assert.ok(s.queue); assert.ok(s.severity.current); assert.ok(s.recommendation); }
});

test('2 · overview counts reconcile to the filtered population', () => {
  const wb = sharedWb();
  for (const f of [{}, { region: 'EMEA' }, { language: 'es', severity: 'L2' }, { reporter_persona: 'driver', product: 'Rides' }, { date_from: '2026-03-03', date_to: '2026-03-04' }, { confidence_band: 'low' }]) {
    const pop = applyFilters(states(wb), f);
    const o = overview(states(wb), f, NOW);
    assert.equal(o.population, pop.length);
    for (const b of ['proposed', 'current', 'reviewed']) assert.equal(sum(o.severity[b]), pop.length, `${b} ${JSON.stringify(f)}`);
    assert.equal(sum(o.handling), pop.length); assert.equal(sum(o.workflow), pop.length); assert.equal(sum(o.automation), pop.length);
    assert.equal(Object.values(o.sla_by_tier).reduce((a, t) => a + sum(t), 0), pop.length);
    assert.ok(o.open_backlog.count <= pop.length && o.new_tickets.count <= pop.length);
  }
});

test('3 · tier distributions distinguish AI-proposed, current and reviewed severity', () => {
  const wb = freshWb();
  const o1 = overview(states(wb), {}, NOW);
  assert.equal(o1.severity.reviewed.not_reviewed, 5000);
  assert.notDeepEqual(o1.severity.proposed, o1.severity.current); // floors + language rule change some
  ackAndOwn(wb, 'SC-0001');
  wb.command(U['u-dm-1'], 'SC-0001', 'reassess', { to: 'L2', danger_assessment: 'incorrectly_detected', evidence_refs: ['telematics'], policy_ref: 'SP-7', reason: 'Driver was waiting for a lost-item handover, confirmed by rider', destination_queue: 'general-review' });
  const o2 = overview(states(wb), {}, NOW);
  assert.equal(o2.severity.reviewed.L2, 1);
  assert.equal(o2.severity.proposed.L4, o1.severity.proposed.L4); // AI proposal history unchanged
});

test('4 · any danger routes to the duty-manager lane regardless of AI confidence or proposed tier', () => {
  const wb = freshWb();
  for (const id of [SOS, 'SC-0001', 'SC-0336']) {
    const c = cases.find((x) => x.case_id === id);
    wb.applyAssessment(id, { ...simulateTriage(c), tier: 'L1', action: 'AUTO_RESOLVE_L1', confidence: 0.99, category: 'conduct', policy_refs: ['SP-1'], flags: [], mode: 'live', model: 'hostile-test' });
    const s = wb.states.get(id);
    assert.equal(s.lane, 'manager', id); assert.equal(s.severity.current, 'L4'); assert.ok(s.danger.alerts.length >= 1);
    assert.notEqual(s.automation.state, 'eligible');
  }
  for (const s of states(wb)) if (s.danger.status === 'detected') assert.equal(s.lane, 'manager', s.case_id);
});

test('4b · structured danger alerts at receipt, before AI preparation', () => {
  const s = sharedWb().states.get(SOS);
  assert.equal(s.clocks.alert_created_at, s.clocks.received_at);
  const ai = s.history.find((h) => h.type === 'ai.assessed');
  assert.ok(Date.parse(ai.at) > Date.parse(s.clocks.alert_created_at));
});

test('5/6 · agents only see permitted markets, lanes and L3 capabilities', () => {
  const wb = sharedWb();
  const emea = U['u-agent-emea'], threats = U['u-spec-threats'], incidents = U['u-spec-incidents'];
  for (const s of states(wb)) {
    const v = viewLevel(emea, s);
    if (v === 'full') { assert.equal(s.region, 'EMEA'); assert.equal(s.lane, 'agent'); assert.notEqual(s.severity.current, 'L3'); }
    if (s.lane === 'manager') { assert.notEqual(viewLevel(emea, s), 'full'); assert.notEqual(viewLevel(threats, s), 'full'); }
    if (s.queue === 'l3-violence-sexual') { assert.equal(viewLevel(threats, s), 'full'); assert.equal(viewLevel(incidents, s), null); }
    if (s.queue === 'l3-safety-incidents') { assert.equal(viewLevel(incidents, s), 'full'); assert.equal(viewLevel(threats, s), null); }
  }
  const us = states(wb).find((s) => s.region === 'US&C' && s.lane === 'agent');
  assert.equal(wb.command(emea, us.case_id, 'take').code, 403);
  assert.equal(wb.command(emea, SOS, 'acknowledge').code, 403);
});

test('7 · eligible automation excludes protected, uncertain, unsupported and repeat cases; L1 is not enough', () => {
  const wb = sharedWb();
  let l1NotEligible = 0;
  for (const s of states(wb)) {
    const e = automationEligibility(s);
    if (e.eligible) {
      assert.equal(s.severity.current, 'L1');
      for (const f of ['violence_or_sexual_allegation', 'credible_threat_language', 'injection_detected', 'prior_flags', 'safety_feature_used']) assert.ok(!s.flags.includes(f), `${s.case_id} ${f}`);
      assert.equal(s.evidence_completeness, 'complete'); assert.ok(s.understanding.supported); assert.ok(s.confidence >= 0.75);
      assert.equal(s.danger.alerts.length, 0); assert.equal(s.links.candidates.length, 0);
    } else if (s.severity.current === 'L1') l1NotEligible++;
    if (s.lane === 'automation') assert.ok(e.eligible);
  }
  // L1 alone is never sufficient: break one gate at a time on a real eligible L1 case.
  const base = states(wb).find((s) => automationEligibility(s).eligible);
  const variants = { prior: { flags: [...base.flags, 'prior_flags'] }, lang: { understanding: { ...base.understanding, supported: false } }, conf: { confidence: 0.6 },
    evidence: { evidence_completeness: 'missing_material' }, protected: { flags: [...base.flags, 'violence_or_sexual_allegation'] }, linked: { links: { candidates: [{ case_id: 'SC-0001' }] } },
    gap: { policy: { ...base.policy, gap: 'x' } }, injection: { flags: [...base.flags, 'injection_detected'] } };
  for (const [k, v] of Object.entries(variants)) assert.equal(automationEligibility({ ...base, ...v }).eligible, false, k);
  assert.equal(base.severity.current, 'L1'); void l1NotEligible;
  assert.equal(states(wb).filter((s) => s.lane === 'automation').length, 0, 'default mode is shadow: nothing automated');
});

test('8 · automation failure creates a human-review exception, not a resolution', () => {
  const wb = freshWb();
  const r = wb.setAutomationMode(U['u-dm-1'], 'enabled');
  assert.ok(r.moved_to_automation > 0);
  const failed = states(wb).filter((s) => s.automation.state === 'sent_to_review');
  assert.ok(failed.length > 0);
  for (const s of failed) {
    assert.equal(s.lane, 'agent'); assert.notEqual(s.workflow, 'resolved'); assert.ok(s.flags.includes('automation_exception'));
    assert.ok(s.executions.some((x) => x.status === 'failed'));
    assert.ok(automationEligibility(s).reasons.includes('automation_not_released_after_reassessment'));
  }
  const done = states(wb).filter((s) => s.automation.state === 'completed');
  for (const s of done) { assert.equal(s.workflow, 'resolved'); assert.ok(s.executions.some((x) => x.status === 'completed')); }
  assert.equal(wb.setAutomationMode(U['u-agent-emea'], 'enabled').code, 403);
});

test('9 · manager reassessment requires ownership, danger assessment, evidence, policy and a reason', () => {
  const wb = freshWb(); const dm = U['u-dm-1'];
  const base = { to: 'L2', danger_assessment: 'incorrectly_detected', evidence_refs: ['telematics'], policy_ref: 'SP-7', reason: 'Driver was waiting for a lost-item handover, confirmed by rider', destination_queue: 'general-review' };
  assert.match(wb.command(dm, 'SC-0001', 'reassess', base).error, /Acknowledge/);
  ackAndOwn(wb, 'SC-0001');
  for (const [k, v, re] of [['evidence_refs', [], /evidence/], ['policy_ref', 'SP-99', /policy/], ['reason', 'too short', /reason/], ['danger_assessment', 'maybe', /danger/], ['destination_queue', 'automation', /never automation/]]) {
    assert.match(wb.command(dm, 'SC-0001', 'reassess', { ...base, [k]: v }).error, re, k);
  }
  assert.match(wb.command(dm, 'SC-0001', 'reassess', { ...base, danger_assessment: 'ongoing' }).error, /ongoing/);
  assert.match(wb.command(U['u-dm-2'], 'SC-0001', 'reassess', base).error, /owner/);
  assert.equal(wb.command(dm, 'SC-0001', 'reassess', base).ok, true);
});

test('10/11 · downgrade preserves alerts, history and clocks; it never resolves or automates', () => {
  const wb = freshWb({ automationMode: 'enabled' }); const dm = U['u-dm-1'];
  const s = wb.states.get('SC-0001');
  const before = { received: s.clocks.received_at, alert: s.clocks.alert_created_at, due: dueAt(s), sla: slaStatus(s, NOW).status, ai: s.ai.severity, signals: s.danger.signals.length, hist: s.history.length };
  ackAndOwn(wb, 'SC-0001');
  wb.command(dm, 'SC-0001', 'reassess', { to: 'L1', danger_assessment: 'incorrectly_detected', evidence_refs: ['telematics', 'ticket'], policy_ref: 'SP-1', reason: 'Driver was returning a lost phone; rider confirmed on call', destination_queue: 'general-review' });
  assert.equal(s.clocks.received_at, before.received); assert.equal(s.clocks.alert_created_at, before.alert);
  assert.equal(dueAt(s), before.due); assert.equal(slaStatus(s, NOW).status, before.sla); // breach not erased
  assert.equal(s.ai.severity, before.ai); assert.equal(s.danger.signals.length, before.signals);
  assert.ok(s.danger.alerts[0].acknowledged_at); assert.ok(s.history.length > before.hist);
  assert.equal(s.severity.current, 'L1'); assert.equal(s.severity.max_held, 'L4');
  assert.notEqual(s.workflow, 'resolved'); assert.equal(s.lane, 'agent'); assert.notEqual(s.queue, 'automation');
  assert.equal(s.handoff.status, 'pending');
  assert.equal(automationEligibility(s).eligible, false);
});

test('10b · new credible danger after a downgrade creates a fresh escalation', () => {
  const wb = freshWb(); const dm = U['u-dm-1'];
  ackAndOwn(wb, 'SC-0001');
  wb.command(dm, 'SC-0001', 'reassess', { to: 'L2', danger_assessment: 'no_longer_present', evidence_refs: ['telematics'], policy_ref: 'SP-7', reason: 'Driver left; rider safe and confirmed by phone call', destination_queue: 'general-review' });
  const s = wb.states.get('SC-0001');
  wb.ingestSignal('SC-0001', { signal: 'live_sos_new' });
  assert.equal(s.danger.alerts.length, 2); assert.equal(s.danger.alerts[1].acknowledged_at, null);
  assert.equal(s.lane, 'manager'); assert.equal(s.severity.current, 'L4'); assert.equal(s.danger.status, 'detected');
});

test('12 · acknowledgement is not resolution or first response', () => {
  const wb = freshWb();
  ackAndOwn(wb, SOS);
  const s = wb.states.get(SOS);
  assert.ok(s.clocks.alert_acknowledged_at); assert.equal(s.owner, 'u-dm-1');
  assert.equal(s.workflow, 'under_review'); assert.equal(s.clocks.resolved_at, null); assert.equal(s.clocks.first_response_at, null);
  assert.match(wb.command(U['u-dm-1'], SOS, 'resolve', { reason: 'all good here now', danger_status: 'no_longer_present' }).error, /reporter-contact/);
});

test('14 · unsupported language never defaults to L1 and blocks automation', () => {
  const wb = sharedWb();
  const unsupported = states(wb).filter((s) => !s.understanding.supported);
  assert.ok(unsupported.length > 0);
  for (const s of unsupported) { assert.notEqual(s.severity.current, 'L1', s.case_id); assert.ok(!automationEligibility(s).eligible); }
});

test('15 · recommendation, decision, execution and outcome stay distinct', () => {
  const wb = freshWb(); const a = U['u-agent-emea'];
  const s = states(wb).find((x) => x.region === 'EMEA' && x.lane === 'agent' && x.severity.current === 'L1' && x.recommendation.exec_actions[0] === 'send_feedback_note'
    && !x.links.candidates.length && wb.failPct === undefined);
  const rec = s.recommendation.next_step;
  assert.equal(wb.command(a, s.case_id, 'approve').ok, true);
  assert.equal(s.recommendation.next_step, rec);
  assert.equal(s.decisions.length, 1); assert.equal(s.decisions[0].decision, 'approve_recommendation');
  assert.deepEqual(s.executions[0].history.map((h) => h.status).slice(0, 2), ['queued', 'running']);
  const last = s.executions[0].status;
  assert.equal(s.workflow === 'resolved', last === 'completed');
  // a failing execution leaves the case open with the decision recorded
  const wb2 = freshWb({ failPct: 100 });
  const s2 = wb2.states.get(s.case_id);
  wb2.command(a, s.case_id, 'approve');
  assert.equal(s2.decisions.length, 1); assert.equal(s2.executions[0].status, 'failed'); assert.notEqual(s2.workflow, 'resolved'); assert.ok(s2.flags.includes('execution_failed'));
});

test('16 · candidate links preserve evidence, highest relevant risk and earliest clock; never merged', () => {
  const wb = sharedWb();
  const child = wb.states.get('SC-1448'), parent = wb.states.get('SC-1417');
  assert.equal(child.links.candidates[0].case_id, 'SC-1417'); assert.equal(child.links.candidates[0].status, 'candidate');
  assert.equal(child.incident_id, parent.incident_id); assert.notEqual(child.case_id, parent.case_id); assert.equal(child.trip_id, parent.trip_id);
  assert.ok({ L1: 1, L2: 2, L3: 3, L4: 4 }[child.severity.current] >= { L1: 1, L2: 2, L3: 3, L4: 4 }[parent.severity.current]);
  assert.ok(dueAt(child) <= dueAt(parent));
  assert.ok(child.sources.length === 7 && child.sources.find((x) => x.id === 'ticket').facts.length > 0);
  assert.notEqual(child.workflow, 'resolved');
});

test('18 · export rows include the brief’s minimum columns and no PII', () => {
  const wb = sharedWb();
  for (const c of ['case_id', 'predicted_tier', 'predicted_action', 'confidence', 'flags', 'rationale', 'human_decision', 'human_reason', 'decided_at']) assert.ok(EXPORT_COLUMNS.includes(c));
  const rows = states(wb).slice(0, 200).map((s) => exportRow(s, NOW));
  const text = JSON.stringify(rows);
  for (const c of cases.slice(0, 200)) { assert.ok(!text.includes(c.pii.reporter.email)); assert.ok(!text.includes(c.pii.reporter.phone)); }
});

test('19a · idempotency: a repeated command key executes once', () => {
  const wb = freshWb(); const a = U['u-agent-emea'];
  const s = states(wb).find((x) => x.region === 'EMEA' && x.lane === 'agent' && x.severity.current === 'L2');
  wb.command(a, s.case_id, 'approve', {}, 'key-1');
  const r = wb.command(a, s.case_id, 'approve', {}, 'key-1');
  assert.equal(r.replayed, true); assert.equal(s.decisions.length, 1); assert.equal(s.executions.length, 1);
});

test('19b · server views mask PII and redact free text by default', () => {
  const wb = sharedWb(); const dm = U['u-dm-1'];
  for (const id of ['SC-0001', 'SC-0009', SOS]) {
    const raw = wb.raw.get(id); const v = JSON.stringify(caseView(wb.states.get(id), raw, dm, NOW, {}));
    for (const val of [raw.pii.reporter.name, raw.pii.reporter.phone, raw.pii.reporter.email, raw.pii.reported_party?.phone, raw.pii.pickup_address].filter(Boolean)) assert.ok(!v.includes(val), `${id} leaks ${val}`);
  }
});

test('policy · SP-8 allegation stays human-reviewed despite counter-evidence; reporter frequency is not counter-evidence', () => {
  const s = sharedWb().states.get('SC-0104');
  assert.ok(['L3', 'L4'].includes(s.severity.current)); assert.equal(s.lane, 'agent'); assert.equal(s.queue, 'l3-violence-sexual');
  assert.ok(s.policy.mandatory_human_checks.some((c) => c.policy === 'SP-8'));
  const c = structuredClone(cases.find((x) => x.case_id === 'SC-0009'));
  c.telematics_summary = 'Reporter has 4 reports in 90 days, 3 closed no-violation.';
  assert.equal(extractSignals(c).counterEvidence, false);
});

test('policy · SP-9 same-behaviour history raises one tier; injection is data and goes to a specialist', () => {
  const wb = sharedWb();
  assert.equal(wb.states.get('SC-0027').severity.current, 'L2');
  assert.equal(wb.states.get('SC-0696').severity.current, 'L3');
  assert.equal(wb.states.get('SC-0657').severity.current, 'L4');
  const inj = wb.states.get('SC-0023');
  assert.ok(inj.flags.includes('injection_detected')); assert.equal(inj.severity.current, 'L3'); assert.equal(inj.queue, 'l3-threats-exposure');
});

test('AI re-assessment never silently overwrites a human-reviewed severity', () => {
  const wb = freshWb(); const a = U['u-agent-emea'];
  const s = states(wb).find((x) => x.region === 'EMEA' && x.lane === 'agent' && x.severity.current === 'L2' && !x.links.candidates.length);
  wb.command(a, s.case_id, 'approve');
  const reviewed = s.severity.reviewed;
  wb.applyAssessment(s.case_id, { ...simulateTriage(wb.raw.get(s.case_id)), tier: 'L1', confidence: 0.95, mode: 'live', model: 't' });
  assert.equal(s.severity.reviewed, reviewed); assert.equal(s.severity.current, reviewed);
  assert.equal(s.severity.proposed, 'L1'); assert.ok(s.flags.includes('ai_disagrees_with_review'));
});

test('SLA · awaiting information does not pause the clock; reassignment does not reset it', () => {
  const wb = freshWb(); const a = U['u-agent-emea'];
  const s = states(wb).find((x) => x.region === 'EMEA' && x.lane === 'agent' && x.severity.current === 'L2');
  const due = dueAt(s);
  wb.command(a, s.case_id, 'request_info', { reason: 'need trip details' });
  assert.equal(dueAt(s), due);
  assert.equal(s.workflow === 'awaiting_information' || s.executions[0].status === 'failed', true);
});
