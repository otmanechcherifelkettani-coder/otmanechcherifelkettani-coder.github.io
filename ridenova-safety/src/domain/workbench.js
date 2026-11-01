// Workbench service: owns case state. Intake, commands (validated + idempotent), simulated
// execution, persistence (append-only JSONL event log) and access logging.

import { createState, applyEvent } from './case.js';
import { assessCase, evidenceSources, structuredDanger, recommend } from './assess.js';
import { route, dangerActive } from './routing.js';
import { dueAt } from './sla.js';
import { viewLevel, canAct } from './permissions.js';
import { simulateExecution } from './execution.js';
import { USERS, QUEUES, EXEC_ACTIONS, rank, maxTier, TIERS } from './catalog.js';
import { extractSignals } from '../signals.js';
import { simulateTriage } from '../simulated.js';
import { submittedUtcMs } from '../tz.js';
import { policyById } from '../policy.js';

const SEC = 1000;
export const DANGER_ASSESSMENTS = ['ongoing', 'no_longer_present', 'incorrectly_detected'];
// No clause in the fictional policy requires a second approval; the hook exists so a real policy can.
export const requiresSecondApproval = () => false;

export class Workbench {
  constructor({ cases, log, audit, now = () => Date.now(), automationMode = 'shadow', failPct } = {}) {
    this.raw = new Map(cases.map((c) => [c.case_id, c]));
    this.log = log; this.audit = audit; this.now = now;
    this.mode = automationMode; this.failPct = failPct;
    this.states = new Map(); this.seq = 0; this.idem = new Map();
    this.boot();
  }

  // ---------- event plumbing ----------
  emit(s, type, at, actor, payload = {}, { persist = true, idem = null, summary = null } = {}) {
    const ev = { seq: ++this.seq, type, case_id: s?.case_id ?? null, at: new Date(at).toISOString(), actor, payload, summary, idem, recorded_at: new Date().toISOString() };
    if (s) applyEvent(s, ev);
    if (persist && this.log) this.log.append(ev);
    return ev;
  }

  boot() {
    const ordered = [...this.raw.values()].sort((a, b) => submittedUtcMs(a) - submittedUtcMs(b) || a.case_id.localeCompare(b.case_id));
    const firstByKey = new Map();
    for (const c of ordered) {
      const key = `${c.reporter_id}|${c.trip_id}`;
      const parent = firstByKey.get(key);
      if (!parent) firstByKey.set(key, c.case_id);
      this.intake(c, parent ? this.states.get(parent) : null);
    }
    // Replay persisted (human / automation / config) events on top of deterministic intake.
    for (const ev of this.log?.readAll() || []) {
      this.seq = Math.max(this.seq, ev.seq);
      if (ev.idem) this.idem.set(ev.idem, ev.idem_result || { ok: true, replayed: true });
      if (ev.type === 'config.automation_mode') { this.mode = ev.payload.mode; continue; }
      const s = this.states.get(ev.case_id);
      if (s) applyEvent(s, ev);
    }
  }

  intake(c, parent) {
    const s = createState(c);
    this.states.set(c.case_id, s);
    const t0 = s.received_ms;
    const sig = extractSignals(c);
    const candidates = parent ? [{ case_id: parent.case_id, basis: 'same reporter + same trip', status: 'candidate' }] : [];
    if (parent) parent.links.candidates.push({ case_id: c.case_id, basis: 'same reporter + same trip', status: 'candidate' });
    const incident = parent ? (parent.incident_id || `INC-${parent.case_id}`) : null;
    if (parent && !parent.incident_id) parent.incident_id = incident;
    this.emit(s, 'intake.received', t0, 'system:intake', {
      sources: evidenceSources(c, sig, new Date(t0).toISOString()), evidence_completeness: sig.missingTrip ? 'missing_material' : 'complete',
      understanding: { language: c.language, supported: false, translation: 'pending' }, candidates, incident_id: incident, link_due_ms: parent ? dueAt(parent) : null,
      hint: /follow|earlier|still waiting|nobody|anxious|submitted a report/i.test(c.report_text) ? 'followup' : '',
    }, { persist: false, summary: 'Ticket received; sources retrieved' });
    // 1) Structured danger checks run immediately — no waiting for AI or full retrieval.
    const structured = structuredDanger(c, sig);
    if (structured.length) {
      this.emit(s, 'danger.detected', t0, 'system:rules', { signals: structured.map((x) => ({ ...x, kind: 'structured' })) }, { persist: false, summary: structured.map((x) => x.label).join('; ') });
      this.emit(s, 'severity.raised', t0, 'system:rules', { to: 'L4', reason: 'structured danger' }, { persist: false });
      this.emit(s, 'alert.created', t0, 'system:rules', { alert_id: `${c.case_id}-A1`, reason: 'SP-7 structured danger signal' }, { persist: false, summary: 'Duty manager alerted (structured signal)' });
      this.emit(s, 'routed', t0, 'system:router', { lane: 'manager', queue: 'duty-managers', reason: 'danger_signal', mode: this.mode }, { persist: false, summary: 'Routed to duty managers before AI preparation' });
    }
    // 2) AI preparation (simulated provider at intake) + deterministic floors.
    const a = assessCase(c, simulateTriage(c));
    this.emit(s, 'ai.assessed', t0 + 30 * SEC, 'ai:simulated', { assessment: a }, { persist: false, summary: `AI proposed ${a.ai.severity} (${a.ai.category}, conf ${a.ai.confidence})` });
    this.afterAssessment(s, a, t0 + 30 * SEC, { persist: false, parent });
  }

  // Shared by intake and later re-assessment.
  afterAssessment(s, a, at, { persist = true, parent = null } = {}) {
    const newDanger = a.structured_danger.concat(a.other_danger);
    if ((a.structured_danger.length || a.other_danger.length) && !dangerActive(s)) {
      const fresh = s.danger.status !== 'none';
      this.emit(s, 'danger.detected', at, 'system:rules', { signals: newDanger.map((x) => ({ ...x, kind: x.source === 'ai' ? 'ai' : x.source === 'ticket' ? 'text' : 'structured' })) }, { persist, summary: fresh ? 'NEW danger after reassessment — fresh escalation' : 'Danger detected' });
      this.emit(s, 'alert.created', at, 'system:rules', { alert_id: `${s.case_id}-A${s.danger.alerts.length + 1}`, reason: fresh ? 'New danger signal after reassessment' : 'SP-7 danger signal' }, { persist, summary: 'Duty manager alerted' });
      if (s.severity.current !== 'L4') this.emit(s, 'severity.raised', at, 'system:rules', { to: 'L4', reason: 'danger' }, { persist });
    }
    // Candidate link: protective — inherit the highest relevant risk (never merge or close).
    if (parent && rank(parent.severity.current) > rank(s.severity.current) && !s.severity.reviewed) {
      this.emit(s, 'severity.raised', at, 'system:rules', { to: parent.severity.current, reason: `candidate link to ${parent.case_id}` }, { persist, summary: `Raised to ${parent.severity.current}: candidate link to ${parent.case_id}` });
    }
    this.reroute(s, at, { persist });
  }

  reroute(s, at, { persist = true, reason = null, clearOwner = false } = {}) {
    if (s.workflow === 'resolved') return;
    const r = route(s, this.mode);
    const rec = recommend({ ...s, lane: r.lane, queue: r.queue });
    if (s.lane === r.lane && s.queue === r.queue && !reason) { s.recommendation = rec; return; }
    this.emit(s, 'routed', at, 'system:router', { lane: r.lane, queue: r.queue, reason: reason || r.reason, eligibility: r.eligibility, mode: this.mode, recommendation: rec, clear_owner: clearOwner || s.lane !== r.lane },
      { persist, summary: `Routed to ${QUEUES[r.queue].label}${r.eligibility?.eligible && r.lane !== 'automation' ? ' (automation-eligible, shadow mode)' : ''}` });
    if (r.lane === 'automation') this.runAutomation(s, at + 30 * SEC, { persist });
  }

  // Upstream automation: eligible -> queued -> running -> completed | failed -> sent_to_review.
  runAutomation(s, at, { persist = true } = {}) {
    const action = s.recommendation?.exec_actions?.[0] || 'send_feedback_note';
    const key = `${s.case_id}:auto:${action}`;
    if (s.executions.some((x) => x.key === key)) return; // idempotent
    const id = `${s.case_id}-X${s.executions.length + 1}`;
    this.emit(s, 'automation.state', at, 'system:automation', { state: 'queued' }, { persist });
    this.emit(s, 'execution.queued', at, 'system:automation', { exec_id: id, action, key }, { persist });
    this.emit(s, 'automation.state', at + SEC, 'system:automation', { state: 'running' }, { persist });
    this.emit(s, 'execution.running', at + SEC, 'system:automation', { exec_id: id }, { persist });
    const res = simulateExecution(s.case_id, action, this.failPct);
    if (res.ok) {
      this.emit(s, 'execution.completed', at + 2 * SEC, 'system:automation', { exec_id: id, receipt: res.receipt, reporter_facing: EXEC_ACTIONS[action].reporter_facing }, { persist, summary: `${EXEC_ACTIONS[action].label} — completed (simulated)` });
      this.emit(s, 'automation.state', at + 2 * SEC, 'system:automation', { state: 'completed' }, { persist });
      this.emit(s, 'case.resolved', at + 2 * SEC, 'system:automation', { outcome: 'auto_resolved_SP1', reason: 'Eligible SP-1 automation completed (simulated adapter)' }, { persist });
    } else {
      this.emit(s, 'execution.failed', at + 2 * SEC, 'system:automation', { exec_id: id, error: res.error }, { persist, summary: `Automation failed: ${res.error}` });
      this.emit(s, 'automation.state', at + 2 * SEC, 'system:automation', { state: 'failed' }, { persist });
      this.emit(s, 'automation.state', at + 2 * SEC, 'system:automation', { state: 'sent_to_review' }, { persist, summary: 'Exception sent to human review' });
      this.reroute(s, at + 3 * SEC, { persist, reason: 'automation_failure' });
    }
  }

  setAutomationMode(user, mode, idem) {
    if (user?.role !== 'duty_manager') return { ok: false, code: 403, error: 'Only a duty manager can change the automation mode.' };
    if (!['shadow', 'enabled'].includes(mode)) return { ok: false, code: 400, error: 'mode must be shadow or enabled' };
    if (idem && this.idem.has(idem)) return { ...this.idem.get(idem), replayed: true };
    this.mode = mode;
    this.emit(null, 'config.automation_mode', this.now(), user.id, { mode }, { idem });
    this.auditLog(user, 'automation_mode', null, { mode });
    let moved = 0;
    if (mode === 'enabled') {
      for (const s of this.states.values()) {
        if (s.automation.state === 'shadow_eligible' && !s.owner && !s.decisions.length && s.workflow !== 'resolved') { this.reroute(s, this.now()); moved++; }
      }
    }
    const res = { ok: true, mode, moved_to_automation: moved };
    if (idem) this.idem.set(idem, res);
    return res;
  }

  // ---------- commands ----------
  command(user, caseId, type, p = {}, idem = null) {
    if (idem && this.idem.has(idem)) return { ...this.idem.get(idem), replayed: true };
    const s = this.states.get(caseId);
    if (!s) return { ok: false, code: 404, error: 'Case not found.' };
    const perm = canAct(user, s, type === 'reopen' ? 'reopen' : type);
    if (!perm.ok) { this.auditLog(user, 'denied', caseId, { type }); return perm; }
    const at = this.now();
    const fail = (error, code = 422) => ({ ok: false, code, error });
    const firstPersisted = this.seq + 1;
    const E = (t, payload, opts = {}) => this.emit(s, t, at, user.id, payload, { ...opts, idem: this.seq + 1 === firstPersisted ? idem : null });
    const exec = (action, decisionIdx) => {
      const key = `${s.case_id}:${action}:${decisionIdx}`;
      if (s.executions.some((x) => x.key === key && x.status !== 'failed')) return;
      const id = `${s.case_id}-X${s.executions.length + 1}`;
      E('execution.queued', { exec_id: id, action, key });
      E('execution.running', { exec_id: id });
      const r = simulateExecution(s.case_id, action, this.failPct);
      if (r.ok) E('execution.completed', { exec_id: id, receipt: r.receipt, reporter_facing: EXEC_ACTIONS[action].reporter_facing }, { summary: `${EXEC_ACTIONS[action].label} — completed (simulated)` });
      else E('execution.failed', { exec_id: id, error: r.error }, { summary: `${EXEC_ACTIONS[action].label} — FAILED: ${r.error}` });
      return r.ok;
    };
    const needReason = (min = 8) => (p.reason || '').trim().length >= min;

    switch (type) {
      case 'take':
        if (s.owner === user.id) return fail('You already own this case.', 409);
        E('case.assigned', { owner: user.id, accept_handoff: true }, { summary: `Taken by ${user.name}` });
        break;
      case 'approve':
      case 'choose_action': {
        const action = type === 'approve' ? recommend(s).exec_actions[0] : p.action;
        if (!EXEC_ACTIONS[action]) return fail('Choose a valid action.');
        if (type === 'choose_action' && !needReason()) return fail('A reason is required when choosing a different action.');
        if (!s.owner) E('case.assigned', { owner: user.id, accept_handoff: true });
        E('decision.recorded', { decision: type === 'approve' ? 'approve_recommendation' : 'chose_alternative_action', action, recommended: recommend(s).exec_actions[0], reason: (p.reason || '').trim() || null }, { summary: `Decision: ${EXEC_ACTIONS[action].label}` });
        const ok = exec(action, s.decisions.length);
        if (ok && EXEC_ACTIONS[action].resolves) E('case.resolved', { outcome: action, reason: (p.reason || '').trim() || 'Approved recommendation executed' }, { summary: 'Resolved after confirmed execution' });
        if (rank(s.severity.current) >= 1 && !s.severity.reviewed) E('severity.reviewed', { tier: s.severity.current });
        break;
      }
      case 'request_info':
        if (!s.owner) E('case.assigned', { owner: user.id, accept_handoff: true });
        E('decision.recorded', { decision: 'request_info', reason: (p.reason || '').trim() || null }, { summary: 'Requested more information' });
        exec('request_more_info', s.decisions.length);
        break;
      case 'escalate': {
        if (!needReason()) return fail('A reason is required to escalate.');
        if (user.role === 'duty_manager') { // manager -> another manager / investigations
          const to = USERS[p.to_user];
          if (!to || to.role !== 'duty_manager' || to.id === user.id) return fail('Choose another duty manager.');
          E('handoff.requested', { to_queue: 'duty-managers', kind: 'manager_reassign', reason: p.reason.trim() });
          E('case.assigned', { owner: to.id }, { summary: `Reassigned to ${to.name}` });
          break;
        }
        if (p.to === 'manager') {
          E('decision.recorded', { decision: 'escalate_urgent', reason: p.reason.trim() }, { summary: 'Agent raised an urgent concern' });
          E('alert.created', { alert_id: `${s.case_id}-A${s.danger.alerts.length + 1}`, reason: `Agent urgent concern: ${p.reason.trim()}` });
          E('severity.raised', { to: 'L4', reason: 'agent urgent concern' });
          E('handoff.requested', { to_queue: 'duty-managers', kind: 'urgent_concern', reason: p.reason.trim() });
          this.emit(s, 'routed', at, 'system:router', { lane: 'manager', queue: 'duty-managers', reason: 'agent_urgent_concern', mode: this.mode, recommendation: recommend({ ...s, severity: { ...s.severity, current: 'L4' } }), clear_owner: true });
        } else {
          E('decision.recorded', { decision: 'escalate_specialist', reason: p.reason.trim() }, { summary: 'Escalated to specialist review' });
          if (rank(s.severity.current) < 3) E('severity.raised', { to: 'L3', reason: 'agent escalation' });
          E('handoff.requested', { to_queue: 'specialist', kind: 'specialist', reason: p.reason.trim() });
          this.reroute(s, at, { reason: 'agent_escalation', clearOwner: true });
        }
        break;
      }
      case 'link':
        if (!s.links.candidates.some((l) => l.case_id === p.case_id)) return fail('Not a candidate link.');
        if (!['confirmed', 'rejected'].includes(p.status)) return fail('status must be confirmed or rejected');
        E('link.decided', { case_id: p.case_id, status: p.status }, { summary: `Link to ${p.case_id} ${p.status}` });
        break;
      case 'resolve': {
        if (!needReason(12)) return fail('A reason (12+ characters) is required to resolve.');
        if (user.role === 'duty_manager') {
          if (!s.clocks.alert_acknowledged_at) return fail('Acknowledge the alert first.');
          const contact = [...s.steps].reverse().find((x) => x.step === 'contact_reporter');
          if (!contact) return fail('Record the reporter-contact step first.');
          if (contact.value === 'no_answer') return fail('Reporter not reached — keep trying before resolving.');
          if (!['no_longer_present', 'incorrectly_detected', 'handed_to_authorities'].includes(p.danger_status)) return fail('State whether danger is no longer present, was incorrectly detected, or was handed to authorities.');
        } else if (!s.decisions.length) return fail('Record a decision before resolving.');
        if (s.executions.some((x) => ['queued', 'running'].includes(x.status))) return fail('An action is still executing.');
        E('case.resolved', { outcome: p.outcome || 'resolved', reason: p.reason.trim(), danger_status: p.danger_status || null }, { summary: 'Resolved' });
        break;
      }
      case 'acknowledge': {
        const open = s.danger.alerts.filter((a) => !a.acknowledged_at);
        if (!open.length) return fail('No open alert.', 409);
        for (const a of open) E('alert.acknowledged', { alert_id: a.id }, { summary: `${user.name} acknowledged and owns the case` });
        if (s.handoff.status === 'pending') E('case.assigned', { owner: user.id, accept_handoff: true });
        break;
      }
      case 'step': {
        const allowed = { contact_reporter: ['reached', 'no_answer', 'no_channel'], emergency_services: ['contacted', 'not_needed', 'declined_by_reporter'], protect: ['restrict_rematch', 'suspend_reported_party', 'none_needed'] };
        if (!allowed[p.step]?.includes(p.value)) return fail('Invalid step or value.');
        if (!s.clocks.alert_acknowledged_at && s.danger.alerts.length) return fail('Acknowledge the alert first.');
        E('response.step', { step: p.step, value: p.value }, { summary: `${p.step.replace('_', ' ')}: ${p.value.replace(/_/g, ' ')}${p.step === 'emergency_services' ? ' (recorded by manager; no notification sent by this system)' : ''}` });
        if (p.step === 'protect' && p.value !== 'none_needed') exec(p.value, s.steps.length);
        break;
      }
      case 'reassess': return this.reassess(user, s, p, at, idem);
      case 'reopen': {
        if (!needReason()) return fail('A reason is required to reopen.');
        E('case.reopened', { reason: p.reason.trim() }, { summary: `Reopened: ${p.reason.trim()}` });
        if (s.automation.state === 'completed') this.emit(s, 'automation.state', at, 'system:automation', { state: 'reopened' });
        this.reroute(s, at, { reason: 'reopened', clearOwner: true });
        break;
      }
      default: return fail('Unknown command.', 400);
    }
    this.auditLog(user, `cmd:${type}`, caseId, {});
    const res = { ok: true };
    if (idem) this.idem.set(idem, res);
    return res;
  }

  // Controlled human reassessment (up or down). Automation can never do this.
  reassess(user, s, p, at, idem) {
    const fail = (error) => ({ ok: false, code: 422, error });
    if (user.role !== 'duty_manager') return { ok: false, code: 403, error: 'Only a duty manager can reassess a manager-lane case.' };
    if (s.danger.alerts.some((a) => !a.acknowledged_at)) return fail('Acknowledge the alert and take ownership first.');
    if (s.owner !== user.id) return fail('Only the accountable owner can reassess. Reassign first if needed.');
    if (!TIERS.includes(p.to) || p.to === s.severity.current) return fail('Choose a severity different from the current one.');
    if (!DANGER_ASSESSMENTS.includes(p.danger_assessment)) return fail('Assess whether danger is ongoing, no longer present, or incorrectly detected.');
    if (p.danger_assessment === 'ongoing' && p.to !== 'L4') return fail('Danger is assessed as ongoing: the case must stay L4 with a duty manager.');
    const refs = (p.evidence_refs || []).filter((r) => s.sources.some((x) => x.id === r));
    if (!refs.length) return fail('Cite at least one evidence source.');
    if (!policyById[p.policy_ref]) return fail('Cite the applicable policy clause (SP-1..SP-9).');
    if ((p.reason || '').trim().length < 20) return fail('Give a meaningful reason (20+ characters).');
    const dest = p.to === 'L4' ? 'duty-managers' : p.destination_queue;
    if (!QUEUES[dest] || dest === 'automation') return fail('Choose a human destination queue (never automation).');
    if (p.to === 'L3' && (!QUEUES[dest].capability || QUEUES[dest].capability === 'general')) return fail('L3 must go to a specialist queue.');
    if (rank(p.to) <= 2 && dest !== 'general-review') return fail('L1/L2 go to general review.');
    if (requiresSecondApproval(s, p)) return fail('Second approval required by policy.');
    const from = s.severity.current;
    const ev = this.emit(s, 'reassessment.recorded', at, user.id, { from, to: p.to, danger_assessment: p.danger_assessment, evidence_refs: refs, policy_ref: p.policy_ref, reason: p.reason.trim(), destination_queue: dest,
      original_ai_severity: s.ai?.severity, max_held: s.severity.max_held }, { idem, summary: `Reassessed ${from} → ${p.to} (danger: ${p.danger_assessment.replace(/_/g, ' ')})` });
    if (p.to !== 'L4') {
      this.emit(s, 'handoff.requested', at, user.id, { to_queue: dest, kind: 'reassessment_handoff', reason: p.reason.trim() });
      this.emit(s, 'routed', at, 'system:router', { lane: 'agent', queue: dest, reason: 'manager_reassessment', mode: this.mode, recommendation: recommend({ ...s, lane: 'agent', queue: dest }), clear_owner: true },
        { summary: `Handed off to ${QUEUES[dest].label} — awaiting acceptance` });
    }
    this.auditLog(user, 'cmd:reassess', s.case_id, { from, to: p.to });
    const res = { ok: true, event: ev.seq };
    if (idem) this.idem.set(idem, res);
    return res;
  }

  // New external signal for an existing case (e.g. a fresh SOS). Never suppressed by an earlier downgrade.
  ingestSignal(caseId, signal) {
    const s = this.states.get(caseId);
    if (!s) return { ok: false, code: 404, error: 'Case not found.' };
    const at = this.now();
    const sig = { signal: signal.signal || 'live_sos', label: signal.label || 'New live SOS pressed', source: 'toolkit', kind: 'structured' };
    const wasDowngraded = !dangerActive(s) && s.danger.status !== 'none';
    this.emit(s, 'danger.detected', at, 'system:rules', { signals: [sig] }, { summary: wasDowngraded ? 'NEW danger after downgrade — fresh escalation' : 'New danger signal' });
    this.emit(s, 'alert.created', at, 'system:rules', { alert_id: `${s.case_id}-A${s.danger.alerts.length + 1}`, reason: wasDowngraded ? 'New danger after reassessment' : 'New danger signal' });
    if (s.severity.current !== 'L4') this.emit(s, 'severity.raised', at, 'system:rules', { to: 'L4', reason: 'new danger signal' });
    if (s.workflow === 'resolved') this.emit(s, 'case.reopened', at, 'system:rules', { reason: 'New danger signal' });
    this.reroute(s, at, { reason: 'new_danger_signal', clearOwner: true });
    return { ok: true };
  }

  // Re-run AI preparation (live or simulated). Never overwrites a human decision.
  applyAssessment(caseId, proposal, actor = 'ai:live') {
    const s = this.states.get(caseId); const c = this.raw.get(caseId);
    const a = assessCase(c, proposal);
    const at = this.now();
    this.emit(s, 'ai.assessed', at, actor, { assessment: a }, { summary: `AI re-assessed: ${a.ai.severity} (${a.ai.mode})` });
    if (s.workflow !== 'resolved') this.afterAssessment(s, a, at);
    return { ok: true };
  }
  aiFailed(caseId, error) {
    const s = this.states.get(caseId);
    this.emit(s, 'ai.failed', this.now(), 'ai:live', { error }, { summary: `AI unavailable: ${error}. Human review continues with the existing assessment.` });
  }

  auditLog(user, event, caseId, detail) {
    this.audit?.append({ at: new Date(this.now()).toISOString(), recorded_at: new Date().toISOString(), user: user?.id || null, role: user?.role || null, event, case_id: caseId, detail });
  }

  visible(user) { return [...this.states.values()].filter((s) => viewLevel(user, s) === 'full'); }
}
