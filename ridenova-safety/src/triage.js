// Triage pipeline: case -> (AI proposal) -> guardrails -> structured record.
// Pure and synchronous for the simulated path, so the full 5,000-case set triages in the
// browser on load and in Node for tests/evaluation.

import { simulateTriage } from './simulated.js';
import { extractSignals } from './signals.js';
import { applyGuardrails } from './guardrails.js';
import { TIERS, rank } from './policy.js';
import { submittedUtcMs } from './tz.js';

// Index: same reporter + same trip seen earlier (by submission time, then case id) -> parent.
export function buildDuplicateIndex(cases) {
  const seen = new Map();
  const parentOf = new Map();
  const ordered = [...cases].sort((a, b) => submittedUtcMs(a) - submittedUtcMs(b) || a.case_id.localeCompare(b.case_id));
  for (const c of ordered) {
    const key = c.reporter_id + '|' + c.trip_id;
    if (seen.has(key)) parentOf.set(c.case_id, seen.get(key));
    else seen.set(key, c.case_id);
  }
  return parentOf;
}

const QA_RATE = 0.05;
const qaSample = (id) => { let h = 7; for (const ch of id) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return (h % 1000) / 1000 < QA_RATE; };

// Merge an AI proposal with guardrails into the record shape used everywhere (UI, export, eval).
export function finalize(c, proposal, ctx = {}) {
  const s = proposal.signals || extractSignals(c);
  const g = applyGuardrails(c, proposal, s, ctx);
  const submitted = submittedUtcMs(c);
  return {
    case_id: c.case_id,
    submitted_utc: new Date(submitted).toISOString(),
    deadline_utc: new Date(submitted + TIERS[g.tier].slaMin * 60e3).toISOString(),
    deadline_ms: submitted + TIERS[g.tier].slaMin * 60e3,
    region: c.region_group, country: c.country, language: c.language,
    // AI groundwork (as proposed) — kept separate from the final routed values
    ai: {
      mode: proposal.mode, provider: proposal.provider, model: proposal.model,
      category: proposal.category, tier: proposal.tier, action: proposal.action, confidence: proposal.confidence,
      rationale: proposal.rationale, summary: proposal.summary, policy_refs: proposal.policy_refs, translation: proposal.translation || null,
      generated_at: proposal.generated_at || null,
    },
    // After guardrails
    predicted_tier: g.tier,
    predicted_action: g.action,
    confidence: g.confidence,
    flags: g.flags,
    policy_refs: [...new Set([...(proposal.policy_refs || []), ...g.changes.map((x) => x.rule).filter((r) => r.startsWith('SP-'))])].sort(),
    rationale: proposal.rationale + (g.changes.length ? ' Guardrails: ' + g.changes.map((x) => `${x.rule}: ${x.from}→${x.to} (${x.why})`).join('; ') + '.' : ''),
    guardrail_changes: g.changes,
    lane: g.lane,
    alert: g.alert,
    locked: g.locked,
    auto_resolved: g.autoResolved,
    qa_sample: g.autoResolved && qaSample(c.case_id),
    parent_case: ctx.parent?.case_id || null,
    status: g.autoResolved ? 'auto_resolved' : 'awaiting_human',
  };
}

// Triage every case with the simulated provider; parents are processed before follow-ups.
export function triageAll(cases) {
  const parentOf = buildDuplicateIndex(cases);
  const out = new Map();
  const ordered = [...cases].sort((a, b) => submittedUtcMs(a) - submittedUtcMs(b) || a.case_id.localeCompare(b.case_id));
  for (const c of ordered) {
    const pid = parentOf.get(c.case_id);
    const parent = pid ? { case_id: pid, tier: out.get(pid)?.predicted_tier } : null;
    out.set(c.case_id, finalize(c, simulateTriage(c), { parent }));
  }
  return out;
}

// Queue order: severity first, then earliest first-response deadline.
export const queueCompare = (a, b) => rank(b.predicted_tier) - rank(a.predicted_tier) || a.deadline_ms - b.deadline_ms;
