// Unify the mocked source systems into one fact list with provenance, and extract the
// deterministic signals used by guardrails and the simulated classifier.

import { LEX, INJECTION } from './lexicon.js';

// Each nested block is treated as a separate source system (see data dictionary).
export const SOURCES = {
  ticket:     { name: 'Ticketing', kind: 'allegation', hint: 'Reporter’s own words — unverified' },
  trip:       { name: 'Trip system', kind: 'system', hint: 'Trip record' },
  history:    { name: 'Case history', kind: 'history', hint: 'Prior reports and flags' },
  toolkit:    { name: 'Safety toolkit', kind: 'system', hint: 'In-app safety-feature events' },
  telematics: { name: 'Telematics', kind: 'system', hint: 'GPS / driving signals' },
  evidence:   { name: 'Evidence store', kind: 'evidence', hint: 'Attachment descriptions (submitted by a party)' },
  identity:   { name: 'Identity vault', kind: 'pii', hint: 'Personal data — masked by role' },
  ai:         { name: 'AI groundwork', kind: 'ai', hint: 'Model interpretation — verify before acting' },
  rules:      { name: 'Policy guardrails', kind: 'rule', hint: 'Deterministic, non-AI' },
};

export function unifiedFacts(c) {
  const f = [];
  const add = (source, label, value) => f.push({ source, label, value });
  add('ticket', 'Channel', c.channel);
  add('ticket', 'Language', c.language);
  add('ticket', 'Reporter → reported', `${c.reporter_role} → ${c.reported_party_role}`);
  add('ticket', 'Submitted (local)', c.submitted_at.replace('T', ' '));
  add('trip', 'Trip ID', c.trip_id);
  add('trip', 'Product', c.trip_context?.product);
  add('trip', 'Region', c.trip_context?.region);
  add('trip', 'Local time of event', c.trip_context?.local_time);
  add('trip', 'Trip status', c.trip_context?.trip_status);
  add('history', 'Reporter reports (90d)', String(c.history?.reporter_reports_90d ?? 'unknown'));
  add('history', 'Reported-party flags (12m)', c.history?.reported_party_flags_12m);
  add('history', 'Reported-party tenure', `${c.history?.reported_party_tenure_months ?? '?'} months`);
  add('toolkit', 'Toolkit log', c.safety_toolkit_log || 'No toolkit events');
  add('telematics', 'Telematics summary', c.telematics_summary);
  for (const a of c.attachments || []) add('evidence', 'Attachment', a);
  if (!(c.attachments || []).length) add('evidence', 'Attachments', 'None');
  return f;
}

const num = (re, s) => { const m = (s || '').match(re); return m ? Number(m[1].replace(/,/g, '')) : null; };

export function priorFlagCategory(flags) {
  if (!flags || flags === 'none' || flags === 'unknown') return null;
  if (/rude/i.test(flags)) return 'conduct';
  if (/personal questions|personal contact/i.test(flags)) return 'personal_contact';
  if (/contact after trip|post-trip/i.test(flags)) return 'post_trip_contact';
  if (/speed|driving/i.test(flags)) return 'driving';
  return 'other';
}

// Negated mentions ("no threats", "nobody touched anyone", "sin amenazas") must not count.
const NEGATED = new RegExp([
  "\\b(no|not|without|zero|nor)\\b[^.!?]{0,25}?(threat\\w*|touch\\w*|physical\\w*|violen\\w*)",
  "no one touched \\w+", 'nobody touched', 'nobody threatened', 'ninguém (foi ameaçad|encostou)\\w*', 'ninguna amenaza', 'no me amenazó', 'न कोई धमकी', 'न कोई शारीरिक', '협박도 접촉도 없', 'ما فيه تهديد', 'ولا أي لمس', 'threat kichu (hoy|hoyni|na)',
  "\\b(sin|ni|nadie|ningún|ninguna)\\b[^.!?]{0,30}?(amenaz\\w*|toc\\w*|físic\\w*)", 'no hubo amenazas',
  "\\b(sans|pas de|aucune?)\\b[^.!?]{0,20}?menace\\w*", "\\b(sem|nem|nenhuma?)\\b[^.!?]{0,20}?(ameaça\\w*|toc\\w*)",
  "\\bkein\\w*\\b[^.!?]{0,20}?(droh\\w*|gewalt)", 'gedroht hat keiner', 'angefasst auch (keiner|niemand)',
  "\\bnessun\\w*\\b[^.!?]{0,20}?minacc\\w*", 'tehdit yok', 'ولا تهديد', 'بدون تهديد', 'ما في تهديد', '暴力的なことは何もなかった', '脅しはなかった',
  '협박은 없', '沒有威脅', '冇威脅', 'brak gróźb', 'ähvardusi ei olnud', 'žádné výhrůžky', 'nincs fenyeget', 'koi dhamki nahi', 'कोई धमकी नहीं',
].join('|'), 'giu');

const RATING_THREAT = /ruin|wreck|destroy|get me (deactivated|kicked|removed|banned)|lose my account|kicked off|make sure i|deactivat|desactiv|echaran|sacaran|hundir|arruin|destroz|bannir|désactiv|disattiv|rovinar|avstängd|banimento|removessem|desativad|퇴출|정지|deactivate|zablokov|zagorčati|uništiti|pilaa|बर्बाद|डीएक्टिवेट|تعطيل|アカウントなく/iu;

export function extractSignals(c) {
  const raw = c.report_text || '';
  const text = raw.replace(NEGATED, ' ');
  const t = c.telematics_summary || '';
  const k = c.safety_toolkit_log || '';
  const att = (c.attachments || []).join(' | ');
  const st = c.trip_context?.trip_status || '';
  const flags = c.history?.reported_party_flags_12m || '';
  const s = {
    // system signals (English, system-generated)
    sos: /SOS (emergency )?(button )?(pressed|triggered|alert)/i.test(k) || c.channel === 'safety_toolkit_auto',
    inProgress: st.startsWith('in_progress'),
    homeProximity: /GPS within \d+ m of rider home/i.test(t) && /no active trip/i.test(t),
    roadsideStop: /stationary .* road shoulder/i.test(t) || /in_progress \(stopped\)/.test(st),
    impact: /impact event detected/i.test(t),
    speeding: /Max \d+ (km\/h|mph) .* zone/i.test(t) || /over limit/i.test(t) && !/^4 hard-brake/.test(t),
    harsh: (num(/(\d+) hard-brake events/, t) || 0) >= 3 || /lane-change flags/i.test(t),
    singleBrake: /^1 hard-brake event/i.test(t),
    routeDeviation: /route deviating/i.test(t),
    unregisteredPassenger: /unregistered passenger/i.test(t),
    stopNotHonored: /stop request .* not honored/i.test(t),
    serviceAnimal: /service animal/i.test(t),
    cancelAfterArrival: /cancel(ed)? .*after arrival/i.test(t) || /cancel after arrival/i.test(t),
    shortDrop: /short of destination/i.test(t) || /ended_early; drop-off .* before destination/i.test(st),
    accountMismatch: /account profile:.*reports/i.test(t) || /login from new device/i.test(t),
    plateColourMismatch: /plate matches; profile vehicle colou?r/i.test(t),
    counterEvidence: /no raised voices|no contact indicators|closed no-violation|filed a .*report against reporter|no handheld-use/i.test(t + ' ' + att),
    tripShared: /shared? (the )?trip|trip shared/i.test(k),
    endedEarly: /ended (the )?trip .*early|ended trip early|early/i.test(k) || /ended_early/.test(st),
    checkInOk: /check-in prompt answered 'I'm OK'/i.test(k),
    reportIssueTapped: /'Report issue' tapped/i.test(k),
    locationMessage: /know which building|where you live|know where/i.test(att) || /drop-off at rider home address; driver has prior/i.test(t),
    minorSystem: /ETA slip|previous-trip overrun|Added stop honored|within auto-adjustment tolerance|no handheld-use detection|Delivery completed on time|Delivery marked completed/i.test(t)
      || /no visible damage|no stains/i.test(att),
    cleaningUsd: num(/about USD ([\d,]+)/i, att) ?? num(/USD ([\d,]+)/i, att),
    vapor: /vapou?r|smok/i.test(att),
    // data quality
    missingTrip: st === 'unknown' || /retrieval error/i.test(t) || c.trip_context?.region === 'unknown' || c.pii?.reported_party == null,
    priorFlags: flags,
    priorCategory: priorFlagCategory(flags),
    // text concepts (multilingual lexicon)
    danger: LEX.danger.test(text),
    violence: LEX.violence.test(text),
    threatHarm: LEX.threatHarm.test(text),
    threatWord: LEX.threatWord.test(text),
    ratingContext: LEX.ratingContext.test(text),
    cash: LEX.offAppCash.test(text),
    personalContact: LEX.personalContact.test(text),
    discrimination: LEX.discrimination.test(text),
    minorText: LEX.minor.test(text),
    injection: INJECTION.test(raw),
  };
  s.ratingThreatOnly = s.ratingContext && (s.threatWord || RATING_THREAT.test(text)) && !s.threatHarm;
  s.threat = s.threatHarm || (s.threatWord && !s.ratingThreatOnly);
  // An injection attempt that also mentions a threat is never read as a mere rating complaint.
  if (s.injection && s.threatWord) s.threat = true;
  // A report filed mid-trip while the vehicle is stopped roadside is an ongoing situation.
  s.liveIncident = s.inProgress && s.roadsideStop;
  s.toolkitActivity = !!k;
  return s;
}
