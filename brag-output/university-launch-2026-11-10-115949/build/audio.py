"""Voiceover track + understated ambient-electronic score for the 60 s university launch film.

Run from the build/ directory:  python3 audio.py
Writes ../composition/assets/vo/voiceover.wav and ../composition/assets/music/score.wav
(the score is pre-ducked under the voice) and prints each VO line's on-screen window.
"""
import json
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
DUR = 60.0
N = int(SR * DUR)
VO_DIR = '../composition/assets/vo'
rng = np.random.default_rng(7)

# ---------- voiceover: trim each line and place it inside its scene window ----------
PLACE = [0.45, 8.6, 18.55, 28.7, 44.55, 54.55]          # scene windows: 0-8, 8-18, 18-28, 28-44, 44-54, 54-60
vo = np.zeros(N)
windows = []
for i, t in enumerate(PLACE, 1):
    x, sr = sf.read(f'{VO_DIR}/raw{i}.wav')
    if x.ndim > 1:
        x = x.mean(1)
    if sr != SR:
        x = np.interp(np.arange(0, len(x) * SR / sr) * sr / SR, np.arange(len(x)), x)
    a = np.abs(x)
    idx = np.where(a > 0.012 * a.max())[0]
    x = x[max(0, idx[0] - 400): idx[-1] + 1800]
    x[:200] *= np.linspace(0, 1, 200)
    x[-900:] *= np.linspace(1, 0, 900)
    s = int(t * SR)
    vo[s:s + len(x)] += x
    windows.append((round(t, 2), round(t + len(x) / SR, 2)))

hp = butter(2, 80, 'hp', fs=SR, output='sos')
vo = sosfilt(hp, vo)
act = np.abs(vo) > 1e-3
vo *= 10 ** (-12 / 20) / np.sqrt(np.mean(vo[act] ** 2))          # about -12 dBFS RMS while speaking
room = np.exp(-np.arange(int(.5 * SR)) / SR * 9) * rng.standard_normal(int(.5 * SR))
room /= np.sqrt((room ** 2).sum())
vo = vo + fftconvolve(vo, room)[:N] * 0.03                          # a touch of air, still dry
peak = np.max(np.abs(vo))
if peak > 0.89:
    vo *= 0.89 / peak
sf.write(f'{VO_DIR}/voiceover.wav', np.stack([vo, vo], 1).astype(np.float32), SR, subtype='PCM_16')

# ---------- score ----------
BPM = 96
B = 60 / BPM            # 0.625 s per beat
BAR = 4 * B             # 2.5 s per bar


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def add(buf, sig, t):
    i = int(t * SR)
    n = min(len(sig), len(buf) - i)
    if n > 0 and i >= 0:
        buf[i:i + n] += sig[:n]


def lpf(x, fc, order=2):
    return sosfilt(butter(order, fc, 'lp', fs=SR, output='sos'), x)


def pad(notes, L, g=1.0, att=1.2, rel=1.6, bright=0.0):
    t = np.arange(int((L + rel) * SR)) / SR
    env = np.minimum(1, t / att) * np.where(t > L, np.exp(-(t - L) * 3 / rel), 1)
    s = np.zeros_like(t)
    for n in notes:
        f = midi(n)
        for d in (1, 1.0035, 0.9968):
            ph = rng.uniform(0, 2 * np.pi)
            s += np.sin(2 * np.pi * f * d * t + ph) + (0.18 + bright) * np.sin(4 * np.pi * f * d * t + ph)
    return g * 0.28 * s / (3 * len(notes)) * env


def pluck(n, g=1.0, L=1.4, tone=0.5):
    t = np.arange(int(L * SR)) / SR
    f = midi(n)
    s = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (4 + k * 3 / tone)) for k, a in ((1, 1), (2, .5), (3, .25), (4, .12)))
    return g * 0.2 * s * np.minimum(1, t / 0.003)


def kick(g=1.0):
    t = np.arange(int(.45 * SR)) / SR
    f = 46 + 70 * np.exp(-t * 28)
    return g * 0.55 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5)


def hat(g=1.0):
    t = np.arange(int(.06 * SR)) / SR
    x = rng.standard_normal(len(t))
    x = x - lpf(x, 6000)
    return g * 0.05 * x * np.exp(-t * 90)


def riser(L, g=1.0):
    t = np.arange(int(L * SR)) / SR
    x = rng.standard_normal(len(t))
    out = np.zeros_like(x)
    for k in range(8):                       # sweep the noise band upward in steps
        seg = slice(int(k * len(t) / 8), int((k + 1) * len(t) / 8))
        out[seg] = lpf(x, 600 + 900 * k)[seg]
    return g * 0.07 * out * (t / L) ** 2.2


def swell_hit(g=1.0):
    t = np.arange(int(2.5 * SR)) / SR
    x = rng.standard_normal(len(t))
    return g * (0.09 * lpf(x, 1800) * np.exp(-t * 2.4) + 0.35 * np.sin(2 * np.pi * 41 * t) * np.exp(-t * 3))


pads, arps, low, perc, fx = (np.zeros(N) for _ in range(5))
# F major family, two bars each: Fmaj9, Am7, Cmaj9, Gsus2/B -> warm and unresolved until the end
CH = [([53, 60, 64, 67, 69], 41), ([57, 60, 64, 67, 71], 45), ([60, 64, 67, 71, 74], 48), ([55, 59, 62, 67, 69], 43)]
ARP = [0, 2, 4, 3, 1, 3, 2, 4]
bars = int(DUR / BAR)
for b in range(bars):
    t0 = b * BAR
    ch, root = CH[(b // 2) % 4]
    if t0 >= 54:
        break
    if b % 2 == 0:
        g = 0.55 if t0 < 8 else (0.7 if t0 < 28 else 0.8)
        add(pads, pad(ch[:4], 2 * BAR, g, bright=0.08 if t0 >= 28 else 0.0), t0)
    # arpeggio: absent in the cold open's first bar, sparse in S1-S2, eighths from S3, sixteenth sparkle in S4
    if t0 >= 2.5:
        step = B / 2 if t0 >= 18 else B
        n = int(BAR / step)
        for k in range(n):
            note = ch[ARP[k % 8] % len(ch)] + 12
            add(arps, pluck(note, 0.55 if t0 < 18 else 0.48, tone=0.5 if t0 < 28 else 0.8), t0 + k * step)
    # soft pulse from S3 on, every beat; hats on offbeats only in the demo section
    if t0 >= 18:
        for k in range(4):
            add(low, kick(0.75 if k == 0 else 0.45), t0 + k * B)
            add(low, pluck(root, 0.6, L=0.5, tone=0.3), t0 + k * B)
    if 28 <= t0 < 44:
        for k in range(8):
            add(perc, hat(1.0 if k % 2 else 0.35), t0 + k * B / 2)

# moments
add(fx, riser(2.0, 1.0), 16.0)                 # into the title reveal at 18 s
add(fx, swell_hit(1.0), 18.0)
add(fx, riser(1.6, 0.6), 42.4)                 # into the outcomes
add(fx, swell_hit(0.6), 44.0)
add(fx, riser(2.0, 0.8), 52.0)                 # into the close
add(fx, swell_hit(0.9), 54.0)
# closing resolution: Fmaj9 on the final title, rung out
add(pads, pad([53, 60, 64, 67, 72], 4.6, 0.95, att=0.4, rel=1.4, bright=0.05), 54.0)
for i, n in enumerate((41, 53, 60, 64, 67, 72, 76)):
    add(arps, pluck(n, 0.5, L=4.0, tone=1.2), 54.0 + i * 0.07)

ir_n = int(2.8 * SR)
ti = np.arange(ir_n) / SR
ir = lpf(rng.standard_normal(ir_n), 4500) * np.exp(-ti * 2.0)
ir /= np.sqrt((ir ** 2).sum())
dry = pads * 0.8 + arps * 0.55 + lpf(low, 700) * 0.8 + perc * 0.7 + fx * 0.8
wet = fftconvolve(pads * 0.4 + arps * 0.7 + fx * 0.3, ir)[:N] * 0.4
L_ = dry + wet
R_ = dry + np.roll(wet, int(0.013 * SR))       # gentle width

# duck about 8 dB under the voice, 0.2 s attack / 0.5 s release
env = np.convolve(np.abs(vo), np.ones(2205) / 2205, 'same')
gate = (env > 0.004).astype(float)
k = int(0.35 * SR)
sm = np.convolve(gate, np.ones(k) / k, 'same')
duck = 1 - (1 - 10 ** (-8 / 20)) * np.clip(sm * 1.4, 0, 1)
mix = np.stack([L_ * duck, R_ * duck], 1)
mix[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
fo = int(1.6 * SR)
mix[-fo:] *= (np.linspace(1, 0, fo) ** 1.6)[:, None]
mix *= 10 ** (-20 / 20) / np.sqrt(np.mean(mix ** 2))   # bed sits around -20 dBFS RMS before ducking
mix = np.tanh(mix * 1.2) / np.tanh(1.2)
mix *= min(1.0, 0.7 / np.max(np.abs(mix)))
sf.write('../composition/assets/music/score.wav', mix.astype(np.float32), SR, subtype='PCM_16')
json.dump(windows, open('vo_windows.json', 'w'))
print('vo windows', windows)
