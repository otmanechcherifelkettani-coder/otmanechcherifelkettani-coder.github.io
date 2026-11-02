# Validation

Reproduce with `npm run evaluate` (writes `validation/results.json`). The figures below come from the **current operating model** (intake, floors and routing) running the **simulated provider** in shadow mode. Live Claude output was not run, so it is not benchmarked.

## What the reference sets are, and are not

| Set | Size | Who labelled | Status |
|---|---|---|---|
| Silver (scenario-level) | 5,000 | Scenario table drafted with AI assistance from system-field signatures (`validation/silver.mjs`) | AI-assisted; **not** candidate-adjudicated |
| AI-drafted reference | 30 | Drafted by Claude during development (`reference_labels_ai_drafted.json`) | **Not independent.** Earlier documents wrongly described these as candidate-labelled; that is corrected here. |
| Candidate-adjudicated | 0 of 30 | The candidate, via `candidate_adjudication.json` | **Pending**: no independent validation can be claimed yet |

## Results (measured on the prototype)

| Measure | Result |
|---|---|
| L4 cases routed to the duty-manager lane (silver) | **138 / 138** |
| L3+ recall (silver) | **519 / 523**. The 4 misses (SC-3570, SC-4268, SC-4275, SC-4278) are L2 human review, not automated. |
| Tier agreement (silver) | 91.8%, with 4 under-triaged and **404 over-triaged** |
| Automation-eligible cases whose silver label is not L1 | **0** |
| With demo automation enabled: automated cases whose silver label is not L1 | **0** (2,342 completed and 114 failed → human review; failures are simulated) |
| AI-drafted reference (30) | 29/30 tier (1 over-triaged: a Swahili music complaint sent to a human) |
| Full intake of 5,000 cases | ~0.7–1.1 s |

## Where it is weak
- **Over-triage rose from 107 to 404.** The deliberate cause: reports in languages the simulated provider does not understand (440 cases) are now provisional L2 for human review instead of L1 guesses. That costs reviewer time and is the main argument for a live, multilingual model plus per-language evaluation.
- **In-sample:** the lexicon was tuned on this file.
- **Right for the wrong reason** remains possible when an unrecognised report defaults to L2 (for example SC-1314, Spanglish).
- **No calibration:** confidence is a heuristic score.

## What tests prove
The 40 unit/API tests and 5 browser tests show that the coded rules behave as specified: routing precedence, permissions, reassessment controls, clocks, idempotency, redaction and persistence. They are not proof of complete policy coverage, model accuracy or production safety.
