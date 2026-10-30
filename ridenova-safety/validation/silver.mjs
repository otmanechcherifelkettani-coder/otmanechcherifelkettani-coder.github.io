// Silver-label reference set for all 5,000 cases.
//
// Why this exists: the brief asks for 20–30 hand labels (see gold_labels.json). That is too
// few to measure recall on rare critical cases. While exploring the data we found that each
// synthetic case belongs to one of ~45 scenario templates, identifiable from the system-
// generated fields (telematics, toolkit log, attachments, history) plus, for one generic
// cluster, a few keywords. We labelled each SCENARIO once against the policy (by hand, see
// SCENARIOS below) and propagate that label to every case in it.
//
// This file is a validation instrument, NOT part of the triage path. The engine never
// imports it. It deliberately uses dataset-specific signatures that would not generalise.

const has = (s, sub) => (s || '').includes(sub);

const RACIST = /racis|razzis|rassis|rasis|rasist|rassit|عنصر|種族|人種|인종|नस्ल|वर्गवाद|ırkçı|accent|acento|sotaque|akzent|aktsen|akcent|accento|لهج|口音|訛|억양|उच्चारण|উচ্চারণ|aksan|акцент|skąd pochodzę/i;
const NUMBER_ASK = /number|n[uú]mero|num[eé]ro|nummer|numer|numara|رقم|番号|번호|नंबर|নম্বর|號碼|free|gratis|gratuit|bedava/i;

// scenario -> [tier, action, policy refs, note]
export const SCENARIOS = {
  stalking_at_home:      ['L4', 'ESCALATE_L4_IMMEDIATE', ['SP-7'], 'Reported party parked at reporter home after trip, app online: stalking in progress.'],
  sos_live:              ['L4', 'ESCALATE_L4_IMMEDIATE', ['SP-7'], 'Live SOS, trip in progress, route deviating, rider asking to be let out.'],
  medical_unresponsive:  ['L4', 'ESCALATE_L4_IMMEDIATE', ['SP-7'], 'Passenger unresponsive: medical emergency.'],
  location_exposure_prior: ['L4', 'ESCALATE_L4_IMMEDIATE', ['SP-6', 'SP-9'], 'Post-trip message revealing home location (L3) + prior L2 flag for same behaviour -> raised one level.'],
  threat_with_injection: ['L3', 'ROUTE_L3_REVIEW', ['SP-6'], 'Credible threat ("find me") hidden behind a prompt-injection attempt.'],
  threat_retaliation:    ['L3', 'ROUTE_L3_REVIEW', ['SP-6'], 'Threat of retaliation if reported.'],
  assault_counter_evidence: ['L3', 'ROUTE_L3_REVIEW', ['SP-8'], 'Assault allegation; counter-evidence exists but SP-8 requires human review.'],
  unwanted_touch:        ['L3', 'ROUTE_L3_REVIEW', ['SP-8', 'SP-6'], 'Non-consensual physical contact; continued after refusal.'],
  personal_questions_prior: ['L3', 'ROUTE_L3_REVIEW', ['SP-4', 'SP-6', 'SP-9'], 'Personal contact requests after refusal + prior L2 flag for same behaviour.'],
  collision_injury:      ['L3', 'ROUTE_L3_REVIEW', ['SP-3'], 'Collision with possible injury (impact event confirmed).'],
  stranded_extortion:    ['L3', 'ROUTE_L3_REVIEW', ['SP-4'], 'Off-app payment demand combined with unsafe action (left roadside).'],
  unregistered_passenger: ['L3', 'ROUTE_L3_REVIEW', ['SP-6'], 'Unknown person boarded mid-trip: vulnerable situation (policy gap, judged L3).'],
  physical_grab:         ['L3', 'ROUTE_L3_REVIEW', ['SP-8'], 'Physical contact (phone grabbed) by intoxicated rider: violence allegation.'],
  account_impersonation: ['L3', 'ROUTE_L3_REVIEW', ['SP-6'], 'Rider does not match account; possible account takeover — credible risk to driver and account owner.'],
  boundaries_vague:      ['L2', 'ROUTE_L2_REVIEW', ['SP-6'], 'Vague discomfort / possible advance; trip ended early. Needs human judgement.'],
  check_in_ok_vibe:      ['L2', 'ROUTE_L2_REVIEW', ['SP-1'], 'Safety feature engaged; no conduct alleged. Not SP-1 eligible because a safety signal exists.'],
  rude_repeat:           ['L2', 'ROUTE_L2_REVIEW', ['SP-1', 'SP-9'], 'Rude behaviour with 2 prior L1 flags for the same behaviour -> raised to L2.'],
  cash_request_cancel:   ['L2', 'ROUTE_L2_REVIEW', ['SP-4'], 'Asked for off-app cash, cancelled on refusal.'],
  phone_stop_ignored:    ['L2', 'ROUTE_L2_REVIEW', ['SP-3'], 'Long call while driving; stop request not honoured for 5 minutes (telematics confirms).'],
  vaping_after_request:  ['L2', 'ROUTE_L2_REVIEW', ['SP-2'], 'Vaping continued after request to stop.'],
  speeding_confirmed:    ['L2', 'ROUTE_L2_REVIEW', ['SP-3'], 'Speeding confirmed by telematics.'],
  harsh_driving_confirmed: ['L2', 'ROUTE_L2_REVIEW', ['SP-3'], 'Harsh braking / lane changes confirmed by telematics.'],
  service_animal_refusal: ['L2', 'ROUTE_L2_REVIEW', ['SP-5'], 'Service-animal refusal. Policy gap: treated like a discriminatory act (SP-5).'],
  property_damage_over_50: ['L2', 'ROUTE_L2_REVIEW', ['SP-2'], 'Spill with cleaning quote > USD 50.'],
  vehicle_mismatch:      ['L2', 'ROUTE_L2_REVIEW', ['SP-1'], 'Vehicle colour mismatch (plate matches). Not an SP-1 category; human verification.'],
  hard_brake_conflict:   ['L2', 'ROUTE_L2_REVIEW', ['SP-3'], 'Alarming allegation vs. single defensive brake at a pedestrian crossing. Conflicting signals -> human.'],
  discriminatory_remark: ['L2', 'ROUTE_L2_REVIEW', ['SP-5'], 'Single non-threatening discriminatory remark.'],
  personal_contact_ask:  ['L2', 'ROUTE_L2_REVIEW', ['SP-4'], 'Driver asked for personal number in exchange for free ride.'],
  missing_trip_record:   ['L2', 'REQUEST_MORE_INFO', [], 'Trip record unavailable, vague report: request more information.'],
  duplicate_followup:    [null, 'MERGE_DUPLICATE', [], 'Follow-up on an earlier case for the same trip: merge; inherits parent tier.'],
  rating_threat_closed_road: ['L1', 'AUTO_RESOLVE_L1', ['SP-1'], 'Rider threatened a bad rating; no safety threat.'],
  comfort_ac_music:      ['L1', 'AUTO_RESOLVE_L1', ['SP-1'], 'Temperature / music / luggage argument; minor conduct.'],
  lateness:              ['L1', 'AUTO_RESOLVE_L1', ['SP-1'], 'Late pickup explained by previous-trip overrun.'],
  door_slam_no_damage:   ['L1', 'AUTO_RESOLVE_L1', ['SP-1'], 'Door shut hard, no damage.'],
  crumbs_no_damage:      ['L1', 'AUTO_RESOLVE_L1', ['SP-1'], 'Crumbs, no stain or damage.'],
  added_stop_attitude:   ['L1', 'AUTO_RESOLVE_L1', ['SP-1'], 'Attitude about an added stop that was honoured.'],
  route_fare:            ['L1', 'AUTO_RESOLVE_L1', ['SP-1'], 'Route/fare complaint; detour from traffic incident, fare within tolerance.'],
  phone_use_refuted:     ['L1', 'AUTO_RESOLVE_L1', ['SP-1'], 'Phone-use allegation; telematics shows mounted phone, no handheld use.'],
  courier_rude:          ['L1', 'AUTO_RESOLVE_L1', ['SP-1'], 'Courier rude on intercom.'],
  courier_wrong_door:    ['L1', 'AUTO_RESOLVE_L1', ['SP-1'], 'Delivery to wrong door; service issue.'],
};

export function scenarioOf(c) {
  const t = c.telematics_summary || '', k = c.safety_toolkit_log || '', a = (c.attachments || []).join(' | ');
  const f = c.history?.reported_party_flags_12m || '', st = c.trip_context?.trip_status || '';
  if (t.startsWith('Driver app still online; GPS within')) return 'stalking_at_home';
  if (k.startsWith('SOS emergency')) return 'sos_live';
  if (has(t, 'road shoulder')) return 'medical_unresponsive';
  if (has(a, 'I know which building')) return 'location_exposure_prior';
  if (t.startsWith('ETA slip')) return 'threat_with_injection';
  if (has(t, 'rider rated trip 1 star')) return 'threat_retaliation';
  if (has(a, 'In-car audio transcript')) return 'assault_counter_evidence';
  if (k.startsWith('Rider shared trip with trusted contact at minute 3')) return 'unwanted_touch';
  if (has(f, 'inappropriate personal questions')) return has(t, 'Same reporter and same trip') ? 'duplicate_followup' : 'personal_questions_prior';
  if (t.startsWith('Impact event')) return 'collision_injury';
  if (t.startsWith('Trip ended 4.1 km short')) return 'stranded_extortion';
  if (t.startsWith('Vehicle seat count')) return 'unregistered_passenger';
  if (k.startsWith("Driver safety toolkit: 'Report issue'")) return 'physical_grab';
  if (t.startsWith('Account profile:')) return 'account_impersonation';
  if (has(t, 'Same reporter and same trip')) return 'duplicate_followup';
  if (k.includes('rider ended trip 7 minutes early')) return 'boundaries_vague';
  if (k.includes("check-in prompt answered")) return 'check_in_ok_vibe';
  if (has(f, '2xL1 (rude behavior)')) return 'rude_repeat';
  if (t.startsWith('Driver cancel after arrival')) return 'cash_request_cancel';
  if (t.startsWith('Hands-free call')) return 'phone_stop_ignored';
  if (has(a, 'vapor visible')) return 'vaping_after_request';
  if (t.startsWith('Max ')) return 'speeding_confirmed';
  if (t.startsWith('4 hard-brake')) return 'harsh_driving_confirmed';
  if (has(t, 'service animal')) return 'service_animal_refusal';
  if (has(a, 'Cleaning quote')) return 'property_damage_over_50';
  if (t.startsWith('Plate matches')) return 'vehicle_mismatch';
  if (t.startsWith('1 hard-brake event')) return 'hard_brake_conflict';
  if (t.startsWith('Trip record retrieval error')) return 'missing_trip_record';
  if (t.startsWith('Pickup ETA slipped')) return 'lateness';
  if (has(a, 'door closed normally')) return 'door_slam_no_damage';
  if (has(a, 'crumbs')) return 'crumbs_no_damage';
  if (t.startsWith('Added stop honored')) return 'added_stop_attitude';
  if (t.startsWith('Route ')) return 'route_fare';
  if (t.startsWith('Phone in a dashboard mount')) return 'phone_use_refuted';
  if (t.startsWith('Delivery completed on time')) return 'courier_rude';
  if (t.startsWith('Delivery marked completed')) return 'courier_wrong_door';
  if (t === 'No anomalies.' && st === 'completed') {
    if (c.reporter_role === 'driver') return RACIST.test(c.report_text) ? 'discriminatory_remark' : 'rating_threat_closed_road';
    return NUMBER_ASK.test(c.report_text) ? 'personal_contact_ask' : 'comfort_ac_music';
  }
  return 'UNMAPPED';
}

// Returns Map(case_id -> {scenario, tier, action, policy, note, parent?})
export function silverLabels(cases) {
  const out = new Map();
  const byTrip = new Map();
  const sorted = [...cases].sort((a, b) => a.case_id.localeCompare(b.case_id));
  for (const c of sorted) {
    const scenario = scenarioOf(c);
    const [tier, action, policy, note] = SCENARIOS[scenario] || [null, null, [], 'unmapped'];
    const rec = { scenario, tier, action, policy, note };
    if (scenario === 'duplicate_followup') {
      const parent = (byTrip.get(c.trip_id) || []).find(p => p.reporter_id === c.reporter_id);
      if (parent) { rec.parent = parent.case_id; rec.tier = out.get(parent.case_id).tier; }
      else rec.tier = 'L2';
    }
    out.set(c.case_id, rec);
    if (!byTrip.has(c.trip_id)) byTrip.set(c.trip_id, []);
    byTrip.get(c.trip_id).push(c);
  }
  return out;
}
