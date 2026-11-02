# AI-use log

## Tools and models
- **Claude Code (Anthropic)** was the main development partner: data exploration, code, tests, docs and both decks.
- **In the product:** Claude via the Anthropic SDK behind a replaceable provider interface (`server/providers.mjs`). The default model is `claude-opus-5-5`, configurable. The key stays server-side, and the model only receives `redactForAI(case)`.

## What was delegated to AI
| Area | AI did | Still requires the candidate |
|---|---|---|
| Data exploration | Clustering cases by system-field signatures; per-language samples | Confirm the scenario interpretation |
| Reference labels | **Drafted** the scenario table (silver) and the 30 case-level reference labels with rationales | **Adjudicate** them in `validation/candidate_adjudication.json`. Until then they are not independent validation. |
| Translations | English fixtures for the 23 non-English reference cases (labelled “fixture” in the UI) | Spot-check |
| Lexicon | Multilingual term drafts | Review false-positive terms |
| Code, tests, docs, decks | First drafts and iterations | Be able to explain every choice and number |

## Ideas taken from another build
A second, separately built version of this exercise (a Python prototype) was compared against this one. Four of its ideas were re-implemented here, with their own tests: the hash-chained access log, retention by tier, removing injection text from model input, and the "second key" for text-only automation. No code was copied; the designs were adapted to this event-sourced model.

## What AI got wrong (caught by evaluation or tests)
- Over-broad lexicon terms (`minor`, `kind`, `child`, `bateu`, the Arabic substring `لمس`) produced 250+ false escalations.
- `\bSOS\b` matched “no SOS”, producing 25 false L4s.
- “Reporter has 4 reports in 90 days” was treated as counter-evidence. That penalises frequent reporters; it was removed.
- In the first build, L1 meant auto-resolve by default and severity, lane and status were mixed in one record. Both were rebuilt.
- The earlier AI-use log claimed the candidate had labelled the 30 reference cases. They were AI-drafted; this log corrects that.
- The first injection stripper's placeholder text itself triggered the injection detector, and Hindi sentence endings (।) weren't recognised, which left one directive in place. Caught by the tests.
- Timing assumptions in the browser tests: assertions ran before server responses arrived.

## Not delegated / guarded
- Policy interpretation, routing precedence and reassessment rules are written as code and checked by tests, not left to prompts.
- Nothing claims live-model accuracy or historical SLA performance.
- No real customer or employee data was used anywhere.
