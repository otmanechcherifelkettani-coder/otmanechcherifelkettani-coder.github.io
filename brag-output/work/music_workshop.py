"""Upbeat score for the workshop film: 120 BPM, C major. Every hit on the grid from t=0."""

import numpy as np, wave

SR = 44100
DUR = 61.0
N = int(SR * DUR)
B = 0.5
S = B / 4          # sixteenth
rng = np.random.default_rng(11)

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)

def env_adsr(n, a, d, s, r, sus_len):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    sl = max(0, int(sus_len * SR) - a - d)
    e = np.concatenate([np.linspace(0, 1, a, False), np.linspace(1, s, d, False), np.full(sl, s), np.linspace(s, 0, r)])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))

def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); z = 0.0
    for i in range(len(x)): z = (1 - a) * x[i] + a * z; y[i] = z
    return y

def add(buf, sig, t):
    i = int(round(t * SR)); j = min(len(buf), i + len(sig))
    if 0 <= i < len(buf): buf[i:j] += sig[:j - i]

def fft_conv(x, ir):
    n = len(x) + len(ir); m = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)]

# ---------- instruments ----------
def kick(g=1.0):
    n = int(.4 * SR); t = np.arange(n) / SR
    f = 44 + 100 * np.exp(-t * 30); ph = 2 * np.pi * np.cumsum(f) / SR
    click = np.exp(-t * 400) * .25
    return g * (np.sin(ph) * np.exp(-t * 8) * .9 + click)

_clapnz = None
def clap(g=1.0):
    n = int(.22 * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n); nz = nz - onepole_lp(nz, 1000); nz = onepole_lp(nz, 7000)
    e = np.exp(-t * 26) * (1 + .7 * ((t % .011) < .004) * (t < .033))
    return g * nz * e * .3

_hats = [None, None]
def hat(g=1.0, open_=False):
    k = 1 if open_ else 0
    if _hats[k] is None:
        n = int((.2 if open_ else .045) * SR); t = np.arange(n) / SR
        nz = rng.standard_normal(n); nz = nz - onepole_lp(nz, 8000)
        _hats[k] = nz * np.exp(-t * (16 if open_ else 80)) * .16
    return g * _hats[k]

def bass(note, length, g=1.0, bright=.35):
    n = int(length * SR); t = np.arange(n) / SR; f = midi(note)
    x = np.sin(2 * np.pi * f * t) + bright * np.sin(4 * np.pi * f * t) + .1 * np.sin(6 * np.pi * f * t)
    return g * x * env_adsr(n, .004, .07, .65, .04, length) * .30

def pluck(note, g=1.0, length=.32, bright=1.0):
    n = int(length * SR); t = np.arange(n) / SR; f = midi(note)
    x = sum(np.sin(2 * np.pi * f * k * t) / k * np.exp(-t * (7 + 6 * k / bright)) for k in range(1, 6))
    return g * x * np.minimum(1, t * 500) * .2

def keys(notes, g=1.0, length=2.0):
    """soft electric-piano-like chord hit"""
    n = int(length * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for nt in notes:
        f = midi(nt)
        x += (np.sin(2 * np.pi * f * t + .8 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 4)) * np.exp(-t * 1.6))
    return g * x / len(notes) * np.minimum(1, t * 300) * .28

def pad(notes, length, g=1.0, att=.35, rel=.6):
    n = int(length * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for nt in notes:
        for det in (-.08, .0, .08):
            f = midi(nt + det)
            x += np.sin(2 * np.pi * f * t + det * 9) + .2 * np.sin(4 * np.pi * f * t + .3)
    return g * x / (3 * len(notes)) * env_adsr(n, att, .3, .85, rel, length) * .16

def blip(note, g=1.0):
    n = int(.25 * SR); t = np.arange(n) / SR; f = midi(note)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 20) + .25 * np.sin(4 * np.pi * f * t) * np.exp(-t * 34)
    return g * x * np.minimum(1, t * 800) * .14

def tick(g=1.0):
    n = int(.025 * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n); nz = nz - onepole_lp(nz, 3500)
    return g * nz * np.exp(-t * 180) * .07

def thock(note, g=1.0):
    n = int(.5 * SR); t = np.arange(n) / SR
    f = midi(note) * (1 + .6 * np.exp(-t * 40)); ph = 2 * np.pi * np.cumsum(f) / SR
    return g * (np.sin(ph) * np.exp(-t * 10) * .6 + tick(1.6)[:n].sum() * 0)

def riser(length, g=1.0, f0=300, f1=3000):
    n = int(length * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    # crude moving band: mix of two lowpasses at fixed corners, crossfaded along time
    lo = onepole_lp(nz, f0); hi = onepole_lp(nz, f1) - onepole_lp(nz, f0 * 1.5)
    p = (t / length)
    x = lo * (1 - p) + hi * p
    tone = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (p * 2)) / SR) * .25
    return g * (x * .5 + tone) * p ** 2.4 * .3

def whoosh(length, g=1.0):
    n = int(length * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n); lo = onepole_lp(nz, 2600); bp = lo - onepole_lp(lo, 450)
    e = np.sin(np.pi * t / length) ** 2
    return g * bp * e * .28

def boom(g=1.0):
    n = int(2.6 * SR); t = np.arange(n) / SR
    f = 32 + 60 * np.exp(-t * 6); ph = 2 * np.pi * np.cumsum(f) / SR
    nz = rng.standard_normal(n); nz = onepole_lp(nz, 5000) * np.exp(-t * 3.5) * .18
    return g * (np.sin(ph) * np.exp(-t * 1.6) * .9 + nz)

def sub(note, length, g=1.0):
    n = int(length * SR); t = np.arange(n) / SR
    return g * np.sin(2 * np.pi * midi(note) * t) * env_adsr(n, .8, .2, .9, 1.0, length) * .22

# ---------- extra playful instruments ----------
def pop(note, g=1.0):
    n = int(.09 * SR); t = np.arange(n) / SR
    f = midi(note) * (0.6 + 0.8 * (1 - np.exp(-t * 60))); ph = 2 * np.pi * np.cumsum(f) / SR
    return g * np.sin(ph) * np.exp(-t * 38) * np.minimum(1, t * 900) * .32

def ding(note, g=1.0, length=1.2):
    n = int(length * SR); t = np.arange(n) / SR; f = midi(note)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 3) + .45 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 7) + .2 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 12)
    return g * x * np.minimum(1, t * 1500) * .16

def marimba(note, g=1.0):
    n = int(.4 * SR); t = np.arange(n) / SR; f = midi(note)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 9) + .3 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 30)
    return g * x * np.minimum(1, t * 1200) * .22

def stab(notes, g=1.0, length=.45):
    n = int(length * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for nt in notes:
        f = midi(nt)
        for det in (-.1, .1):
            ph = 2 * np.pi * f * 2 ** (det / 12) * t
            x += 2 / np.pi * np.arcsin(np.sin(ph)) * .6 + np.sign(np.sin(ph)) * .15   # tri + a little square
    return g * x / (2 * len(notes)) * np.exp(-t * 6) * np.minimum(1, t * 600) * .35

def click(g=1.0):
    n = int(.012 * SR); t = np.arange(n) / SR
    return g * np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 500) * .12

def snap(g=1.0):
    n = int(.08 * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n); nz = nz - onepole_lp(nz, 2500)
    return g * nz * np.exp(-t * 60) * .25

# ---------- stems ----------
drums = np.zeros(N); music = np.zeros(N); pads = np.zeros(N); sfx = np.zeros(N)
def beats(a, b, step=B):
    k0 = int(np.ceil(a / step - 1e-9)); k1 = int(np.floor((b - 1e-9) / step))
    return [k * step for k in range(k0, k1 + 1)]
E = B / 2   # eighth
C = (36, [60, 64, 67], [72, 76, 79, 84]); G = (43, [59, 62, 67], [71, 74, 79, 83]); Am = (45, [60, 64, 69], [72, 76, 81, 84]); F = (41, [60, 65, 69], [72, 77, 81, 84])
LOOP = [C, G, Am, F]

def groove(a, b, lvl=1.0, clapf=True, openhat=True, shaker=True):
    for t in beats(a, b):
        add(drums, kick(lvl), t)
        if clapf and round(t / B) % 2 == 1: add(drums, clap(.8 * lvl), t)
        if openhat: add(drums, hat(.3 * lvl, True), t + E)
    if shaker:
        for t in beats(a, b, S): add(drums, hat((.16 if round(t / S) % 2 else .1) * lvl), t)

def harmony(a, b, arp=True, bassg=1.0, padg=.8, arpg=.5, start_bar=0):
    for k, t0 in enumerate(beats(a, b, 4 * B)):
        ch = LOOP[(k + start_bar) % 4]; t1 = min(b, t0 + 4 * B)
        add(pads, pad(ch[1], t1 - t0 + .1, padg, att=.05, rel=.3), t0)
        # syncopated bass: 1, &2, 3, &4
        for off in (0, 1.5, 2, 3, 3.5):
            tt = t0 + off * B
            if tt < t1: add(music, bass(ch[0] + (12 if off in (1.5, 3.5) else 0), .22, bassg, .5), tt)
        if arp:
            for j, tt in enumerate(beats(t0, t1, E)):
                add(music, marimba(ch[2][[0, 1, 2, 1, 3, 2, 1, 2][j % 8]], arpg), tt)

# 0-4 hook: playful, light groove
harmony(0, 4, padg=.5, arpg=.45)
for t in beats(0, 4): add(drums, kick(.7), t)
for t in beats(0, 4, E): add(drums, hat(.14), t + S)
for i in range(12): add(sfx, pop([72, 76, 79, 84, 79, 76, 81, 84, 72, 79, 76, 84][i], .7), i * .25)
for i in range(8): add(sfx, click(1.0), .5 + i * .25)
for i in range(5): add(sfx, pop([84, 88, 91, 86, 89][i], .8), 2.0 + i * .25)
for t in (1.0, 3.0): add(drums, clap(.6), t)
# 4-8 the question: breakdown with snaps
add(pads, pad([57, 60, 64, 67], 4.0, .9, att=.4), 4.0)
for t in beats(4, 8, B): add(music, bass(45 if t < 6 else 43, .35, .8, .3), t)
for t in (4.5, 5.5, 6.5, 7.5): add(drums, snap(1.0), t)
add(sfx, pop(67, 1.0), 4.5); add(sfx, pop(91, .9), 5.25); add(sfx, ding(91, .6, .8), 5.25)
add(sfx, riser(1.5, .8, 300, 5000), 6.5)
for t in beats(7.0, 8.0, S): add(drums, snap(.3 + .5 * (t - 7)), t)
# 8-18 opportunity: full groove
groove(8, 17.65); harmony(8, 18)
for k in range(int(1.25 / S)): add(sfx, click(.9 + .3 * (k % 2)), 8.625 + k * S)          # typing
add(sfx, whoosh(.4, .5), 9.9)
add(sfx, pop(79, .8), 11.25); add(sfx, pop(72, .9), 11.75)
for k in range(3): add(sfx, pop([86, 88, 91][k], .7), 12.625 + k * .125)
add(sfx, ding(84, .5, .6), 13.0); add(sfx, ding(88, .55, .6), 13.625)
for k in range(3): add(sfx, ding([79, 84, 88][k], .45, .7), 14.75 + k * .25)
add(sfx, ding(96, .8, 1.2), 15.75)
add(sfx, whoosh(.4, .6), 17.5)
# 18-22 title slams
for i, t in enumerate((18.25, 18.75, 19.25)):
    add(music, stab([60, 64, 67, 72] if i < 2 else [65, 69, 72, 77], 1.1), t); add(drums, kick(1.1), t); add(drums, clap(.7), t)
for i, t in enumerate((18.25, 18.75, 19.25)): add(sfx, pop([67, 72, 79][i], .6), t + .05)
add(sfx, pop(84, .8), 19.5)
for t in beats(20, 21.65): add(drums, kick(.9), t)
for t in beats(20, 21.65, E): add(drums, hat(.25), t + S)
add(pads, pad([60, 65, 69, 72], 3.7, .8, att=.05), 18.25)
add(sfx, whoosh(.4, .6), 21.5)
# 22-30 promise + days
groove(22, 30); harmony(22, 30)
add(sfx, pop(76, 1.0), 24.0); add(sfx, pop(81, 1.0), 24.5)
for k in range(7): add(sfx, pop([84, 86, 88, 84, 86, 88, 91][k], .45), 24.25 + k * .125 + (0.5 if k >= 3 else 0))
for k in range(3): add(sfx, pop([88, 91, 96][k], .7), 26.0 + k * .25)
# 30-42 what they do
groove(30, 41.65); harmony(30, 42, arpg=.55)
for i in range(4): add(sfx, pop([72, 76, 79, 84][i], 1.0), 30.5 + i * 1.25)
for k in range(4): add(sfx, click(1.2), 31.0 + k * .125)
for k in range(6): add(sfx, ding([84, 86, 88, 91, 84, 93][k], .3, .4), 34.5 + k * .125)
for i in range(4): add(sfx, whoosh(.25, .35), 35.7 + i * .25)
for k in range(24): add(sfx, click(.8), 36.25 + k * .0625)
add(sfx, snap(1.2), 37.375)
for k in range(9): add(sfx, pop(72 + k, .3), 36.75 + k * .0625)
for k in range(6): add(sfx, pop(76 + 2 * k, .4), 37.0 + k * .125)
add(sfx, whoosh(.4, .6), 41.5)
# 42-46 instructor: breakdown, sparkle
add(pads, pad([57, 60, 64, 67, 71], 4.0, 1.2, att=.3, rel=.5), 42.0)
for t in beats(42, 45.65, 2 * B): add(drums, kick(.7), t)
for k, t in enumerate(beats(42, 45.65, E)): add(music, ding([84, 88, 91, 95, 91, 88][k % 6], .25, .5), t)
for t in beats(42, 45.65, B): add(music, bass(45, .4, .7, .2), t)
add(sfx, whoosh(.4, .6), 45.5)
# 46-50 punches
for i, t in enumerate((46.0, 46.5, 47.0)):
    add(music, stab([[60, 64, 67], [62, 67, 71], [64, 69, 72]][i], 1.1), t); add(drums, kick(1.0), t); add(drums, clap(.7), t)
groove(47.5, 50, .9); harmony(48, 50, start_bar=2)
# 50-54 deliverables + build
groove(50, 52, 1.0); harmony(50, 54, arpg=.45, start_bar=3)
for i in range(5): add(sfx, pop([72, 76, 79, 84, 88][i], 1.0), 50.5 + i * .5); add(sfx, click(1.2), 50.5 + i * .5)
for t in beats(52, 53.65, B): add(drums, kick(.9), t)
for t in beats(52, 53.65, S): add(drums, snap(.2 + .4 * (t - 52) / 1.65), t)
add(sfx, riser(2.0, 1.0, 250, 6000), 51.65)
# 54-61 final
for t in (54.0,):
    add(music, stab([60, 64, 67, 72, 76], 1.3, .8), t); add(drums, kick(1.3), t); add(drums, boom(.8), t)
groove(54, 58, 1.0); harmony(54, 58, arpg=.5)
for k, t in enumerate((54.0, 54.18, 54.36)): add(sfx, pop([67, 72, 79][k], .5), t)
for k in range(6): add(sfx, pop([72, 74, 76, 79, 81, 84][k], .35), 55.5 + k * .125)
add(sfx, click(2.0), 57.5); add(sfx, ding(91, .7, 1.0), 57.5)
add(music, stab([60, 64, 67, 72, 76], 1.2, 1.4), 58.0); add(drums, kick(1.1), 58.0)
add(pads, pad([48, 60, 64, 67, 71, 74], 3.0, 1.5, att=.02, rel=1.5), 58.0)
add(music, ding(84, .8, 2.5), 58.0); add(music, bass(36, 2.5, .9, .1), 58.0)

# ---------- mix ----------
irn = int(1.2 * SR); ti = np.arange(irn) / SR
ir = rng.standard_normal(irn) * np.exp(-ti * 4.0); ir = onepole_lp(ir, 6000); ir /= np.sqrt((ir ** 2).sum())
wet = fft_conv(pads * .4 + sfx * .35 + music * .25, ir) * .25
duck = np.ones(N)
for t in [x for x in beats(0, 61) if True]:
    i = int(t * SR); n = int(.18 * SR); duck[i:i + n] = np.minimum(duck[i:i + n], .62 + .38 * np.linspace(0, 1, n) ** .7)
mix = drums * .8 + (music * .75 + pads * .8 + wet) * duck + sfx * .7
fo = np.ones(N); fo[:200] = np.linspace(0, 1, 200); m = int(.3 * SR); fo[-m:] = np.linspace(1, 0, m)
mix *= fo
mix = np.tanh(mix * 1.25) / np.tanh(1.25)
mix *= 10 ** (-1 / 20) / np.max(np.abs(mix))
st = np.stack([mix + wet * .05 * fo, mix - wet * .05 * fo], 1)
st = np.clip(st, -1, 1)
with wave.open('music_workshop.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype('<i2').tobytes())
print('ok', N / SR)
