// Validation of model output. Live triage output is untrusted until it passes this check;
// invalid fields fall back to the safest values (L3 human review) and are flagged.

import { ACTIONS, TIERS } from './policy.js';

// Model output is untrusted until validated; invalid fields fall back to the safest value.
export function validateTriage(r = {}) {
  const tier = TIERS[r.tier] ? r.tier : 'L3';
  const action = ACTIONS.includes(r.action) ? r.action : 'ROUTE_L3_REVIEW';
  const confidence = Number.isFinite(+r.confidence) ? Math.max(0, Math.min(1, +r.confidence)) : 0.3;
  return {
    category: String(r.category || 'unclassified').slice(0, 40), tier, action, confidence,
    rationale: String(r.rationale || '').slice(0, 1200), summary: String(r.summary || '').slice(0, 600),
    translation: r.translation ? String(r.translation).slice(0, 2000) : null,
    policy_refs: (r.policy_refs || []).filter((x) => /^SP-[1-9]$/.test(x)),
    flags: (r.flags || []).filter((x) => /^[a-z_]{3,40}$/.test(x)).concat(TIERS[r.tier] && ACTIONS.includes(r.action) ? [] : ['ai_output_invalid']),
  };
}
