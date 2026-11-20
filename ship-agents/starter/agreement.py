"""Can you trust your LLM judge? Compare it to your own labels.

1. Open the latest results/run-*.csv, read 20+ rows, put 1 (good) or 0 (bad) in human_pass.
2. python agreement.py results/run-XXXX.csv

TPR = of the replies you judged good, how many the judge also passed.
TNR = of the replies you judged bad, how many the judge also failed. TNR is the one that protects users.
Below ~0.8 on either: rewrite the rubric (not your labels) and re-run.
"""
import csv
import sys

rows = [r for r in csv.DictReader(open(sys.argv[1], encoding="utf-8")) if r["human_pass"].strip() in {"0", "1"}]
if not rows:
    sys.exit("No human labels yet: fill the human_pass column with 0 or 1.")

good = [r for r in rows if r["human_pass"].strip() == "1"]
bad = [r for r in rows if r["human_pass"].strip() == "0"]
tpr = sum(r["judge_passed"] == "True" for r in good) / len(good) if good else float("nan")
tnr = sum(r["judge_passed"] == "False" for r in bad) / len(bad) if bad else float("nan")
print(f"labelled {len(rows)}  |  TPR {tpr:.0%} ({len(good)} good)  |  TNR {tnr:.0%} ({len(bad)} bad)")
for r in rows:
    if (r["human_pass"].strip() == "1") != (r["judge_passed"] == "True"):
        print(f"  disagree {r['id']}: you={r['human_pass']} judge={r['judge_passed']} — {r['judge_reason']}")
