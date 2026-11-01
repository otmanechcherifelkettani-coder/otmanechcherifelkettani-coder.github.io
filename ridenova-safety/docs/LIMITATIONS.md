# Limitations (explicit)

**Scope and data**
- RideNova, its SP-1..SP-9 policy and all 5,000 cases are fictional and synthetic.
- The capability model (`general`, `threats_exposure`, `violence_sexual`, `safety_incidents`) and the user directory are invented; the brief defines neither.
- `submitted_at` has no timezone. City-level UTC offsets are assumed (see `src/tz.js`).
- There are no historical response or resolution timestamps, so **no historical SLA performance is claimed**. SLA figures come from a replay clock (default 8 March 2026, 08:00 UTC).

**Security and privacy**
- Sign-in is **simulated**: you pick a profile, and a session token maps to it. The server enforces scopes on every request, but this is not real authentication, SSO or production RBAC.
- Redaction is pattern-based plus known-value matching. A stranger's name that appears only in free text is not caught. This is not complete anonymisation.
- Records live in local append-only JSONL files. They are durable across refresh and restart but are **not tamper-proof or immutable audit storage**.
- Retention purges by real recording time on server start. No legal retention schedule exists yet.
- Exports have no personal data and are restricted to duty managers. They are still downloadable files that need governance.

**AI**
- Without `ANTHROPIC_API_KEY`, all AI output is **simulated** (rules plus a multilingual lexicon). The lexicon was tuned on this same file, so its results are in-sample.
- The live Claude path (re-assessment, translation, policy Q&A) is implemented with validation and failure handling but was **not run** in the build environment (no key). It has not been benchmarked.
- Confidence scores are **uncalibrated**.
- Demo translations are fixtures for 23 cases, written by AI during development. Every other non-English case shows "no translation", never a guess.

**Execution and automation**
- Every action goes through a **simulated adapter**. Nothing is sent, charged or suspended. Failures are deterministic (about 5%) to exercise the exception path.
- Emergency services are never contacted by the system. Managers record what they did themselves.
- Automation starts in shadow mode. "Enable" is a demo switch for fictional SP-1 cases only, with no gradual or per-market rollout control.

**Validation**
- The 30 "reference" labels were **drafted by AI**, and the silver labels were AI-assisted. Neither has been adjudicated by the candidate. `validation/candidate_adjudication.json` is the empty template for that review.
- The tests prove the coded rules behave as specified. They are **not** proof of complete policy coverage or production safety.

**Not built**
- Real integrations, an on-call paging integration, second-approval workflows (the hook exists; the fictional policy requires none), reporter-facing messaging, batch live inference, model monitoring and a QA sampling UI.
