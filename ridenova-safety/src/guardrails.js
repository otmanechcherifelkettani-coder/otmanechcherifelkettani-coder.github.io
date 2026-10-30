// Deterministic policy guardrails. Applied AFTER any AI proposal (simulated or live), never
// bypassable by model output. The AI proposes; these rules constrain; a human decides.
//
// Precedence (overlapping rules resolve to the most protective outcome):
//   1. SP-7 danger  -> L4, ESCALATE_L4_IMMEDIATE, duty-manager alert, locked against auto-close/downgrade
//   2. SP-8 violence/sexual allegation -> floor L3, human review required
//   3. SP-6 harm-threat language -> floor L3
//   4. Prompt injection -> flag, specialist review (floor L3), confidence capped
//   5. Prior flags / missing evidence / duplicates -> human review, more-info or merge
//   6. AUTO_RESOLVE_L1 only if every gate passes (allow-list, not default)

import { rank, maxTier, defaultAction } from './policy.js';

export const AUTO_RESOLVE_MIN_CONF = 0.75;
const BLOCKS_AUTO = new Set(['danger_signal', 'violence_or_sexual_allegation', 'credible_threat_language', 'injection_detected',
  'prior_flags', 'missing_evidence', 'conflicting_signals', 'mixed_signals', 'uncertain', 'safety_feature_used', 'duplicate']);

export function applyGuardrails(c, proposal, s, ctx = {}) {
  const changes = [];
  const flags = new Set(proposal.flags || []);
  let tier = proposal.tier;
  let action = proposal.action;
  let confidence = proposal.confidence;
  let alert = false;
  let locked = false;
  const raise = (to, rule, why) => {
    if (rank(to) > rank(tier)) { changes.push({ rule, from: tier, to, why }); tier = to; }
  };

  // 1. SP-7
  if (s.sos || s.homeProximity || s.danger || s.liveIncident) {
    flags.add('danger_signal');
    raise('L4', 'SP-7', s.sos ? 'Live SOS in toolkit' : s.homeProximity ? 'Reported party near reporter’s home after trip' : s.liveIncident ? 'Report filed mid-trip with vehicle stopped roadside' : 'Danger-signal language in report');
    if (action !== 'ESCALATE_L4_IMMEDIATE') changes.push({ rule: 'SP-7', from: action, to: 'ESCALATE_L4_IMMEDIATE', why: 'Danger signals always escalate' });
    action = 'ESCALATE_L4_IMMEDIATE';
    alert = true; locked = true;
  }
  if (tier === 'L4') { alert = true; locked = true; action = 'ESCALATE_L4_IMMEDIATE'; }

  // 2. SP-8
  if (s.violence) { flags.add('violence_or_sexual_allegation'); raise('L3', 'SP-8', 'Violence/sexual-misconduct allegation requires human review'); }
  // 3. SP-6
  if (s.threat) { flags.add('credible_threat_language'); raise('L3', 'SP-6', 'Threat-of-harm language'); }
  // 4. Injection
  if (s.injection) {
    flags.add('injection_detected');
    // Text written to manipulate triage cannot be trusted to be minor: specialist review.
    raise('L3', 'INJ', 'Report contains instructions aimed at the triage system — treated as data, routed to a specialist');
    confidence = Math.min(confidence, 0.5);
  }
  // 5a. Prior flags
  if (s.priorCategory) flags.add('prior_flags');
  // 5b. Safety-feature use
  if (s.toolkitActivity) flags.add('safety_feature_used');
  // 5c. Missing evidence
  if (s.missingTrip) {
    flags.add('missing_evidence');
    confidence = Math.min(confidence, 0.6);
    if (rank(tier) <= 2 && action !== 'ESCALATE_L4_IMMEDIATE') {
      if (action !== 'REQUEST_MORE_INFO') changes.push({ rule: 'DATA', from: action, to: 'REQUEST_MORE_INFO', why: 'Trip record / reported party unavailable' });
      action = 'REQUEST_MORE_INFO'; tier = maxTier(tier, 'L2');
    }
  }
  // 5d. Duplicates: same reporter + same trip as an earlier case -> merge, inherit the higher tier
  const parent = ctx.parent;
  if (parent) {
    flags.add('duplicate');
    if (parent.tier) raise(parent.tier, 'DUP', `Inherits tier of parent ${parent.case_id}`);
    if (!locked) { changes.push({ rule: 'DUP', from: action, to: 'MERGE_DUPLICATE', why: `Follow-up on ${parent.case_id}` }); action = 'MERGE_DUPLICATE'; }
    if (rank(tier) >= 3) flags.add('priority');
  }

  // Keep action consistent with tier (an AI can never propose closing L3/L4)
  if (!['REQUEST_MORE_INFO', 'MERGE_DUPLICATE'].includes(action) || rank(tier) >= 3) {
    const want = defaultAction(tier);
    if (action !== want && !(action === 'MERGE_DUPLICATE' && tier !== 'L4')) {
      if (rank(tier) >= 2 || action !== 'AUTO_RESOLVE_L1') { changes.push({ rule: 'TIER', from: action, to: want, why: 'Action must match tier' }); action = want; }
    }
  }
  if (tier === 'L4') action = 'ESCALATE_L4_IMMEDIATE';

  // 6. Auto-resolve gate
  let autoResolved = false;
  if (action === 'AUTO_RESOLVE_L1') {
    const blockers = [...flags].filter((f) => BLOCKS_AUTO.has(f));
    if (tier === 'L1' && confidence >= AUTO_RESOLVE_MIN_CONF && !blockers.length && (proposal.policy_refs || []).includes('SP-1')) {
      autoResolved = true;
    } else {
      changes.push({ rule: 'SP-1', from: 'AUTO_RESOLVE_L1', to: 'ROUTE_L2_REVIEW',
        why: 'Auto-resolve gate failed: ' + (blockers.length ? blockers.join(', ') : confidence < AUTO_RESOLVE_MIN_CONF ? `confidence ${confidence} < ${AUTO_RESOLVE_MIN_CONF}` : 'not an SP-1 category') });
      action = 'ROUTE_L2_REVIEW';
      flags.add('auto_resolve_blocked');
    }
  }

  const lane = tier === 'L4' ? 'critical' : tier === 'L3' ? 'priority' : autoResolved ? 'auto' : 'standard';
  return { tier, action, confidence: +confidence.toFixed(2), flags: [...flags].sort(), alert, locked, autoResolved, lane, changes };
}
