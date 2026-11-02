// Removes instructions aimed at the triage system from text BEFORE it is sent to a model.
// Ported idea: the model never sees the injection, while the deterministic rules keep scanning
// the ORIGINAL text, so sanitising can never hide a threat from the floors.
//
// Strategy (most precise first):
//  1. Delimited directives: [ ... ], << ... >>, <admin> ... </admin>, ### ... ###, *** ... ***, 【 ... 】,
//     ( ... ) when the content matches an injection pattern.
//  2. Undelimited clauses: the clause containing an injection pattern, up to the next sentence end,
//     but only if that clause carries no harm/danger/violence language (otherwise it is kept).

import { INJECTION, LEX } from './lexicon.js';

const DELIMITED = [/\[[^\]]{4,400}\]/g, /<<[^>]{4,400}>>/g, /<admin>[\s\S]{0,400}?<\/admin>/gi, /###[^#]{4,400}###/g, /\*\*\*[^*]{4,400}\*\*\*/g, /【[^】]{4,400}】/g, /\([^)]{4,400}\)/g, /（[^）]{4,400}）/g];
const SENTENCE = /[^.!?。！？।\n]*[.!?。！？।\n]?/g;
const carriesRisk = (t) => LEX.threatHarm.test(t) || LEX.threatWord.test(t) || LEX.danger.test(t) || LEX.violence.test(t);

export function stripInjection(text) {
  if (!text || !INJECTION.test(text)) return { text, removed: [] };
  const removed = [];
  let out = text;
  for (const rx of DELIMITED) {
    out = out.replace(rx, (m) => (INJECTION.test(m) && !carriesRisk(m.replace(INJECTION, '')) ? (removed.push(m), ' ⟪instruction removed⟫ ') : m));
  }
  if (INJECTION.test(out)) {
    out = (out.match(SENTENCE) || []).map((sent) => {
      if (!INJECTION.test(sent)) return sent;
      // split on separators often used to chain the real report after the directive
      const parts = sent.split(/(\s--\s|\s—\s|;|:\s)/);
      const out2 = [];
      for (let i = 0; i < parts.length; i++) {
        const p = parts[i];
        if (!(INJECTION.test(p) && !carriesRisk(p))) { out2.push(p); continue; }
        removed.push(p.trim()); out2.push(' ⟪instruction removed⟫ ');
        // "Note to bot: <directive>" -> the clause after a removed label is the directive itself
        if (/^:\s$/.test(parts[i + 1] || '') && parts[i + 2] != null && !carriesRisk(parts[i + 2])) { removed.push(parts[i + 2].trim()); i += 2; }
      }
      return out2.join('');
    }).join('');
  }
  // a dangling label left in front of a removed directive, e.g. "System:" / "Järjestelmä:"
  out = out.replace(/([^\s.!?。]{2,20}:)\s*(?=⟪instruction removed⟫)/gu, (m, w) => (INJECTION.test(w) ? (removed.push(w), '') : m));
  return { text: out.replace(/\s{2,}/g, ' ').trim(), removed };
}
