"""Run the eval set, grade every case, print the scorecard that goes in your Production Report.

    python eval.py                 # all cases
    python eval.py --only E03 R02  # a few cases while debugging
    python eval.py --skip-judge    # code checks only (free and instant to grade)

Grading = deterministic code checks first, then an LLM judge for what code cannot check (tone, correctness of the
explanation). A case passes only if every check and the judge pass. Write the pass bar BEFORE you run.
"""
import argparse
import csv
import json
import pathlib
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel

import agent
import llm

ROOT = pathlib.Path(__file__).parent
PASS_BAR = 0.85  # decided before the first run; do not move it after seeing results


class Verdict(BaseModel):
    passed: bool
    reason: str


JUDGE_PROMPT = """You grade one reply from a telecom support agent against one criterion.
Read the customer message, the tools the agent called with their results, and the final reply.
Answer passed=true only if the reply fully meets the criterion. Be strict; a partial match fails.
Give a one-sentence reason that names the specific problem when it fails.

<customer>{input}</customer>
<tool_calls>{tool_calls}</tool_calls>
<reply>{reply}</reply>
<criterion>{rubric}</criterion>"""


def code_checks(case: dict, out: dict) -> list[str]:
    called = [c["name"] for c in out["tool_calls"]]
    failures = []
    for name in case["must_call"]:
        if name not in called:
            failures.append(f"did not call {name}")
    for name in case["must_not_call"]:
        if name in called:
            failures.append(f"called forbidden {name}")
    escalated = "escalate_to_human" in called
    if case["expect_escalation"] is not None and escalated != case["expect_escalation"]:
        failures.append(f"escalation expected={case['expect_escalation']} got={escalated}")
    credited = sum(c["output"].get("amount_mad", 0) for c in out["tool_calls"]
                   if c["name"] == "issue_credit" and c["output"].get("status") == "issued")
    if credited > case["credit_max_mad"]:
        failures.append(f"credited {credited} MAD > max {case['credit_max_mad']}")
    return failures


def judge(case: dict, out: dict) -> Verdict:
    calls = json.dumps([{k: c[k] for k in ("name", "input", "output")} for c in out["tool_calls"]], ensure_ascii=False)
    response = llm.client.messages.parse(
        model=llm.JUDGE_MODEL,
        max_tokens=2000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(
            input=case["input"], tool_calls=calls, reply=out["reply"], rubric=case["rubric"])}],
        output_format=Verdict,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        return Verdict(passed=False, reason="judge refused or returned nothing")
    return response.parsed_output


def grade(case: dict, use_judge: bool) -> dict:
    out = agent.run(case["input"], run_id=f"eval-{case['id']}")
    failures = code_checks(case, out)
    verdict = judge(case, out) if use_judge else Verdict(passed=True, reason="judge skipped")
    return {
        "id": case["id"],
        "category": case["category"],
        "passed": not failures and verdict.passed,
        "code_failures": "; ".join(failures),
        "judge_passed": verdict.passed,
        "judge_reason": verdict.reason,
        "human_pass": "",  # fill in by hand for 20+ rows, then run agreement.py
        "tools": " > ".join(c["name"] for c in out["tool_calls"]),
        "reply": out["reply"],
        "cost_usd": out["cost_usd"],
        "latency_s": out["latency_s"],
        "turns": out["turns"],
        "outcome": out["outcome"],
    }


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(p * (len(ordered) - 1))))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--skip-judge", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    cases = [json.loads(line) for line in (ROOT / "evals" / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.only:
        cases = [c for c in cases if c["id"] in args.only]

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda c: grade(c, not args.skip_judge), cases))

    out_file = ROOT / "results" / f"run-{time.strftime('%Y%m%d-%H%M%S')}.csv"
    out_file.parent.mkdir(exist_ok=True)
    with out_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    pass_rate = sum(r["passed"] for r in rows) / len(rows)
    print(f"\nPASS RATE {pass_rate:.0%}  ({sum(r['passed'] for r in rows)}/{len(rows)})  bar {PASS_BAR:.0%}  ->  "
          f"{'SHIP' if pass_rate >= PASS_BAR else 'DO NOT SHIP'}")
    for cat in sorted({r["category"] for r in rows}):
        sub = [r for r in rows if r["category"] == cat]
        print(f"  {cat:<12} {sum(r['passed'] for r in sub)}/{len(sub)}")
    costs = [r["cost_usd"] for r in rows]
    lat = [r["latency_s"] for r in rows]
    print(f"cost/task ${statistics.mean(costs):.4f}   latency p50 {percentile(lat, .5):.1f}s  p95 {percentile(lat, .95):.1f}s")
    print("\nFailures:")
    for r in rows:
        if not r["passed"]:
            print(f"  {r['id']}: {r['code_failures'] or ''} {'' if r['judge_passed'] else '| judge: ' + r['judge_reason']}")
    print(f"\nSaved {out_file.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
