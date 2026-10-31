# RideNova Safety Console

A centralized safety-case review tool. It puts everything a reviewer needs on **one screen**. **AI does the groundwork** (summary, translation, proposed tier and action, policy citations), **deterministic guardrails** enforce the policy, and **humans make the decisions**.

Built for the *Program Leader, Tech Transformation – Field Operations* case exercise. RideNova is fictional and all data is synthetic.

| | |
|---|---|
| **Console** | `console.html`: queue, case view, decisions, policy assistant, overview, access log |
| **Case solution** | `index.html`: problem structure, prioritisation, brief coverage |
| **Executive deck** | `deck.html`: 11 slides + 4 annex (arrow keys; *Print / PDF* to export) |
| **Docs** | [`docs/DECISIONS.md`](docs/DECISIONS.md) · [`docs/VALIDATION.md`](docs/VALIDATION.md) · [`docs/AI_LOG.md`](docs/AI_LOG.md) |

## Run it (5 commands)

Requires Node ≥ 20.

```bash
cd ridenova-safety
npm install                      # only needed for live AI (Anthropic SDK)
npm test                         # 25 tests on the critical rules
npm start                        # DEMO mode → http://localhost:8080/console.html
ANTHROPIC_API_KEY=sk-... npm start   # LIVE mode (key stays server-side)
```

Optional: `npm run evaluate` re-runs validation over all 5,000 cases and writes `validation/results.json`.
Env vars: `PORT` (8080), `AI_MODEL` (default `claude-opus-5-5`), `AI_EFFORT` (default `low`). See `.env.example`. **No secrets are in the repo.**

The console also runs on any static host (e.g. GitHub Pages) in demo mode, because the whole triage pipeline runs in the browser.

## Demo mode vs. live AI

| | Demo (no key) | Live (`ANTHROPIC_API_KEY` set) |
|---|---|---|
| Triage of all 5,000 cases | ✅ `SimulatedProvider`: rules + multilingual lexicon, **labelled SIMULATED** | Initial queue is simulated; **“Run live AI”** per case calls Claude |
| Summary | Template by detected category | Model-written, from redacted input |
| Translation | Precomputed for the 23 non-English gold cases (labelled *precomputed*); elsewhere a labelled gist, **never a fake translation** | Live translation |
| Policy Q&A | Retrieval over SP-1..SP-9 with a coverage threshold → cite or “Not covered” | Model answer; citations validated against the clause list |
| Guardrails | Always on | Always on, applied identically to model output |

**Inference coverage.** Demo mode covers 100% of cases. Live mode runs per case on demand; batch live triage (e.g. Message Batches API) is the obvious next step and is not built. **Live output was not benchmarked**: the build environment had no API key. The integration (`server/server.mjs`, `src/ai.js`) is written against the Anthropic SDK with structured JSON output, refusal handling, output validation and safe fallbacks, but it is untested against the real API.

## Architecture

```
candidate_cases.json ──► unifiedFacts()  (6 mocked source systems, fact-level provenance)
                     ──► redactForAI()   (PII boundary: no PII block, pseudonymous IDs, free-text redaction)
                     ──► AIProvider.triage()  (LiveProvider → server → Claude | SimulatedProvider)
                     ──► applyGuardrails()    (deterministic, non-AI; cannot be bypassed by model output)
                     ──► record + lane       (critical / priority / standard / auto) ordered by tier → UTC deadline
                     ──► human decision      (approve / override / escalate + reason; role checks) ──► access log, export
```

| File | Responsibility |
|---|---|
| `src/signals.js` | Source unification + provenance; deterministic signal extraction (negation-aware) |
| `src/lexicon.js` | Multilingual concept lexicons (danger, violence, threat, injection, …) |
| `src/simulated.js` | Demo “AI”: same output contract as the live model |
| `src/guardrails.js` | Policy enforcement and precedence (SP-7 > SP-8 > SP-6 > injection > data quality > auto-resolve gate) |
| `src/triage.js` | Pipeline, duplicate index, queue ordering, record shape |
| `src/ai.js` | Provider interface (`SimulatedProvider`, `LiveProvider`), output validation |
| `src/pii.js` | Masking, role definitions, redaction, PII refusal check |
| `src/store.js` | Decisions, access log, retention purge, CSV/JSON export |
| `src/policyqa.js` | Offline policy Q&A with “Not covered” |
| `server/server.mjs` | Static server + `/api/ai` proxy (key never reaches the browser) |
| `validation/` | Gold labels (30), silver reference labeller (5,000), results |

## Where things run

| Upstream: intake service (on ticket creation) | Reviewer console (humans only) |
|---|---|
| Unify sources → redact → AI proposal → guardrails → route | **L4 · Respond**: acknowledge → contact reporter → emergency services → protect → outcome (timestamped) |
| L4: page the duty manager immediately | **L2–L3 · Decide**: approve / override / escalate the proposal, with a reason |
| L1 that passes every gate: closed with a message or credit, never queued | **QA & audit**: auto-resolved sample, access log, exports |

In the prototype the intake step runs in the browser so the demo works without a server. In production it is a service in the ticketing pipeline, so paging and L1 closure never wait for someone to open the console.

## Severity paths

| Lane | Tier | What happens |
|---|---|---|
| **Critical** | L4 | Escalated and duty manager paged at intake. In the console the human *acts* through a response checklist rather than re-triaging. Locked: automation cannot close, downgrade or resolve; only a duty manager can downgrade, with a reason. |
| **Priority** | L3 | Specialist review. AI never closes. Threats, violence/sexual allegations and injection attempts floor here. |
| **Standard** | L2 (+ blocked L1) | Agent review. Also gets anything uncertain, conflicting, with missing evidence, or not on the SP-1 allow-list. |
| **Auto (QA view)** | L1 | Resolved upstream, not a work queue. Auto-resolved only if L1 **and** an SP-1 category **and** confidence ≥ 0.75 **and** no blocking flags. 5% QA sample. Reviewers can still override. |

## Protecting personal information

* **Redaction before AI.** The PII block is dropped, reporter and trip IDs are pseudonymised, and free text has known names, phones, emails, plates and addresses replaced with tokens. Generic phone, email and address patterns are also caught. The server **refuses** any payload that still looks like it contains PII.
* **Role-based masking.** Agent (L1/L2, cannot reveal), Specialist, Duty manager (reveal per field with a logged reason), Auditor (no PII). PII is never shown unmasked by default, including in the report text.
* **Access logging.** Case opens, reveals (with reason), translations, AI calls, decisions, alert acknowledgements and exports are logged. Only metadata is logged, never content.
* **Retention.** Decisions are kept 365 days and the access log 400 days, with a purge on load. Raw case data and PII are never persisted by the app.
* **Limitations.** Roles are client-side (no SSO). The log lives in browser storage. Free-text redaction misses names that appear *only* in free text (production needs in-boundary NER). Exports contain no PII but do contain rationales.

## Tests

`npm test` runs 25 tests: SP-7 escalation and locking (including against a hostile AI proposal), stalking via telematics, no AI closure of L3/L4, SP-8 with counter-evidence, prompt injection (English and Japanese wrappers), the SP-1 auto-resolve gate and confidence threshold, SP-9 at three levels, missing data, duplicates, full-dataset invariants, queue ordering, PII redaction over 500 cases, masking, decision validation and role limits, the L4 response checklist (order, timestamps, close conditions), export columns without PII, retention, policy Q&A “Not covered”, and invalid model output.

## Known limitations and next steps

1. Benchmark live Claude on the gold set and the full file; add batch inference.
2. Replace lexicon-based guardrail features with a model-plus-lexicon ensemble, measured per language.
3. Real integrations (ticketing, trip, telematics), SSO roles, a server-side audit store and on-call paging.
4. In-boundary NER for free-text PII.
5. Policy-owner rulings on the 6 gaps in `docs/DECISIONS.md`.
