# Starter kit — Atlas Telecom support agent

The reference project for the **1-Day Lab** and week 1 of the **5-Week Lab**.
Atlas Telecom is fictional and every record in `data/` is synthetic.

| File | What it teaches |
|---|---|
| `agent.py` | The agent loop written out by hand: call the model, run tools, send results back, stop. Turn cap + hand-off as the exit. |
| `tools.py` | Six tools with model-facing descriptions. Money and privacy rules enforced in code, not only in the prompt. |
| `llm.py` | One place for model calls: model choice, cost per call, latency, one trace line per call. |
| `evals/cases.jsonl` | 20 test cases: typical / edge / refusal / error-prone, each with code checks and a one-line rubric. |
| `eval.py` | Code checks first, LLM judge second, pass bar written before the run, scorecard printed. |
| `agreement.py` | Checks the judge against your own labels (TPR / TNR). |
| `gen_cases.py` | Generates messy candidate cases for human review. |
| `app.py` | Streamlit chat UI with a "Flag this answer" button that feeds error analysis. |

## Setup (10 minutes)

```bash
python -m venv .venv && source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

```bash
export ANTHROPIC_API_KEY=...   # from console.anthropic.com
```

## Run order on the day

```bash
python agent.py "Coupure fibre à Maarif depuis ce matin. Salma, 0661234567"
```

```bash
python eval.py --skip-judge
```

```bash
python eval.py
```

```bash
python agreement.py results/run-YYYYMMDD-HHMMSS.csv
```

```bash
streamlit run app.py
```

## See every step (optional, recommended)

Create a free LangSmith account, then set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY`. Every run then shows up in
the LangSmith web UI as one trace: each model call, each tool call, tokens, cost and time. It wraps this plain SDK
code; no LangChain or LangGraph needed. Without the key, traces still go to `traces/traces.jsonl`.

## Models and cost

Defaults: agent `claude-haiku-5-5` (the cheapest current model) at effort `medium`, judge `claude-sonnet-5-5` at effort `low`. Compare once with `AGENT_MODEL=claude-opus-5-5 python eval.py` and keep the bigger model only if the pass rate justifies the cost.
Change them with `AGENT_MODEL`, `AGENT_EFFORT`, `JUDGE_MODEL`. Server-side refusal fallback is enabled in `llm.py`
(`fallbacks="default"`) for models that support it (not Haiku 5.5), so a declined request is retried on a fallback model inside the same call.
Every call is written to `traces/traces.jsonl` with tokens, cost and latency. Read your traces before changing prompts.

## Make it yours

Keep the loop, swap the case: replace `data/`, the tools in `tools.py`, the `SYSTEM` prompt, and write your own
`evals/cases.jsonl`. The graduation bar does not change.
