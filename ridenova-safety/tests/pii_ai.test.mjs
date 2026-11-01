import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cases, get } from './helpers.mjs';
import { redactForAI, redactText, containsObviousPII, maskPhone, maskName } from '../src/pii.js';
import { answerPolicyLocally } from '../src/policyqa.js';
import { validateTriage } from '../src/ai.js';
import { INJECTION } from '../src/lexicon.js';

test('19 · redactForAI removes every structured PII value, including in free text', () => {
  for (const c of cases.slice(0, 500)) {
    const out = JSON.stringify(redactForAI(c)); const p = c.pii;
    for (const v of [p.reporter?.name, p.reporter?.phone, p.reporter?.email, p.reported_party?.name, p.reported_party?.phone, p.reported_party?.email, p.reported_party?.vehicle_plate, p.pickup_address, p.dropoff_address].filter(Boolean)) assert.ok(!out.includes(v), `${c.case_id} leaked ${v}`);
    assert.ok(!out.includes(c.reporter_id) && !out.includes(c.trip_id));
    assert.equal(containsObviousPII(redactForAI(c)), false);
  }
});
test('free-text names, phones, emails and plates are redacted; masking hides most of a value', () => {
  const c = get('SC-0001');
  const s = redactText(`It was ${c.pii.reported_party.name}, call +61 491 570 999 or x.y@example.test. Plate ${c.pii.reported_party.vehicle_plate}.`, c);
  assert.ok(!s.includes(c.pii.reported_party.name.split(' ')[0])); assert.match(s, /\[PHONE\]/); assert.match(s, /\[EMAIL\]/); assert.match(s, /\[PLATE\]/);
  assert.equal(maskName('Hao Huang'), 'H•• H••••'); assert.ok(!maskPhone('+61 491 570 476').includes('491'));
});
test('public text is data: injection wrappers are detected in several languages', () => {
  const inj = cases.filter((c) => c.telematics_summary.startsWith('ETA slip'));
  assert.equal(inj.filter((c) => INJECTION.test(c.report_text)).length, inj.length);
});
test('policy Q&A cites clauses or says "Not covered"', () => {
  const a = answerPolicyLocally('Is a cleaning fee for a stain over 50 USD property damage?');
  assert.equal(a.covered, true); assert.ok(a.citations.includes('SP-2'));
  assert.equal(answerPolicyLocally('Can a driver refuse a service animal?').covered, false);
});
test('invalid model output falls back to the safest values', () => {
  const v = validateTriage({ tier: 'L9', action: 'CLOSE_NOW', confidence: 'high', policy_refs: ['SP-1', 'IGNORE'], flags: ['ok_flag', 'DROP TABLE'] });
  assert.equal(v.tier, 'L3'); assert.equal(v.action, 'ROUTE_L3_REVIEW'); assert.equal(v.confidence, 0.3); assert.deepEqual(v.policy_refs, ['SP-1']); assert.ok(v.flags.includes('ai_output_invalid'));
});
