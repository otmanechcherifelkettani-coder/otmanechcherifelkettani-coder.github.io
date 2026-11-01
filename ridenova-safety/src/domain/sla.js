// First-response SLA. Rules (documented in docs/DECISIONS.md):
// - Clock starts at receipt and is never reset (not by reassignment, linking or downgrade).
// - Deadline = receipt + SLA of the HIGHEST tier the case has held. Escalation tightens it;
//   a downgrade never loosens it. A late escalation can therefore be breached immediately.
// - Linked follow-ups use the earliest applicable deadline in the link group.
// - Awaiting information does NOT pause the clock (the policy permits no pause).
// - The clock stops at the first SUBSTANTIVE response (a reporter-facing action that executed).
//   Acknowledging an alert is not a first response.

import { SLA_MIN } from './catalog.js';

export const APPROACHING_SHARE = 0.25;

export function dueAt(state) {
  const own = state.received_ms + SLA_MIN[state.severity.max_held] * 60e3;
  return Math.min(own, state.link_due_ms ?? Infinity);
}

// status: met | missed | breached (open) | approaching | on_track
export function slaStatus(state, now) {
  const due = dueAt(state);
  const fr = state.clocks.first_response_at ? Date.parse(state.clocks.first_response_at) : null;
  if (fr != null) return { due_at: new Date(due).toISOString(), status: fr <= due ? 'met' : 'missed' };
  if (state.workflow === 'resolved') return { due_at: new Date(due).toISOString(), status: 'closed_without_response' };
  const total = SLA_MIN[state.severity.max_held] * 60e3;
  if (now > due) return { due_at: new Date(due).toISOString(), status: 'breached', overdue_min: Math.round((now - due) / 60e3) };
  return { due_at: new Date(due).toISOString(), status: due - now <= total * APPROACHING_SHARE ? 'approaching' : 'on_track', remaining_min: Math.round((due - now) / 60e3) };
}
