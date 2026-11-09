"""VO for the v2 university film (Kokoro am_michael), one file per sentence, silence-trimmed."""
import json, sys, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
k = Kokoro('/root/.cache/hyperframes/tts/models/kokoro-v1.0.onnx', '/root/.cache/hyperframes/tts/voices/voices-v1.0.bin')
SPEED = float(sys.argv[1]) if len(sys.argv) > 1 else 1.15
L = [
 "Artificial intelligence is transforming the way industries work.",
 "The next generation of professionals will need more than the ability to use AI.",
 "They'll need to know how to build with it.",
 "Universities have an opportunity to prepare students for this new reality,",
 "bringing practical AI experience into the classroom.",
 "Introducing: Shipping AI That Works.",
 "A two-day, hands-on workshop, led by an industry practitioner with experience building and deploying AI agents at Uber.",
 "Working in teams, students identify business challenges, design and build AI agents, test their performance, evaluate risks, and explore what it takes to deploy them responsibly.",
 "They leave with a working prototype, practical project deliverables, and skills they can carry into their careers.",
 "Don't just teach students about AI.",
 "Give them the opportunity to build it.",
 "Bring Shipping AI That Works to your university.",
]
d = {}
for i, line in enumerate(L, 1):
    s, sr = k.create(line, voice='am_michael', speed=SPEED, lang='en-us')
    a = np.abs(s); idx = np.where(a > .01 * a.max())[0]; s = s[max(0, idx[0] - 480):idx[-1] + 1440]
    sf.write(f'vo2/l{i:02d}.wav', s, sr); d[i] = round(len(s) / sr, 2)
print(d, 'total', round(sum(d.values()), 2)); json.dump(d, open('vo2/dur.json', 'w'))
