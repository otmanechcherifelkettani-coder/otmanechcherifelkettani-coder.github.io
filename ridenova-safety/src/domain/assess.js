// Intake assessment: evidence structure, AI proposal, deterministic floors, policy assessment
// and a concrete recommendation. Pure functions; no state.

import { extractSignals, unifiedFacts } from '../signals.js';
import { applyGuardrails } from '../guardrails.js';
import { simulateTriage, CATEGORY_GLOSS } from '../simulated.js';
import { policyById } from '../policy.js';
import { POLICY_VERSION, SUPPORTED_LANGUAGES, CATEGORY_CAPABILITY, capabilityQueue, rank } from './catalog.js';

export const DANGER_CATEGORIES = new Set(['sos', 'stalking', 'medical', 'danger']);
export const POLICY_GAP_CATEGORIES = { vulnerable: 'Unregistered passenger is not named in SP-1..SP-9', impersonation: 'Account takeover is not named in SP-1..SP-9',
  discomfort: 'Safety-feature use without an alleged act is not named in SP-1..SP-9', unclassified: 'No clause is supported by the available understanding of the report' };
const SP1_CATEGORIES = new Set(['conduct', 'rating_threat']);

// Structured danger checks run FIRST and need no text understanding or AI (an SOS never waits).
export function structuredDanger(c, s = extractSignals(c)) {
  const out = [];
  if (s.sos) out.push({ signal: 'live_sos', label: 'Live SOS pressed', source: 'toolkit' });
  if (s.homeProximity) out.push({ signal: 'party_near_home', label: 'Reported party’s GPS near reporter’s home after the trip, app online', source: 'telematics' });
  if (s.liveIncident) out.push({ signal: 'live_incident_stopped', label: 'Report filed mid-trip with the vehicle stopped roadside', source: 'trip' });
  return out;
}

export function evidenceSources(c, s = extractSignals(c), at) {
  const facts = unifiedFacts(c);
  const tripErr = /retrieval error/i.test(c.telematics_summary || '') || c.trip_context?.trip_status === 'unknown';
  const src = (id, name, kind, status, missing = []) => ({ id, name, kind, status, missing, version: 'v1', retrieved_at: at, facts: facts.filter((f) => f.source === id) });
  return [
    src('ticket', 'Ticketing', 'allegation', 'ok'),
    src('trip', 'Trip system', 'system', tripErr ? 'error' : 'ok', tripErr ? ['trip record (timeout)'] : []),
    src('history', 'Case history', 'history', c.history?.reported_party_flags_12m === 'unknown' ? 'partial' : 'ok', c.history?.reported_party_flags_12m === 'unknown' ? ['reported-party flags'] : []),
    src('toolkit', 'Safety toolkit', 'system', 'ok'),
    src('telematics', 'Telematics', 'system', tripErr ? 'error' : 'ok', tripErr ? ['GPS / driving signals'] : []),
    src('evidence', 'Evidence store', 'evidence', 'ok'),
    src('identity', 'Identity vault', 'pii', c.pii?.reported_party ? 'ok' : 'partial', c.pii?.reported_party ? [] : ['reported party identity']),
  ];
}

function conditions(s, proposal) {
  const C = [];
  const add = (policy, condition, source, basis) => C.push({ policy, condition, source, basis });
  if (s.sos) add('SP-7', 'Live SOS during the trip', 'toolkit', 'system observation');
  if (s.homeProximity) add('SP-7', 'Reported party waiting near reporter’s home (stalking in progress)', 'telematics', 'system observation');
  if (s.liveIncident) add('SP-7', 'Ongoing situation: report filed mid-trip, vehicle stopped', 'trip', 'system observation');
  if (s.danger) add('SP-7', 'Report describes ongoing or imminent danger', 'ticket', 'allegation');
  if (s.violence) add('SP-8', 'Allegation of violence or unwanted physical/sexual contact', 'ticket', 'allegation');
  if (s.threat) add('SP-6', 'Report describes a threat of harm or retaliation', 'ticket', 'allegation');
  if (s.locationMessage) add('SP-6', 'Post-trip message revealing the reporter’s location', 'evidence', 'submitted evidence');
  if (s.impact) add('SP-3', 'Collision (impact event) with possible injury', 'telematics', 'system observation');
  if (s.speeding || s.harsh) add('SP-3', 'Speeding / harsh driving confirmed by telematics', 'telematics', 'system observation');
  if (s.stopNotHonored) add('SP-3', 'Stop request not honoured during a long call', 'telematics', 'system observation');
  if (s.cash) add('SP-4', 'Request for off-app payment', 'ticket', 'allegation');
  if (s.cancelAfterArrival) add('SP-4', 'Cancel after arrival with no payment event', 'telematics', 'system observation');
  if (s.shortDrop) add('SP-4', 'Trip ended short in a potentially unsafe place', 'telematics', 'system observation');
  if (s.personalContact) add('SP-4', 'Request for personal contact / personal questions', 'ticket', 'allegation');
  if (s.discrimination) add('SP-5', 'Discriminatory remark', 'ticket', 'allegation');
  if (s.serviceAnimal) add('SP-5', 'Cancel after arrival; rider has a service-animal flag (policy gap)', 'telematics', 'system observation');
  if (s.cleaningUsd != null) add('SP-2', `Cleaning quote ≈ USD ${s.cleaningUsd} (${s.cleaningUsd > 50 ? 'over' : 'under'} USD 50)`, 'evidence', 'submitted evidence');
  if (s.vapor) add('SP-2', 'Vaping after a request to stop', 'evidence', 'submitted evidence');
  if ((proposal.flags || []).includes('prior_same_behaviour')) add('SP-9', `Prior flag for the same behaviour: ${s.priorFlags}`, 'history', 'historical');
  if (s.minorSystem) add('SP-1', 'System data explains a minor/lateness/route/service complaint', 'telematics', 'system observation');
  else if (s.minorText && SP1_CATEGORIES.has(proposal.category)) add('SP-1', 'Minor conduct / comfort complaint, no safety signal', 'ticket', 'allegation');
  return C;
}

export function assessPolicy(c, proposal, s, floors, understanding) {
  const conds = conditions(s, proposal);
  const applicable = [...new Set([...conds.map((x) => x.policy), ...(proposal.policy_refs || [])])].filter((p) => policyById[p]).sort();
  const checks = [];
  if (floors.flags.includes('danger_signal')) checks.push({ policy: 'SP-7', check: 'Duty manager alerted immediately; automation may not close, downgrade or resolve' });
  if (s.violence) checks.push({ policy: 'SP-8', check: 'Human review required regardless of counter-evidence' });
  if ((proposal.flags || []).includes('prior_same_behaviour')) checks.push({ policy: 'SP-9', check: 'Confirm the new report is credible before applying the +1 tier' });
  if (s.injection) checks.push({ policy: '—', check: 'Report contains instructions aimed at the triage system: treated as data, specialist review' });
  const conflicts = [];
  if (s.counterEvidence && (s.violence || s.threat)) conflicts.push('Allegation conflicts with system/counter-evidence (audio transcript or counter-report). Note: counter-evidence never closes an SP-8 case.');
  if (s.singleBrake) conflicts.push('Alarming driving allegation vs one 0.6g brake at a pedestrian crossing (no collision, 4-star rating).');
  if (s.plateColourMismatch) conflicts.push('Vehicle colour differs from profile although the plate matches.');
  const missing = [];
  if (s.missingTrip) missing.push('Trip record unavailable / reported party unknown');
  if (!understanding.supported) missing.push(`Report language “${c.language}” is not understood by the active provider; translation unavailable`);
  const gap = POLICY_GAP_CATEGORIES[proposal.category] || (s.serviceAnimal ? 'Service-animal refusal is not named in SP-1..SP-9 (treated under SP-5)' : null);
  return {
    version: POLICY_VERSION, applicable, conditions: conds, mandatory_human_checks: checks, conflicts, missing,
    not_covered: !applicable.length || proposal.category === 'unclassified', gap,
  };
}

export function recommend(state) {
  const { severity, ai, danger, policy, understanding } = state;
  const t = severity.current;
  const cat = ai.category;
  if (danger.status === 'detected' || danger.status === 'ongoing' || t === 'L4') {
    return { next_step: 'Acknowledge and own the alert, call the reporter now, and decide on emergency services. Restrict contact between the parties while the situation is unclear.',
      actor: 'duty_manager', urgency: 'immediate', approval_required: false, destination: 'duty-managers', proposed_action: 'ESCALATE_L4_IMMEDIATE', exec_actions: ['restrict_rematch', 'suspend_reported_party'] };
  }
  if (state.links.candidates.length && /follow|waiting|earlier/i.test(state.report_text_hint || '')) {
    return { next_step: `Review the candidate link to ${state.links.candidates[0].case_id}, then reply to the reporter with the status of the earlier report.`, actor: 'agent', urgency: t === 'L3' ? '4h' : '24h',
      approval_required: false, destination: state.queue, proposed_action: 'MERGE_DUPLICATE', exec_actions: ['safety_followup'] };
  }
  if (!understanding.supported && !policy.applicable.length) {
    return { next_step: 'Report not understood by the active provider. Read it with a qualified-language reviewer, classify it, then choose an action.', actor: 'agent', urgency: '24h',
      approval_required: false, destination: 'general-review', proposed_action: 'ROUTE_L2_REVIEW', exec_actions: ['request_more_info'] };
  }
  if (policy.missing.some((m) => /Trip record/.test(m))) {
    return { next_step: 'Ask the reporter for the trip date, time and what happened; the trip record could not be retrieved.', actor: 'agent', urgency: '24h', approval_required: false,
      destination: 'general-review', proposed_action: 'REQUEST_MORE_INFO', exec_actions: ['request_more_info'] };
  }
  if (t === 'L3') {
    const cap = CATEGORY_CAPABILITY[cat] || (state.flags.includes('injection_detected') ? 'threats_exposure' : 'safety_incidents');
    const steps = {
      violence: 'Contact the reporter to confirm safety and details; restrict re-matching; open an investigation. Counter-evidence does not close this case (SP-8).',
      threat: 'Contact the reporter to confirm safety; review the reported party’s messages; restrict re-matching pending investigation.',
      post_trip_contact: 'Contact the reporter; preserve the message evidence; suspend the reported party pending investigation.',
      personal_contact: 'Contact the reporter; given the prior flag for the same behaviour, restrict re-matching and open an investigation.',
      collision: 'Check on the reporter’s injury, offer medical-support guidance, and open a collision investigation.',
      unsafe_drop: 'Confirm the reporter is safe; investigate the off-app payment demand; restrict re-matching.',
      vulnerable: 'Contact the reporter; investigate the unauthorised passenger with the driver.',
      impersonation: 'Lock the rider account pending verification; inform the driver; route to account integrity.',
    };
    return { next_step: steps[cat] || 'Specialist review: confirm safety with the reporter and investigate.', actor: `specialist:${cap}`, urgency: '4h', approval_required: true,
      destination: capabilityQueue(cap), proposed_action: 'ROUTE_L3_REVIEW', exec_actions: ['safety_followup', 'restrict_rematch'] };
  }
  if (t === 'L2') {
    const map = {
      property: ['Verify the cleaning quote and charge the cleaning fee to the rider (SP-2).', 'charge_cleaning_fee'],
      smoking: ['Send a policy warning to the rider about vaping (SP-2).', 'warn_reported_party'],
      driving: ['Send a driving-safety warning to the driver, citing the telematics evidence (SP-3).', 'warn_reported_party'],
      driving_conflict: ['Telematics does not confirm harsh driving. Reply to the reporter explaining what was found; no violation unless new evidence.', 'send_feedback_note'],
      off_app_payment: ['Warn the driver about off-app payment requests (SP-4) and reassure the reporter.', 'warn_reported_party'],
      personal_contact: ['Warn the driver about personal-contact requests (SP-4).', 'warn_reported_party'],
      discrimination: ['Warn the reported party about discriminatory remarks (SP-5).', 'warn_reported_party'],
      vehicle_check: ['Ask the driver to update the vehicle record; confirm to the reporter.', 'send_feedback_note'],
      discomfort: ['Contact the reporter, offer to block re-matching, and ask whether anything else happened.', 'safety_followup'],
      conduct: ['Repeat pattern (SP-9): warn the reported party about conduct and reply to the reporter.', 'warn_reported_party'],
    };
    const [next, act] = map[cat] || ['Review the report and choose an action.', 'send_feedback_note'];
    return { next_step: next, actor: 'agent', urgency: '24h', approval_required: false, destination: 'general-review', proposed_action: 'ROUTE_L2_REVIEW', exec_actions: [act] };
  }
  return { next_step: 'Send a feedback / no-violation note to the reporter (SP-1). Optionally add a goodwill credit.', actor: state.automation?.eligible ? 'automation' : 'agent', urgency: '48h',
    approval_required: false, destination: state.automation?.eligible ? 'automation' : 'general-review', proposed_action: 'AUTO_RESOLVE_L1', exec_actions: ['send_feedback_note'] };
}

// Full intake assessment for one case with a given provider proposal (simulated or live).
export function assessCase(c, proposal = simulateTriage(c)) {
  const s = proposal.signals || extractSignals(c);
  const floors = applyGuardrails(c, proposal, s, {});
  const understanding = { language: c.language, supported: SUPPORTED_LANGUAGES.has(c.language) || proposal.mode === 'live',
    translation: c.language === 'en' ? 'not_needed' : proposal.mode === 'live' ? 'live' : 'unavailable_or_fixture' };
  const structured = structuredDanger(c, s);
  const textDanger = s.danger && !structured.length ? [{ signal: 'danger_language', label: 'Report text describes danger', source: 'ticket' }] : [];
  const aiDanger = proposal.tier === 'L4' && !structured.length && !textDanger.length ? [{ signal: 'ai_l4', label: 'AI proposed L4', source: 'ai' }] : [];
  const policy = assessPolicy(c, proposal, s, floors, understanding);
  let current = floors.tier;
  // Not understood -> provisional L2 human review, never a low-risk default.
  const provisional = proposal.category === 'unclassified' || !understanding.supported && rank(current) < 2;
  if (!understanding.supported && rank(current) < 2) current = 'L2';
  return {
    signals: s, structured_danger: structured, other_danger: [...textDanger, ...aiDanger],
    ai: {
      severity: proposal.tier, confidence: proposal.confidence, calibration: 'uncalibrated — no adjudicated production labels', category: proposal.category,
      rationale: proposal.rationale, summary: proposal.summary || CATEGORY_GLOSS[proposal.category], uncertainty: [...(proposal.flags || []).filter((f) => ['uncertain', 'mixed_signals', 'conflicting_signals'].includes(f)), ...(proposal.uncertainty ? [proposal.uncertainty] : [])],
      mode: proposal.mode, model: proposal.model, policy_refs: proposal.policy_refs || [], translation: proposal.translation || null,
    },
    floor_tier: current, floor_changes: floors.changes, flags: floors.flags.filter((f) => f !== 'auto_resolve_blocked' && f !== 'duplicate'),
    confidence: floors.confidence, provisional, understanding, policy,
    evidence_completeness: s.missingTrip ? 'missing_material' : 'complete',
  };
}
