"""Synthesize the tightened VO line by line with Kokoro (am_michael)."""
import json, sys, soundfile as sf
from kokoro_onnx import Kokoro
k = Kokoro('/root/.cache/hyperframes/tts/models/kokoro-v1.0.onnx', '/root/.cache/hyperframes/tts/voices/voices-v1.0.bin')
SPEED = float(sys.argv[1]) if len(sys.argv) > 1 else 1.12
LINES = [
 "AI is changing the world of work.",
 "Tomorrow's professionals won't just use it.",
 "They'll need to build with it.",
 "As Morocco accelerates its AI ambitions, universities can prepare a new generation to turn this technology into something useful.",
 "And that starts with practical experience.",
 "At Uber, I've led the development of LLM-based agents supporting millions of customer interactions.",
 "Now I'm bringing that real-world experience into the classroom.",
 "Introducing: Shipping AI That Works.",
 "A two-day, hands-on workshop that goes beyond theory.",
 "In teams, students take on a realistic business problem, design an AI agent, build a working prototype, and put it to the test.",
 "They learn to evaluate it, manage the risks, and deploy AI responsibly.",
 "And they leave having built something themselves.",
 "The next generation shouldn't just use AI.",
 "They should know how to build it.",
]
out = {}
for i, line in enumerate(LINES, 1):
    s, sr = k.create(line, voice='am_michael', speed=SPEED, lang='en-us')
    f = f'vo/l{i:02d}.wav'; sf.write(f, s, sr); out[f] = round(len(s) / sr, 2); print(f, out[f], line)
print('total', round(sum(out.values()), 2))
json.dump(out, open('vo/durations.json', 'w'), indent=1)
