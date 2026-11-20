# Instructor notes — 1-Day Lab simulation, student run 1

Student profile: bac+4 HESTIM, comfortable with computers, never built an agent, never used Claude Code.
Setup: empty Claude Code session, case = Atlas Telecom (unless changed at build card), agent model claude-haiku-5-5, budget < $2.
Format note: one student alone (not a team of 3–4), so the red-team swap is replaced by me attacking the student's agent.

## Running cost
| Gate | Spend so far |
|---|---|
| Opening | $0.00 (no API calls yet) |

## Block log

### Block 1 — The opening (planned 45 min · simulated ~15 min of exchange)
- **Gate: PASS.** 4/4 on the classification check.
- **Misunderstanding:** said the difference between workflow (#3) and agent (#4) is "4 requires LLM judgement". Classic confusion: workflows contain LLMs too. Re-explained with "who decides the steps" + the flowchart test ("could you draw it before the customer writes?"). Will re-test at the build card (pattern choice).
- Injection check: answered correctly and tersely ("model can be tricked; rule 2, the code enforces it").
- **Explained twice:** workflow vs agent (once in the table, once after the wrong answer).
- **Course change:** the course pack's one-line quick check only asks for labels; all four labels can be right while the concept is wrong. Add the follow-up "what's the difference between #3 and #4?" to the official quick check. The four-row table should say explicitly that a workflow can contain a model ("Code fixes the steps; the model fills them" is right but too subtle for a first read).
- **Course change:** the five rules are meant to be "shown live", but in a 1-student or from-zero setting there is no agent yet at 09:15. Either pre-build the instructor demo agent (starter kit, run by the instructor) or explicitly move the live demos to after build v0 / guardrails. Here they were deferred.
- Terms introduced: model, tool, agent, prompt, trace, pass bar, prompt injection, gate, API key, environment variable.

### Block 2 — Build card / Q1 + Q2 (planned 45 min · ~8 exchanges)
- **Gate: PASS** (with instructor help on Q1).
- **Biggest struggle:** first answer to Q1 was written *as a customer* ("I have mobile line / I cannot call / I don't understand"). The student did not know what "user", "problem", "baseline" mean on a build card, and did not see that they are written from the builder's side.
- **Second struggle:** "which brief are you talking about" — the client brief was embedded as a blockquote in a long message and was missed. Fixed by saving it as `BRIEF.md` and re-showing it plainly.
- Then merged problem + baseline in one line (fine), skipped the user line, and twice skipped the guardrail metric ("must not break"); I wrote it for them and asked for confirmation (no explicit confirmation given).
- Kill filters: answers right but vague ("nature and complexity", "medium" with no reason, "I guess yes" on checkability). Student doesn't yet know HOW outputs get checked — expected, evals come later; I previewed code checks vs judge.
- Pattern: "agent, because the steps depend on the message" — correct, uses this morning's concept. The workflow/agent confusion from block 1 appears resolved.
- **Explained twice:** what a baseline is (definition, then restaurant example); the brief.
- **Course changes:**
  1. Hand out the client brief as a separate one-page document *before* the block (the course pack lists "what to fill" but contains no brief text for the telecom case; I had to write one). Put the baseline numbers (4 h, 60%) in it.
  2. Provide a build-card template with one worked example from a different case (e.g. logistics), so students see the builder's-eye voice before writing.
  3. Add "must not break" (guardrail metric) as an explicit field on the template; students won't invent it.
  4. Kill filter 4 ("can the output be checked?") cannot be answered well before the evals block; give the answer shape on the template ("code checks for actions + judge for wording").

### Block 3 — Build v0 (planned 90 min · ~10 exchanges)
- **Gate: PASS.** 3 typical cases answered end to end (Salma outage, Youssef balance, Khadija suspended), every model and tool call in `traces.jsonl` with cost and latency. Spend at gate: **$0.0022**.
- Tool design: student listed exactly the six tools of the reference design, verify first, but gave no descriptions and no reason for the order.
- **Struggled:** reading code. "Where am I expected to check this?" — a student who has never used Claude Code does not know the file panel exists, or that they can ask Claude to show a function. Had to paste the function inline with line numbers. Once shown, answered correctly (line 40, C001 vs C004).
- **Misread output:** attributed an error line from a different call to Mehdi's credit case. Matching output lines to calls is a skill to teach explicitly before error analysis.
- **Explained twice:** the system prompt (introduced in one line when the loop was shown; student asked "what is the system prompt?").
- Predictions before running: 2/2 tool sequences right for the simple cases; Khadija predicted verify → get_account (actual: 5 tool calls incl. a guessed `check_outage("Casablanca")` and a duplicated EN answer). Good material for error analysis.
- **Course changes:**
  1. Add a 5-minute "how to read code in Claude Code" moment at the start of build v0 (file panel; "show me function X"; line numbers). Students who never used the tool lose the thread otherwise.
  2. Define "system prompt" with its own slide/line in the opening, next to model/tool/agent; it's the main lever all afternoon.
  3. The "predict before you run" ritual worked very well and is cheap (each run ~$0.0006). Make it a formal step in the workbook.
  4. Writing tools.py + agent.py from zero with the student took most of the block even with the instructor typing. In a 30-student room with teams, the course pack's own plan (start from the starter kit) is right; "from zero" only fits if the instructor live-codes once for everyone.
