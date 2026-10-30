# Validation

Reproduce with `npm run evaluate` (writes `validation/results.json`). All numbers are **measured** on the supplied file with the **demo provider + guardrails**. Live Claude output was not benchmarked (no API key in the build environment).

## Method

**Gold set (30 cases, `validation/gold_labels.json`).** Stratified by hand: every tier, all four regions, 16 languages (es, ja, ar, de, en, zh-Hant, fr, pt, tr, pl, hi/Hinglish, nl, ko, sw, it, cs), plus edge cases: prompt injection (×2), conflicting evidence, missing trip record, duplicate follow-up, mixed-language (Spanglish), SP-9 at three levels, and borderline policy gaps. I read each case and labelled it against SP-1..SP-9, with a written rationale.

**Silver reference (all 5,000, `validation/silver.mjs`).** While exploring the data I found that it was generated from about 40 scenario templates, each identifiable from system-generated fields (telematics, toolkit log, attachments, history). I labelled each scenario once against the policy and propagated the label. This allows recall to be measured on rare L4s, which 30 cases cannot do. The engine never imports these signatures, because they would not generalise.

## Results

| Measure | Result |
|---|---|
| L4 recall (silver) | **138 / 138** |
| L3+ recall (silver) | **519 / 523** (all 4 misses went to a human L2 review, not closed) |
| Unsafe auto-resolutions (non-L1 auto-closed) | **0** |
| Tier agreement (silver) | **97.8%**: 4 under-triaged, 107 over-triaged |
| Gold set | **29 / 30** tier and action |
| L1 cases auto-resolved | 3,524 of 3,629 silver-L1 (97%) |
| Full-file triage time | ~0.2–0.5 s (browser / Node) |

**Where it performed well:** all language-independent danger signals (SOS, home-proximity telematics, roadside stop mid-trip); injection detection across 15 languages; SP-9 at all three levels; duplicates linked to their parent case in every instance; the conflicting assault allegation kept at L3.

**Where it was wrong or uncertain:**
* **101 L1 → L2 over-triage**, mostly comfort complaints in long-tail languages (cs, uk, sw, …) with no lexicon match. This is a safe failure, but it costs reviewer time. Gold example: SC-0334 (Swahili, loud music).
* **Right for the wrong reason:** SC-1314 (Spanglish “te llevo free si me das tu cel”) and SC-0467 (Czech, rude + prior flags) landed on L2 because nothing was recognised and the default applies, not because SP-4 or SP-9 were understood.
* **4 under-triaged:** one typo (“tocuhed”), one typo (“Overafll”), an indirect grab description, and a follow-up whose parent was under-triaged.
* **Silver label error:** SC-2557 (Sinhala) is a racist remark that my silver labeller marked as a rating threat. Reference sets need review too.

## What I changed because of validation

| Finding | Change |
|---|---|
| `"no SOS"` in a toolkit log matched `SOS` → 25 false L4 | SOS pattern requires *pressed / triggered / alert* |
| “Minor thing”, “kind of”, “like a child” triggered the minors rule | Minors terms now require context (“underage”, “menor de edad”, …) |
| Negations (“no threats, nobody touched anyone”, “sin amenazas”, “협박도 접촉도 없었어요”) → false L3 | Negation stripping before matching (multilingual) |
| Idioms read as violence: “bateu a porta” (slammed door), “zugeschlagen”, “frenaba de golpe”, “agarró un camino”, Arabic “لمس” inside “لمساعدتكم” | Narrowed to first-person violence phrases |
| Door / phone numbers read as personal-contact requests (“numéro”, “番号”, “電話”) | Personal-contact terms require possessives (“my number”, “mi número”, …) |
| Injection + threat in Bengali, Hindi and Portuguese slipped to L2 | Injection now floors at L3 (specialist) |
| SP-9 lifted unrecognised cases | SP-9 requires a positively recognised same-behaviour match |

## Caveats

* **In-sample.** The lexicon was tuned on this file, so expect lower accuracy on new data. Mitigations: auto-resolve is gated, there is a shadow pilot before any automation, and language-independent signals drive L4.
* **Synthetic data is templated.** Real reports are more varied, which is the main argument for the live model plus guardrails rather than lexicons alone.
