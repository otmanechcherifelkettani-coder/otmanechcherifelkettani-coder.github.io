"""VO for the university demo film (Kokoro am_onyx), one file per line, silence-trimmed."""
import json, sys, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
M = sys.argv[1]; SPEED = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
k = Kokoro(f'{M}/kokoro-v1.0.onnx', f'{M}/voices-v1.0.bin')
L = [
 "Artificial intelligence is rewriting how the world works.",
 "By twenty thirty, employers expect four in ten core skills to change.",
 "And the next wave is already here: AI agents.",
 "Software that doesn't just answer. It acts.",
 "By twenty twenty-eight, a third of enterprise applications will have agents built in.",
 "Yet more than forty percent of agent projects are expected to be cancelled.",
 "The gap isn't the technology. It's people who know how to ship it.",
 "Morocco is aiming for a hundred thousand digital talents a year.",
 "Using AI is no longer enough. Graduates need to know how to build with it.",
 "Introducing: Shipping AI That Works.",
 "A two-day, hands-on workshop for universities and business schools.",
 "In teams, students take on a realistic business case, and build a working AI agent.",
 "They test it against evidence, stress its guardrails, and defend a go or no-go decision.",
 "Every student leaves with a portfolio: a prototype, an evaluation report, a risk assessment, and a business case.",
 "And your university gets a ready-to-grade programme, built on real industry practice.",
 "Your instructor builds these systems for a living.",
 "At Uber Eats, he leads customer support automation across fifty-one countries and eleven languages, taking AI agents from prototype to production.",
 "And he teaches in French, Arabic and English.",
 "Don't just teach your students about AI.",
 "Let them ship it.",
 "Bring Shipping AI That Works to your campus.",
]
d = {}
for i, line in enumerate(L, 1):
    s, sr = k.create(line, voice='am_onyx', speed=SPEED, lang='en-us')
    a = np.abs(s); idx = np.where(a > .01 * a.max())[0]; s = s[max(0, idx[0] - 480):idx[-1] + 1440]
    sf.write(f'vo/l{i:02d}.wav', s, sr); d[i] = round(len(s) / sr, 2)
print(d, 'total', round(sum(d.values()), 2)); json.dump({'dur': d, 'lines': L}, open('vo/dur.json', 'w'))
