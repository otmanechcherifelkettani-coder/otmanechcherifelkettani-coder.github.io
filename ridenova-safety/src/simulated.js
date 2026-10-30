// SIMULATED AI — the key-free demo stand-in for the LLM.
//
// It reads the same redacted inputs the live model would (system fields are English; the report
// text is matched against a multilingual concept lexicon) and returns the same output contract
// as the live provider. It is deliberately conservative: when it cannot positively recognise a
// minor complaint it routes the case to a human. Every output is labelled mode:'simulated'.

import { maxTier, raiseTier, rank, defaultAction } from './policy.js';
import { extractSignals } from './signals.js';

export const CATEGORY_GLOSS = {
  sos: 'Live SOS triggered during an active trip.',
  stalking: 'Reported party appears to be waiting at the reporter’s home after the trip.',
  medical: 'Passenger reported as unresponsive / medically unwell; vehicle stopped.',
  danger: 'Report describes ongoing or imminent danger.',
  post_trip_contact: 'Post-trip message suggesting the reported party knows where the reporter lives.',
  threat: 'Reporter describes a threat of harm or retaliation.',
  violence: 'Allegation of physical violence or unwanted physical/sexual contact.',
  unsafe_drop: 'Reporter left in an unsafe place after a demand for extra money.',
  collision: 'Collision with possible injury.',
  vulnerable: 'Unknown person boarded mid-trip (vulnerable situation).',
  impersonation: 'Rider does not match the account holder; possible account takeover.',
  personal_contact: 'Request for personal contact or inappropriate personal questions.',
  off_app_payment: 'Request for off-app cash payment.',
  discrimination: 'Discriminatory remark or refusal.',
  property: 'Property damage claim with a cleaning quote.',
  smoking: 'Vaping/smoking after being asked to stop.',
  driving: 'Unsafe driving confirmed by telematics.',
  driving_conflict: 'Alarming driving allegation; telematics shows a single (possibly defensive) brake.',
  vehicle_check: 'Vehicle details do not match the profile; verification needed.',
  discomfort: 'Reporter felt uncomfortable and used safety features; no specific act described.',
  missing: 'Too little information and the trip record is unavailable.',
  conduct: 'Minor conduct / comfort / service complaint.',
  rating_threat: 'Rider threatened a bad rating; no safety threat.',
  unclassified: 'Could not confidently classify — human review.',
};

function cand(category, tier, conf, policy, why, action) {
  return { category, tier, conf, policy, why, action: action || defaultAction(tier) };
}

export function simulateTriage(c) {
  const s = extractSignals(c);
  const C = [];

  // L4 — SP-7 danger signals
  if (s.sos) C.push(cand('sos', 'L4', 0.97, ['SP-7'], 'Toolkit shows a live SOS' + (s.routeDeviation ? ' and telematics shows route deviation' : '') + '.'));
  if (s.homeProximity) C.push(cand('stalking', 'L4', 0.9, ['SP-7'], 'Telematics: reported party’s app online and GPS near the reporter’s home with no active trip — possible stalking in progress.'));
  if ((s.danger || s.liveIncident) && s.roadsideStop) C.push(cand('medical', 'L4', 0.9, ['SP-7'], 'Report describes an unresponsive/unwell person; telematics shows the vehicle stopped roadside mid-trip.'));
  else if (s.danger) C.push(cand('danger', 'L4', 0.8, ['SP-7'], 'Report text contains danger-signal language.'));

  // L3
  if (s.locationMessage) C.push(cand('post_trip_contact', 'L3', 0.9, ['SP-6'], 'Evidence: post-trip message indicating the reported party knows where the reporter lives.'));
  if (s.threat) C.push(cand('threat', 'L3', s.threatHarm ? 0.82 : 0.7, ['SP-6'], 'Report describes a threat of harm or retaliation.'));
  if (s.violence) C.push(cand('violence', 'L3', s.counterEvidence ? 0.7 : 0.85, ['SP-8'], 'Allegation of physical violence or unwanted physical contact' + (s.tripShared || s.endedEarly ? '; trip shared/ended early (toolkit).' : '.') + (s.counterEvidence ? ' Counter-evidence exists but SP-8 requires human review.' : '')));
  if (s.shortDrop && (s.cash || s.threat)) C.push(cand('unsafe_drop', 'L3', 0.85, ['SP-4'], 'Demand for extra cash combined with an unsafe drop-off (trip ended short near a highway).'));
  else if (s.shortDrop) C.push(cand('unsafe_drop', 'L3', 0.6, ['SP-4'], 'Trip ended short of destination in a potentially unsafe place.'));
  if (s.impact) C.push(cand('collision', 'L3', 0.8, ['SP-3'], 'Telematics confirms an impact event; reporter describes possible injury.'));
  if (s.unregisteredPassenger) C.push(cand('vulnerable', 'L3', 0.72, ['SP-6'], 'Telematics: an unregistered passenger boarded mid-trip. Policy does not name this explicitly; judged a vulnerable situation.'));
  if (s.accountMismatch) C.push(cand('impersonation', 'L3', 0.7, ['SP-6'], 'Telematics/account: rider does not match profile and logged in from a new device — possible account takeover.'));

  // L2
  if (s.personalContact && !s.discrimination) C.push(cand('personal_contact', 'L2', 0.75, ['SP-4'], 'Request for personal contact / personal questions.'));
  if (s.cash || s.cancelAfterArrival) C.push(cand('off_app_payment', 'L2', s.cash ? 0.85 : 0.55, ['SP-4'], 'Request for off-app cash' + (s.cancelAfterArrival ? '; telematics shows a cancel after arrival with no payment event.' : '.')));
  if (s.discrimination) C.push(cand('discrimination', 'L2', 0.8, ['SP-5'], 'Single discriminatory remark, no threat reported.'));
  if (s.serviceAnimal) C.push(cand('discrimination', 'L2', 0.75, ['SP-5'], 'Driver cancelled after arrival; rider has a service-animal flag. Policy gap: treated as discriminatory refusal.'));
  if (s.cleaningUsd != null) C.push(cand('property', s.cleaningUsd > 50 ? 'L2' : 'L1', 0.9, ['SP-2'], `Cleaning quote ≈ USD ${s.cleaningUsd} (${s.cleaningUsd > 50 ? 'over' : 'under'} the USD 50 threshold).`));
  if (s.vapor) C.push(cand('smoking', 'L2', 0.85, ['SP-2'], 'Photo shows vapour in the cabin; report says it continued after a request to stop.'));
  if (s.speeding || s.harsh) C.push(cand('driving', 'L2', 0.9, ['SP-3'], 'Speeding / harsh driving confirmed by telematics.'));
  if (s.stopNotHonored) C.push(cand('driving', 'L2', 0.8, ['SP-3'], 'Telematics: long call while driving and an in-app stop request not honoured for 5 minutes.'));
  if (s.singleBrake) C.push(cand('driving_conflict', 'L2', 0.55, ['SP-3'], 'Telematics shows one hard brake at a pedestrian crossing, no collision, 4-star rating — not "confirmed harsh driving". Conflicts with the alarming allegation.'));
  if (s.plateColourMismatch) C.push(cand('vehicle_check', 'L2', 0.6, ['SP-1'], 'Plate matches but vehicle colour differs from profile; outside SP-1 categories — verify vehicle record.'));
  if (s.toolkitActivity && (s.tripShared || s.endedEarly || s.checkInOk) && !s.violence && !s.sos) C.push(cand('discomfort', 'L2', 0.55, ['SP-6'], 'Reporter used safety features (trip shared' + (s.endedEarly ? ', ended early' : '') + (s.checkInOk ? ', check-in answered OK' : '') + '); a safety signal exists so SP-1 auto-close does not apply.'));
  if (s.reportIssueTapped && !s.violence) C.push(cand('discomfort', 'L2', 0.6, ['SP-8'], 'Driver tapped “Report issue” in the toolkit.'));
  if (s.missingTrip) C.push(cand('missing', 'L2', 0.6, [], 'Trip record unavailable and the report lacks detail.', 'REQUEST_MORE_INFO'));

  // L1 — SP-1 allow-list (positive recognition only)
  if (s.ratingThreatOnly && !s.threat) C.push(cand('rating_threat', 'L1', 0.75, ['SP-1'], 'Threat concerns a rating/account complaint only — not a threat of harm.'));
  if (s.minorSystem) C.push(cand('conduct', 'L1', 0.9, ['SP-1'], 'System data explains the complaint (lateness, route/fare within tolerance, stop honoured, no damage, phone mounted, or delivery service issue).'));
  else if (s.minorText) C.push(cand('conduct', 'L1', 0.78, ['SP-1'], 'Minor conduct / comfort / service complaint.'));

  if (!C.length) C.push(cand('unclassified', 'L2', 0.4, [], 'No recognised pattern — routed to a human rather than auto-resolved.'));

  // pick the most severe; break ties on confidence
  C.sort((a, b) => rank(b.tier) - rank(a.tier) || b.conf - a.conf);
  const top = { ...C[0] };
  let tier = top.tier;
  const policy = new Set(C.filter((x) => rank(x.tier) === rank(tier) || x.category === top.category).flatMap((x) => x.policy));
  const others = [...new Set(C.slice(1, 3).map((x) => x.why))].filter((w) => w !== top.why);
  const why = [top.why, ...(others.length ? ['Also noted: ' + others.join(' ')] : [])];
  const flags = [];

  // SP-9 — prior flag for the same behaviour raises the tier one level
  const sameBehaviour = s.priorCategory && (s.priorCategory === top.category ||
    (s.priorCategory === 'post_trip_contact' && ['post_trip_contact', 'personal_contact'].includes(top.category)) ||
    (s.priorCategory === 'personal_contact' && ['personal_contact', 'discomfort'].includes(top.category)) ||
    (s.priorCategory === 'conduct' && top.category === 'conduct'));
  if (sameBehaviour) {
    const raised = raiseTier(tier);
    why.push(`Prior flag for the same behaviour (${s.priorFlags}) — SP-9 raises ${tier} → ${raised}.`);
    tier = raised; policy.add('SP-9'); flags.push('prior_same_behaviour');
    if (top.category === 'personal_contact' || top.category === 'discomfort') top.category = 'personal_contact';
  }

  // Conflicting / uncertain signals
  const tiersSeen = new Set(C.map((x) => x.tier));
  if (s.counterEvidence && (s.violence || s.threat)) flags.push('conflicting_signals');
  if (top.category === 'driving_conflict') flags.push('conflicting_signals');
  if (tiersSeen.size > 2) flags.push('mixed_signals');
  let conf = top.conf;
  if (tiersSeen.size > 2) conf -= 0.05;
  if (top.category === 'unclassified' || top.conf < 0.6) flags.push('uncertain');

  const action = top.action === 'REQUEST_MORE_INFO' && rank(tier) <= 2 ? 'REQUEST_MORE_INFO' : defaultAction(tier);
  return {
    mode: 'simulated', provider: 'SimulatedProvider', model: 'rules+lexicon v1',
    category: top.category, tier, action, confidence: Math.max(0.05, Math.min(0.99, +conf.toFixed(2))),
    policy_refs: [...policy].sort(), flags, rationale: why.join(' '),
    summary: CATEGORY_GLOSS[top.category] || CATEGORY_GLOSS.unclassified,
    signals: s,
  };
}

export { maxTier };
