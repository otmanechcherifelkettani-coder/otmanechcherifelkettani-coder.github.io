// SIMULATED execution adapter. Nothing real is sent, charged, suspended or notified.
// Outcomes are deterministic per (case, action) so demos and tests are reproducible; a small
// share fails on purpose so the exception path is exercised. Emergency notifications are never
// executed by the system at all: a duty manager records what they did.

import { EXEC_ACTIONS } from './catalog.js';
import { ACTION_TARGET, systemLabel } from './integrations.js';

export const SIM_FAIL_PCT = Number(process.env?.SIM_FAIL_PCT ?? 5);

const hash = (s) => { let h = 2166136261; for (const ch of s) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return h >>> 0; };

export function simulateExecution(caseId, action, failPct = SIM_FAIL_PCT, attempt = 1) {
  if (!EXEC_ACTIONS[action]) return { ok: false, error: `Unknown action ${action}` };
  // Deterministic per attempt, so a human retry after a failure is a fresh attempt.
  const fail = hash(`${caseId}:${action}${attempt > 1 ? ':' + attempt : ''}`) % 100 < failPct;
  return fail ? { ok: false, error: `Simulated downstream failure: ${systemLabel(ACTION_TARGET[action])} timed out` } : { ok: true, receipt: `SIM-${hash(caseId + action).toString(36).toUpperCase()}` };
}
