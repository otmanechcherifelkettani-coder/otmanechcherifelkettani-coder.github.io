// Routing precedence: A (duty manager) -> B (eligible automation) -> C (agent review).
// Severity, lane, workflow status and permissions are separate concepts; this module only
// decides the LANE and QUEUE from the current state.

import { CATEGORY_CAPABILITY, capabilityQueue, SUPPORTED_LANGUAGES } from './catalog.js';

export const AUTOMATION_MIN_CONFIDENCE = 0.75;
const SP1_CATEGORIES = new Set(['conduct', 'rating_threat']);

export const dangerActive = (state) => ['detected', 'ongoing'].includes(state.danger.status);

// Lane B eligibility. Every exclusion is listed so the record shows WHY a case was not automated.
// L1 alone never makes a case eligible.
export function automationEligibility(state) {
  const r = [];
  const f = new Set(state.flags);
  if (state.severity.current !== 'L1') r.push('not_L1');
  if (!state.policy.applicable.includes('SP-1') || !SP1_CATEGORIES.has(state.ai.category)) r.push('no_explicit_SP1_eligibility');
  if (state.evidence_completeness !== 'complete') r.push('material_evidence_missing');
  if (!state.understanding.supported || !SUPPORTED_LANGUAGES.has(state.language) && state.ai.mode !== 'live') r.push('language_not_supported');
  if (f.has('violence_or_sexual_allegation') || f.has('credible_threat_language')) r.push('protected_allegation');
  if (dangerActive(state) || state.danger.alerts.length) r.push('danger_signal');
  if (f.has('prior_flags')) r.push('repeat_pattern_history');
  if (state.policy.gap || state.policy.not_covered) r.push('policy_gap');
  if (f.has('injection_detected')) r.push('injection_detected');
  if (state.policy.conflicts.length || f.has('conflicting_signals')) r.push('conflicting_signals');
  if (state.confidence < AUTOMATION_MIN_CONFIDENCE) r.push('low_confidence');
  if (state.links.candidates.length) r.push('candidate_linked_case');
  if (f.has('safety_feature_used')) r.push('safety_feature_used');
  if (state.severity.reviewed && state.severity.reviewed !== state.severity.proposed) r.push('human_reassessed');
  if (state.automation.release_required) r.push('automation_not_released_after_reassessment');
  return { eligible: r.length === 0, reasons: r };
}

export function requiredCapability(state) {
  if (state.severity.current !== 'L3') return 'general';
  return CATEGORY_CAPABILITY[state.ai.category] || (state.flags.includes('injection_detected') || state.flags.includes('credible_threat_language') ? 'threats_exposure'
    : state.flags.includes('violence_or_sexual_allegation') ? 'violence_sexual' : 'safety_incidents');
}

// mode: 'shadow' (default: compute eligibility, route to agents) or 'enabled' (demo only).
export function route(state, mode = 'shadow') {
  if (dangerActive(state) || state.severity.current === 'L4') {
    return { lane: 'manager', queue: 'duty-managers', reason: dangerActive(state) ? 'danger_signal' : 'L4' };
  }
  const elig = automationEligibility(state);
  if (elig.eligible && mode === 'enabled') return { lane: 'automation', queue: 'automation', reason: 'eligible_SP1', eligibility: elig };
  const cap = requiredCapability(state);
  return { lane: 'agent', queue: cap === 'general' ? 'general-review' : capabilityQueue(cap), reason: elig.eligible ? 'shadow_mode' : 'human_review_required', eligibility: elig, capability: cap };
}
