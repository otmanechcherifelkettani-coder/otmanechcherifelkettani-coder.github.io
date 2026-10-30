// Offline policy Q&A (demo mode). Retrieval over the nine policy clauses with a coverage
// threshold: answers ONLY from clause text, always with a citation, otherwise "Not covered".

import { POLICY } from './policy.js';

const STOP = new Set('a an the is are was were be can could should would do does did of to in on for with and or if it this that what which who how when my our we i you he she they case cases rider driver report reports about any there policy rule rules under'.split(' '));
const SYN = { smoke: 'smoking', vape: 'vaping', crash: 'collision', accident: 'collision', racist: 'discriminatory', racism: 'discriminatory', slur: 'discriminatory',
  money: 'payment', cash: 'payment', tip: 'payment', grope: 'sexual', groped: 'sexual', touched: 'touch', hit: 'violence', punched: 'violence', fight: 'violence',
  stalk: 'stalking', stalker: 'stalking', following: 'stalking', gun: 'weapon', knife: 'weapon', speed: 'speeding', fast: 'speeding', spill: 'damage', stain: 'damage',
  earlier: 'prior', previous: 'prior', before: 'prior', again: 'repeat', threatened: 'threat', threatening: 'threat', home: 'location', address: 'location' };

const tokens = (q) => q.toLowerCase().replace(/[^\p{L}\p{N}\s-]/gu, ' ').split(/\s+/).filter((w) => w && !STOP.has(w)).map((w) => SYN[w] || w);

export const COVERAGE_THRESHOLD = 2;

export function answerPolicyLocally(question) {
  const q = tokens(question);
  if (!q.length) return { covered: false, answer: 'Not covered — ask a question about the supplied policy.', citations: [], mode: 'simulated' };
  const scored = POLICY.map((p) => {
    const kw = new Set([...p.keywords, ...tokens(p.title)]);
    const hits = q.filter((w) => kw.has(w) || [...kw].some((k) => k.length > 4 && (w.startsWith(k) || k.startsWith(w))));
    return { p, score: new Set(hits).size, hits: [...new Set(hits)] };
  }).sort((a, b) => b.score - a.score);
  const best = scored.filter((s) => s.score >= COVERAGE_THRESHOLD && s.score >= scored[0].score - 1).slice(0, 2);
  if (!best.length) {
    return { covered: false, mode: 'simulated', citations: [],
      answer: 'Not covered. The supplied policy (SP-1 to SP-9) does not address this. Escalate to a policy owner; do not improvise a rule.' };
  }
  return {
    covered: true, mode: 'simulated', citations: best.map((b) => b.p.id),
    answer: best.map((b) => `${b.p.id} (${b.p.title}): “${b.p.text}”`).join('\n\n'),
    matched_terms: best.flatMap((b) => b.hits),
  };
}
