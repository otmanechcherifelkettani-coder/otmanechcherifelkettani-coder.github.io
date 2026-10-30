# Decisions, assumptions and policy interpretation

## Scope choices (prioritisation)

| Built (P0–P1) | Built, gated (P2) | Deliberately not built |
|---|---|---|
| Danger detection + duty-manager alert, locked lane | L1 auto-resolve (allow-list, confidence gate, 5% QA) | Real system integrations, SSO |
| One-screen case view with fact-level provenance | | Server-side persistence / audit DB |
| Guardrails, lanes, deadline ordering, filters | | In-boundary NER for free-text PII |
| Human decisions with reasons + role checks | | Outbound messaging to reporters |
| PII redaction, masking, access log, retention, export | | Batch live inference |
| Swappable AI provider, live Claude path, key-free demo | | |

**Why this order:** the riskiest failure is a missed or auto-closed danger case, so the safety floor is built first. The biggest cost is search time, so unification comes next. Automation saves the most hours but carries the most risk, so it comes last and behind a gate.

## How overlapping rules resolve

The most protective outcome wins, in this order:

1. **SP-7 danger** (SOS, stalking telematics, medical or weapon language, a report filed mid-trip with the vehicle stopped roadside) → L4, `ESCALATE_L4_IMMEDIATE`, alert, locked.
2. **SP-8** violence or sexual-misconduct allegation → floor L3, human review, even with counter-evidence (which is flagged `conflicting_signals`).
3. **SP-6** harm-threat language → floor L3. Rating or deactivation threats with no harm are *not* SP-6 threats.
4. **Prompt injection** → floor L3 (specialist), confidence capped at 0.5. Text written to manipulate triage cannot be trusted to be minor.
5. **SP-9** prior flag for the *same* behaviour → +1 tier. Applied only when the current behaviour is positively recognised.
6. **Missing evidence** → `REQUEST_MORE_INFO` (unless danger is present), confidence capped.
7. **Duplicates** (same reporter + same trip, later submission) → `MERGE_DUPLICATE`, inheriting the parent’s tier; an L3+ parent gets a `priority` flag.
8. **Auto-resolve gate** → otherwise `ROUTE_L2_REVIEW` with `auto_resolve_blocked`.

When candidate rules disagree on tier, the highest tier is taken and the alternatives appear in the rationale as “Also noted”.

## Uncertain, missing and conflicting

* **Uncertain:** nothing recognised → L2 human with low confidence and an `uncertain` flag. Never L1.
* **Missing:** trip-record errors or an unknown party → request more information; never blocks escalation.
* **Conflicting:** shown side by side with their sources (allegation vs. system signal) and flagged. The tier is never lowered because of counter-evidence when SP-8 applies.

## Policy gaps (conservative defaults — need a policy-owner ruling)

| Gap | Cases | Default | Question |
|---|---|---|---|
| SP-9 lifting L3 → L4 (location exposure + prior post-trip contact) | 38 | L4 (policy-literal) | Can history alone create an L4? (+760 L4/week at ×20) |
| Service-animal refusal | 50 | L2 via SP-5 | Add an explicit accessibility clause |
| Unregistered passenger boarded mid-trip | 76 | L3 (vulnerable situation) | L2 violation or L3? |
| Account takeover / rider ≠ profile | 20 | L3 | Also route to fraud? |
| Safety-feature use, no act alleged | 50 | L2 (not SP-1-eligible) | Does trip-sharing count as a “safety signal”? |
| Rating / deactivation threats | 51 | L1 | Confirm SP-6 means threats of harm |

## Assumptions

1. `submitted_at` is local city time. UTC offsets are valid for 1–7 Mar 2026: before US DST (8 Mar) and EU DST (29 Mar); southern-hemisphere DST active in AU-SE, NZ and CL. Per-city mapping is in `src/tz.js`.
2. The first-response deadline is `submitted_at` (UTC) + the tier SLA. There is no first-response timestamp in the data, so SLA attainment cannot be measured here.
3. Weekly figures are sample × 20 (per the brief).
4. Handling times for the capacity estimate are my assumptions: L1 6, L2 15, L3 35, L4 45 minutes. 55% of that time is search, and the unified view halves it.
5. “Credible” (SP-9) is assumed true unless counter-evidence exists. Counter-evidence lowers confidence, not tier.
6. The 30 reports with an unknown product and missing trip data are the brief’s “require more information” cases.

## Model and vendor

* **Default model:** `claude-opus-5-5` at `effort: low` for triage. It is configurable via `AI_MODEL` / `AI_EFFORT`; a cheaper model can be evaluated on the gold set before switching. Structured JSON output via `output_config.format`, server-side refusal fallback enabled, `stop_reason: refusal` handled.
* **Build vs. buy:** build the control layer (guardrails, lanes, console, evals); buy the model via API behind the provider interface; avoid end-to-end black-box triage vendors.
