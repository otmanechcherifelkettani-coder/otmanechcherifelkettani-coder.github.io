// Server-side access rules. The UI may hide buttons, but THIS decides.
import { requiredCapability } from './routing.js';

export const AGENT_ACTIONS = new Set(['take', 'approve', 'choose_action', 'request_info', 'escalate', 'link', 'resolve']);
export const MANAGER_ACTIONS = new Set(['acknowledge', 'step', 'reassign', 'reassess', 'resolve', 'escalate']);

// 'full' | 'handoff_status' | null
export function viewLevel(user, s) {
  if (!user) return null;
  if (user.role === 'duty_manager') return user.regions.includes(s.region) ? 'full' : null;
  if (s.owner === user.id) return 'full';
  if (s.lane === 'agent' && user.regions.includes(s.region) && user.capabilities.includes(requiredCapability(s))) return 'full';
  if (s.handoff?.from === user.id || s.decisions.some((d) => d.by === user.id)) return 'handoff_status';
  return null;
}

export function canAct(user, s, type) {
  if (viewLevel(user, s) !== 'full') return { ok: false, code: 403, error: 'Not authorised for this case.' };
  if (user.role === 'duty_manager') {
    if (type === 'reopen') return s.workflow === 'resolved' ? { ok: true } : { ok: false, code: 409, error: 'Only resolved cases can be reopened.' };
    if (s.lane !== 'manager') return { ok: false, code: 409, error: 'This case is not in the duty-manager lane.' };
    return MANAGER_ACTIONS.has(type) ? { ok: true } : { ok: false, code: 403, error: `Duty managers cannot “${type}” here.` };
  }
  if (s.lane !== 'agent') return { ok: false, code: 403, error: 'Agents cannot act on manager-lane or automation-lane cases.' };
  if (!AGENT_ACTIONS.has(type)) return { ok: false, code: 403, error: `Agents cannot “${type}”.` };
  if (s.workflow === 'resolved') return { ok: false, code: 409, error: 'Case is resolved.' };
  if (type !== 'take' && s.owner && s.owner !== user.id) return { ok: false, code: 409, error: 'Case is owned by someone else.' };
  return { ok: true };
}
