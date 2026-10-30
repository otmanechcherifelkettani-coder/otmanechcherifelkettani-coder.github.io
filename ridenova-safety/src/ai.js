// AI provider interface. Every provider implements the same four methods and returns the
// same shapes, so the vendor/model can be swapped without touching the UI or guardrails.
//
//   triage(case)        -> { mode, provider, model, category, tier, action, confidence, rationale, summary, policy_refs, flags, translation? }
//   translate(case)     -> { mode, text, source }
//   policyQA(question)  -> { mode, covered, answer, citations[] }
//   info()              -> { mode, model }
//
// Live providers only ever receive redactForAI(case) — never the raw record.

import { simulateTriage, CATEGORY_GLOSS } from './simulated.js';
import { answerPolicyLocally } from './policyqa.js';
import { redactForAI } from './pii.js';
import { extractSignals } from './signals.js';
import { ACTIONS, TIERS } from './policy.js';

export class SimulatedProvider {
  constructor(precomputed = {}) { this.precomputed = precomputed; }
  info() { return { mode: 'simulated', model: 'rules+lexicon v1 (no AI key)' }; }
  async triage(c) { return { ...simulateTriage(c), generated_at: new Date().toISOString() }; }
  async translate(c) {
    const pre = this.precomputed[c.case_id];
    if (pre) return { mode: 'precomputed', text: pre.en, source: pre.by };
    if (c.language === 'en') return { mode: 'none', text: c.report_text, source: 'Already English' };
    const p = simulateTriage(c);
    return { mode: 'simulated', text: `[Gist, not a translation] ${CATEGORY_GLOSS[p.category]}`, source: 'Demo mode has no machine translation. Run with an AI key for a real translation.' };
  }
  async policyQA(q) { return answerPolicyLocally(q); }
}

export class LiveProvider {
  constructor(endpoint = 'api/ai', model = '') { this.endpoint = endpoint; this.model = model; }
  info() { return { mode: 'live', model: this.model }; }
  async call(task, payload) {
    const r = await fetch(this.endpoint, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ task, payload }) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || `AI call failed (${r.status})`);
    return j;
  }
  async triage(c) {
    const out = await this.call('triage', redactForAI(c));
    const v = validateTriage(out.result);
    return { ...v, mode: 'live', provider: 'LiveProvider', model: out.model, generated_at: new Date().toISOString(), signals: extractSignals(c) };
  }
  async translate(c) {
    const out = await this.call('translate', redactForAI(c));
    return { mode: 'live', text: out.result.translation, source: `Claude (${out.model}) — redacted input` };
  }
  async policyQA(question) {
    const out = await this.call('policy_qa', { question });
    const r = out.result;
    // Never trust a citation the policy does not contain.
    const valid = (r.citations || []).filter((id) => /^SP-[1-9]$/.test(id));
    if (!r.covered || !valid.length) return { mode: 'live', covered: false, answer: 'Not covered. ' + (r.answer || ''), citations: [] };
    return { mode: 'live', covered: true, answer: r.answer, citations: valid };
  }
}

// Model output is untrusted until validated; invalid fields fall back to the safest value.
export function validateTriage(r = {}) {
  const tier = TIERS[r.tier] ? r.tier : 'L3';
  const action = ACTIONS.includes(r.action) ? r.action : 'ROUTE_L3_REVIEW';
  const confidence = Number.isFinite(+r.confidence) ? Math.max(0, Math.min(1, +r.confidence)) : 0.3;
  return {
    category: String(r.category || 'unclassified').slice(0, 40), tier, action, confidence,
    rationale: String(r.rationale || '').slice(0, 1200), summary: String(r.summary || '').slice(0, 600),
    translation: r.translation ? String(r.translation).slice(0, 2000) : null,
    policy_refs: (r.policy_refs || []).filter((x) => /^SP-[1-9]$/.test(x)),
    flags: (r.flags || []).filter((x) => /^[a-z_]{3,40}$/.test(x)).concat(TIERS[r.tier] && ACTIONS.includes(r.action) ? [] : ['ai_output_invalid']),
  };
}

export async function detectProvider(precomputed) {
  try {
    const r = await fetch('api/health', { cache: 'no-store' });
    if (r.ok) { const j = await r.json(); if (j.live) return new LiveProvider('api/ai', j.model); }
  } catch { /* static hosting: no server */ }
  return new SimulatedProvider(precomputed);
}
