// Personal-information protection: role-based masking for display, and redaction before any
// text leaves the trust boundary (external AI provider, exports).
//
// Limits (stated, not hidden): free-text redaction is pattern + known-value based. It catches
// phone numbers, emails, plates and the names/addresses held in the PII block, but not a
// stranger's name that appears only in free text. Production would add an NER model running
// inside the boundary.

import { stripInjection } from './sanitize.js';

export const ROLES = {
  agent:      { label: 'Safety agent (L1/L2)', reveal: false, maxTier: 'L2', note: 'Masked PII. Cannot reveal.' },
  specialist: { label: 'Safety specialist (L3/L4)', reveal: true, maxTier: 'L4', note: 'Masked by default. Reveal per field with a logged reason.' },
  duty:       { label: 'Duty manager', reveal: true, maxTier: 'L4', note: 'Masked by default. Reveal per field with a logged reason. Receives L4 alerts.' },
  auditor:    { label: 'Auditor / QA', reveal: false, maxTier: 'L4', note: 'No PII. Decisions and audit trail only.' },
};

const EMAIL = /[\w.+-]+@[\w-]+(\.[\w-]+)+/g;
const PHONE = /\+?\d[\d\s().-]{6,}\d/g;
const ADDRESS = /\b\d{1,4}\s+[A-Z][\w'’.-]*(\s+[A-Z][\w'’.-]*){0,3}\s+(Street|St|Ave|Avenue|Road|Rd|Lane|Blvd|Boulevard|Way|Drive|Calle|Rua|Rue|Strasse|Straße|Via)\b[^,]*/g;

export function maskName(n) {
  if (!n) return '—';
  return n.split(/\s+/).map((p) => p[0] + '•'.repeat(Math.max(2, Math.min(5, p.length - 1)))).join(' ');
}
export const maskPhone = (p) => (p ? p.replace(/\d(?=[\d\s]{3})/g, '•') : '—');
export const maskEmail = (e) => (e ? e.replace(/^(.)[^@]*(@.*)$/, '$1•••$2') : '—');
export const maskPlate = (p) => (p ? p.slice(0, 2) + '•'.repeat(Math.max(1, p.length - 2)) : '—');
export const maskAddress = (a) => (a ? '•••, ' + (a.split(',').slice(-1)[0] || '').replace('(fictional)', '').trim() + ' (city only)' : '—');

function knownValues(c) {
  const out = [];
  const p = c.pii || {};
  const add = (v, tag) => { if (v && typeof v === 'string' && v.length > 2) out.push([v, tag]); };
  for (const [who, tag] of [['reporter', 'REPORTER'], ['reported_party', 'REPORTED_PARTY']]) {
    const x = p[who];
    if (!x) continue;
    add(x.name, `${tag}_NAME`);
    for (const part of (x.name || '').split(/\s+/)) if (part.length > 2) add(part, `${tag}_NAME`);
    add(x.phone, 'PHONE'); add(x.email, 'EMAIL'); add(x.vehicle_plate, 'PLATE');
  }
  add(p.pickup_address, 'ADDRESS'); add(p.dropoff_address, 'ADDRESS');
  return out.sort((a, b) => b[0].length - a[0].length);
}

const escapeRx = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// Redact one free-text string using the case's known PII values plus generic patterns.
export function redactText(text, c) {
  if (!text) return text;
  let s = text;
  let n = 0;
  for (const [v, tag] of knownValues(c)) {
    const r = new RegExp(`(?<![\\p{L}\\p{N}])${escapeRx(v)}(?![\\p{L}\\p{N}])`, 'giu');
    s = s.replace(r, () => { n++; return `[${tag}]`; });
  }
  s = s.replace(EMAIL, () => { n++; return '[EMAIL]'; });
  s = s.replace(PHONE, (m) => (/^\d{4}-\d{2}-\d{2}/.test(m) || /^\d{1,2}:\d{2}/.test(m) || m.replace(/\D/g, '').length < 7 ? m : (n++, '[PHONE]')));
  s = s.replace(ADDRESS, () => { n++; return '[ADDRESS]'; });
  return s;
}

// Stable pseudonym so the AI can correlate without seeing the real ID.
export function pseudonym(id) {
  let h = 2166136261;
  for (const ch of String(id)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  return 'P-' + (h >>> 0).toString(36).toUpperCase();
}

// The ONLY object that may be sent to an external AI provider. No PII block, pseudonymous IDs,
// free text redacted. Unit-tested in tests/pii.test.mjs.
// Text sent to a model: PII redacted first, then instructions aimed at the triage system removed
// (src/sanitize.js). The deterministic rules always scan the original text.
export function redactForAI(c) {
  const clean = (t) => stripInjection(redactText(t, c));
  const report = clean(c.report_text);
  const atts = (c.attachments || []).map(clean);
  return {
    case_ref: c.case_id,
    reporter_ref: pseudonym(c.reporter_id),
    trip_ref: pseudonym(c.trip_id),
    region: c.region_group, country: c.country, city: c.city,
    channel: c.channel, language: c.language,
    reporter_role: c.reporter_role, reported_party_role: c.reported_party_role,
    report_text: report.text,
    injection_removed: report.removed.length + atts.reduce((n, a) => n + a.removed.length, 0),
    trip_context: { product: c.trip_context?.product, local_time: c.trip_context?.local_time, trip_status: c.trip_context?.trip_status },
    history: c.history,
    attachments: atts.map((a) => a.text),
    safety_toolkit_log: c.safety_toolkit_log ? redactText(c.safety_toolkit_log, c) : null,
    telematics_summary: redactText(c.telematics_summary, c),
  };
}

// Defence in depth: the server refuses payloads that still look like they contain PII.
export function containsObviousPII(obj) {
  const s = JSON.stringify(obj);
  return /[\w.+-]+@[\w-]+\.(test|com|org|net)/.test(s) || /\+\d{1,3}[\s\d]{8,}/.test(s);
}

export function displayParty(party, role, revealed = {}) {
  if (!party) return null;
  const show = (k, masker) => (revealed[k] ? party[k] : masker(party[k]));
  if (role === 'auditor') return { name: 'hidden', phone: 'hidden', email: 'hidden', vehicle_plate: 'hidden' };
  return {
    name: show('name', maskName), phone: show('phone', maskPhone), email: show('email', maskEmail),
    vehicle_plate: party.vehicle_plate === undefined ? undefined : show('vehicle_plate', maskPlate),
  };
}
