"""Score + VO mix for the university film: 120 BPM, C major, VO-ducked."""

import numpy as np, wave

SR = 44100
DUR = 64.0
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

import soundfile as sf
# ---------- extra sounds ----------
def boing(note, g=1.0):
    n = int(.35 * SR); t = np.arange(n) / SR; f = midi(note) * (1 + .5 * np.exp(-t * 12) * np.sin(2 * np.pi * 14 * t))
    return g * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * .22
def thunk(note, g=1.0):
    n = int(.25 * SR); t = np.arange(n) / SR; f = midi(note) * (1 + 1.5 * np.exp(-t * 50))
    return g * (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18) * .5 + click(1.0)[:n].sum() * 0)
def whir(length, g=1.0):
    n = int(length * SR); t = np.arange(n) / SR; f = 300 + 500 * (t / length)
    return g * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / length) ** 2 * (0.6 + .4 * np.sin(2 * np.pi * 30 * t)) * .05
def signature(t, g=1.0):   # rising three-note chime: G5 C6 E6
    for k, nt in enumerate((79, 84, 88)): add(sfx, ding(nt, g * (.8 + .1 * k), 2.2), t + k * .125)

drums = np.zeros(N); music = np.zeros(N); pads = np.zeros(N); sfx = np.zeros(N)
def beats(a, b, step=B):
    k0 = int(np.ceil(a / step - 1e-9)); k1 = int(np.floor((b - 1e-9) / step))
    return [k * step for k in range(k0, k1 + 1)]
E = B / 2
C_ = (36, [60, 64, 67], [72, 76, 79, 84]); G_ = (43, [59, 62, 67], [71, 74, 79, 83]); Am = (45, [60, 64, 69], [72, 76, 81, 84]); F_ = (41, [60, 65, 69], [72, 77, 81, 84])
LOOP = [C_, G_, Am, F_]
def groove(a, b, lvl=1.0, clapf=True, openhat=True, shaker=True):
    for t in beats(a, b):
        add(drums, kick(lvl), t)
        if clapf and round(t / B) % 2 == 1: add(drums, clap(.75 * lvl), t)
        if openhat: add(drums, hat(.26 * lvl, True), t + E)
    if shaker:
        for t in beats(a, b, S): add(drums, hat((.14 if round(t / S) % 2 else .08) * lvl), t)
def harmony(a, b, arp=True, bassg=.9, padg=.75, arpg=.42, sb=0):
    for k, t0 in enumerate(beats(a, b, 4 * B)):
        ch = LOOP[(k + sb) % 4]; t1 = min(b, t0 + 4 * B)
        add(pads, pad(ch[1], t1 - t0 + .1, padg, att=.05, rel=.3), t0)
        for off in (0, 1.5, 2, 3, 3.5):
            tt = t0 + off * B
            if tt < t1: add(music, bass(ch[0] + (12 if off in (1.5, 3.5) else 0), .22, bassg, .5), tt)
        if arp:
            for j, tt in enumerate(beats(t0, t1, E)): add(music, marimba(ch[2][[0, 1, 2, 1, 3, 2, 1, 2][j % 8]], arpg), tt)

# 0-8 hook
harmony(0, 8, padg=.55, arpg=.35)
for t in beats(0, 4): add(drums, kick(.6), t)
for t in beats(0, 4, E): add(drums, hat(.12), t + S)
groove(4, 7.75, .85)
for i in range(10): add(sfx, pop([72, 76, 79, 84, 79, 76, 81, 84, 72, 79][i], .65), .25 + i * .25)
add(sfx, pop(67, 1.0), 1.0); add(sfx, boing(72, .7), 1.0); add(sfx, whir(1.2, .9), 1.1)
add(sfx, ding(88, .4, .6), 5.5); add(sfx, whoosh(.3, .5), 7.7)
# 8-19.5 opportunity
groove(8, 19.25); harmony(8, 19.5)
for i in range(4): add(sfx, thunk(48 + i * 4, .9), 8.5 + i * .5)
for i, t in enumerate((10.9, 11.9, 12.9, 13.9)): add(sfx, boing(67 + i * 3, .6), t)
for i in range(2): add(sfx, pop(86 + i * 3, .8), 14.625 + i * .25)
add(sfx, click(1.2), 15.0); signature(16.75, .45)
add(sfx, whoosh(.3, .5), 19.2)
# 19.5-30.75 instructor
harmony(19.5, 30.5, sb=2, padg=.9, arpg=.35); groove(20, 30.5, .9)
for k, t in enumerate(beats(20, 26.5, E)): add(music, ding([88, 91, 93, 96][k % 4], .12, .4), t)
add(sfx, whoosh(.6, .6), 26.5)
for k in range(12): add(sfx, click(.8), 26.625 + k * .0625)
add(sfx, thunk(40, .9), 27.25)
add(sfx, whoosh(.3, .5), 30.5)
# 30.75-33.5 title
add(music, stab([60, 64, 67, 72], 1.2, .6), 31.0); add(drums, kick(1.2), 31.0); add(drums, boom(.6), 31.0)
add(music, stab([65, 69, 72, 77], 1.2, .6), 31.5); add(drums, kick(1.1), 31.5); add(drums, clap(.8), 31.5)
signature(31.5, .6); add(sfx, boing(74, .6), 31.5)
for t in beats(32, 33.5): add(drums, kick(.9), t)
for t in beats(32, 33.5, E): add(drums, hat(.22), t + S)
add(pads, pad([60, 64, 67, 72], 2.6, .8, att=.02), 31.0)
# 33.5-42.25 SoukGo
groove(33.5, 42.0); harmony(34, 42.25, arpg=.4)
for i in range(4): add(sfx, pop(84 + i * 2, .6), 34.0 + i * .25)
add(sfx, pop(76, .7), 34.25)
for t in (37.375, 38.375, 39.25): add(sfx, click(1.4), t); add(sfx, ding(84, .35, .5), t)
add(sfx, click(1.6), 40.875); add(sfx, ding(91, .55, 1.0), 41.0); add(sfx, pop(79, .6), 41.375)
add(sfx, whoosh(.3, .5), 42.0)
# 42.25-46 escalation
groove(42.25, 45.75, .8, clapf=False); harmony(42.25, 46, arpg=.3, sb=3)
add(sfx, thunk(36, 1.0), 42.375); add(sfx, pop(72, .6), 42.625)
add(sfx, thunk(52, .9), 43.375); add(sfx, boing(60, .6), 43.375)
add(sfx, whoosh(.5, .5), 44.0); signature(44.625, .4)
add(sfx, whoosh(.3, .5), 45.75)
# 46-54 achievement
groove(46, 53.75); harmony(46, 54, arpg=.45)
for i in range(5): add(sfx, pop([72, 76, 79, 84, 88][i], .9), 46.5 + i * .5); add(sfx, thunk(48 + i * 2, .5), 46.5 + i * .5)
for t in (46.625, 48.375, 49.375): add(sfx, click(1.2), t)
add(pads, pad([60, 64, 67, 71, 74], 2.8, 1.0, att=.6), 51.25)
for k in range(5): add(sfx, boing(79 + (k % 2) * 5, .35), 51.25 + k * .5)
add(sfx, riser(1.5, .7, 300, 5000), 52.4); add(sfx, whoosh(.3, .5), 53.75)
# 54-64 final
add(music, stab([60, 64, 67, 72, 76], 1.2, .8), 54.0); add(drums, kick(1.2), 54.0); add(drums, boom(.6), 54.0)
groove(54, 58.5); harmony(54, 58.75, arpg=.4)
for i in range(4): add(sfx, pop([72, 79, 84, 88][i], .4), 54.25 + i * .15)
add(sfx, click(2.0), 58.75); signature(58.75, .9)
add(music, stab([60, 64, 67, 72, 76], 1.0, 1.6), 58.75); add(drums, kick(1.0), 58.75)
add(pads, pad([48, 60, 64, 67, 71, 74], 4.5, 1.4, att=.02, rel=2.0), 58.75); add(music, bass(36, 3.0, .8, .1), 58.75)

# ---------- VO ----------
PLACE = [.5, 3.0, 5.5, 8.0, 16.75, 19.75, 26.5, 31.0, 33.75, 37.25, 46.0, 51.25, 54.5, 57.25]
vo = np.zeros(N)
for i, t in enumerate(PLACE, 1):
    x, sr = sf.read(f'vo/t{i:02d}.wav'); assert sr == 24000
    x = np.interp(np.arange(0, len(x) * SR / sr) * sr / SR, np.arange(len(x)), x)   # resample to 44.1k
    add(vo, x, t)
vo = vo - onepole_lp(vo, 80)
act = np.abs(vo) > 1e-3; vo *= 10 ** (-12 / 20) / np.sqrt(np.mean(vo[act] ** 2))
env = np.convolve(np.abs(vo), np.ones(2205) / 2205, 'same'); gate = (env > .008).astype(float)
k = int(.15 * SR); att = np.convolve(gate, np.ones(k) / k, 'same'); vduck = 1 - (1 - 10 ** (-9 / 20)) * np.clip(att * 1.5, 0, 1)

# ---------- mix ----------
irn = int(1.2 * SR); ti = np.arange(irn) / SR
ir = rng.standard_normal(irn) * np.exp(-ti * 4.0); ir = onepole_lp(ir, 6000); ir /= np.sqrt((ir ** 2).sum())
wet = fft_conv(pads * .4 + sfx * .35 + music * .25, ir) * .25
duck = np.ones(N)
for t in beats(0, 64):
    i = int(t * SR); n = int(.18 * SR); duck[i:i + n] = np.minimum(duck[i:i + n], .65 + .35 * np.linspace(0, 1, n) ** .7)
bed = (drums * .75 + (music * .7 + pads * .75 + wet) * duck + sfx * .65) * vduck
mix = bed * .8 + vo
mix[:200] *= np.linspace(0, 1, 200); m = int(1.0 * SR); mix[-m:] *= np.linspace(1, 0, m) ** 1.5
mix = np.tanh(mix * 1.2) / np.tanh(1.2); mix *= 10 ** (-1 / 20) / np.max(np.abs(mix))
st = np.clip(np.stack([mix + wet * .04, mix - wet * .04], 1), -1, 1)
with wave.open('music_uni.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype('<i2').tobytes())
print('ok')
