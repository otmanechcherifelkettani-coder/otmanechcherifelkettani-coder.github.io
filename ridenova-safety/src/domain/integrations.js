// MOCK connections to the company systems the workbench sits between. Nothing here talks to a
// real system: every record is derived deterministically from the case's own events so that the
// demo shows WHERE each step would land (ticket, page, message, enforcement, ledger) and what the
// round trip looks like. In production each entry is an adapter behind the same interface.

import { EXEC_ACTIONS } from './catalog.js';

export const SYSTEMS = {
  ticketing:   { label: 'Support ticketing', role: 'System of record for the case. The workbench reads the ticket and writes status, owner and outcome back.', direction: 'read + write' },
  trip:        { label: 'Trip system', role: 'Trip record, route and status.', direction: 'read' },
  telematics:  { label: 'Telematics', role: 'GPS, stops, speed and impact signals.', direction: 'read' },
  toolkit:     { label: 'Safety toolkit', role: 'In-app SOS and emergency-button events (push).', direction: 'read (push)' },
  history:     { label: 'Case history', role: 'Prior reports and flags for both parties.', direction: 'read' },
  evidence:    { label: 'Evidence store', role: 'Attachments, in-app messages, photos.', direction: 'read' },
  identity:    { label: 'Identity vault', role: 'Names, phone numbers, plates. Masked; every reveal is logged.', direction: 'read (logged)' },
  paging:      { label: 'On-call paging', role: 'Pages the duty-manager rotation for each danger alert; acknowledgement syncs back.', direction: 'write + read' },
  messaging:   { label: 'Messaging service', role: 'Reporter- and party-facing messages.', direction: 'write' },
  payments:    { label: 'Payments ledger', role: 'Goodwill credits and fees.', direction: 'write' },
  enforcement: { label: 'Account enforcement', role: 'Re-match blocks and suspensions.', direction: 'write' },
};

export const ACTION_TARGET = {
  send_feedback_note: 'messaging', request_more_info: 'messaging', safety_followup: 'messaging', warn_reported_party: 'messaging',
  issue_goodwill_credit: 'payments', charge_cleaning_fee: 'payments',
  restrict_rematch: 'enforcement', suspend_reported_party: 'enforcement',
};
for (const k of Object.keys(EXEC_ACTIONS)) if (!ACTION_TARGET[k]) throw new Error(`No target system for ${k}`);

const ROTATION = { EMEA: 'Safety duty managers · EMEA', 'US&C': 'Safety duty managers · Americas', LatAm: 'Safety duty managers · Americas', APAC: 'Safety duty managers · APAC' };

export const ticketRef = (caseId) => `SAF-${String(caseId).replace(/\D/g, '').padStart(6, '0')}`;
export const systemLabel = (k) => `${SYSTEMS[k]?.label || k} (mock)`;

// Per-case records in the connected systems.
export function caseIntegrations(s) {
  const status = s.workflow === 'resolved' ? 'Solved' : s.owner ? 'Open · assigned' : 'New';
  return {
    ticket: { system: systemLabel('ticketing'), ref: ticketRef(s.case_id), status, synced_fields: ['status', 'owner', 'severity', 'outcome'], last_sync: s.history.at(-1)?.at || null },
    pages: s.danger.alerts.map((a, i) => ({ system: systemLabel('paging'), ref: `PG-${ticketRef(s.case_id).slice(4)}-${i + 1}`, rotation: ROTATION[s.region] || 'Safety duty managers',
      triggered_at: a.created_at, status: a.acknowledged_at ? 'acknowledged' : 'triggered', acknowledged_at: a.acknowledged_at || null })),
    executions: s.executions.map((x) => ({ exec_id: x.exec_id || x.id, target: systemLabel(ACTION_TARGET[x.action]) })),
  };
}

// Overview: what flowed to and from each system in this scope.
export function integrationStats(states) {
  const out = { tickets_synced: 0, pages_triggered: 0, pages_acknowledged: 0, messaging: 0, payments: 0, enforcement: 0, failed_calls: 0 };
  for (const s of states) {
    out.tickets_synced++;
    for (const a of s.danger.alerts) { out.pages_triggered++; if (a.acknowledged_at) out.pages_acknowledged++; }
    for (const x of s.executions) { if (x.status === 'completed') out[ACTION_TARGET[x.action]]++; if (x.status === 'failed') out.failed_calls++; }
  }
  return out;
}
