# AI-use log

## Tools and models

* **Claude Code (Anthropic Claude, Opus-class model)**: main development partner for exploration, code, tests, docs and the deck.
* **Inside the product:** Claude via the official Anthropic SDK (`@anthropic-ai/sdk`) behind `src/ai.js`’s provider interface. The default is `claude-opus-5-5`, configurable.

## What I delegated to AI

| Area | Delegated | Checked by me |
|---|---|---|
| Data exploration | Scripts to cluster cases by system-field signatures and print samples per cluster and language | Read the samples; decided which clusters are real scenarios |
| Scenario labels (silver) | Drafting the scenario → tier table | Every tier/action call against SP-1..SP-9; the 6 policy-gap defaults |
| Gold labels | Pulling a stratified sample | Read all 30 cases and wrote each label and rationale |
| Translations | English translations of the 23 non-English gold cases (shown as *precomputed*) | Spot-checked es, fr, pt, ar, de |
| Lexicons | First drafts of multilingual terms | Every term that caused a false positive in evaluation |
| Code | First drafts of the engine, UI, server, tests | Guardrail precedence, auto-resolve gate, role checks, redaction, test assertions |
| Deck and docs | Drafting and layout | Every number, traced to `validation/results.json` or the annex A1 formula |

## What AI got wrong

* Over-broad lexicon terms: `minor`, `kind`, `child`, `bateu`, `geschlagen`, `agarró`, `golpe`, Arabic `لمس` (a substring of “help”), `numéro`/`番号`/`電話`. Together these caused 250+ false escalations, caught by the evaluation loop.
* `\bSOS\b` matched “no SOS” in a toolkit log, which produced 25 false L4s.
* It assumed `node --test tests/` would glob the directory; on Node 22 it does not.
* An early draft let SP-9 raise *unrecognised* cases (L2 → L3), which over-escalated.
* A layout bug: an element’s `hidden` attribute was overridden by `display: grid`.

## What I chose not to delegate

* The interpretation of the policy, especially SP-9 into L4, injection → L3, and the auto-resolve allow-list.
* The decision to keep the silver signatures out of the engine, so validation is not circular.
* What to claim. Live AI is reported as not benchmarked because it was not run.

## Data handling

Only the supplied synthetic dataset was used. No real customer or employee data was pasted into any AI tool. Inside the product, the model only ever receives `redactForAI(case)`.
