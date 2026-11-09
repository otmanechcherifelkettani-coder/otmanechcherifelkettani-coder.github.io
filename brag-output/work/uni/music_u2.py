"""Score + VO mix for the v2 university film (airy launch-film style): 120 BPM, C major."""

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
E = B / 2; q = lambda x: round(x / S) * S
Cm = (36, [60, 64, 67, 71], [72, 76, 79, 83]); Am = (45, [60, 64, 67, 69], [72, 76, 79, 81]); Fm = (41, [60, 64, 65, 69], [72, 77, 81, 84]); Gm = (43, [59, 62, 67, 69], [71, 74, 79, 81])
LOOP = [Fm, Cm, Am, Gm]
def harm(a, b, arp=.3, padg=.8, bassg=.6, sb=0, step=E):
    for k, t0 in enumerate(beats(a, b, 4 * B)):
        ch = LOOP[(k + sb) % 4]; t1 = min(b, t0 + 4 * B)
        add(pads, pad(ch[1], t1 - t0 + .2, padg, att=.3, rel=.5), t0)
        if bassg:
            for off in (0, 1.5, 2.5): 
                if t0 + off * B < t1: add(music, bass(ch[0], .3, bassg, .2), t0 + off * B)
        if arp:
            for j, tt in enumerate(beats(t0, t1, step)): add(music, pluck(ch[2][[0, 2, 1, 3, 2, 1, 3, 2][j % 8]], arp, .5, bright=.7), tt)
def kit(a, b, lvl=.8, clapf=True, shaker=True):
    for t in beats(a, b):
        add(drums, kick(lvl), t)
        if clapf and round(t / B) % 2 == 1: add(drums, clap(.55 * lvl), t)
    if shaker:
        for t in beats(a, b, S): add(drums, hat((.11 if round(t / S) % 2 else .06) * lvl), t)
    for t in beats(a, b, B): add(drums, hat(.16 * lvl, True), t + E)
# S1 0-12
add(pads, pad([60, 64, 67, 71, 74], 3.0, 1.0, att=1.2, rel=.6), 0.0); add(music, ding(84, .35, 1.5), .25)
for t in beats(.5, 3.0, E): add(sfx, tick(.5), t)
harm(3.0, 12.0, arp=.28); kit(3.0, 11.75, .7)
for i, t in enumerate((3.0, 5.0, 7.0)): add(sfx, whoosh(.45, .45), t - .25); add(sfx, pop([79, 83, 86][i], .5), t + .25); add(sfx, click(1.0), t + .5)
add(sfx, whoosh(.5, .45), 9.05); add(music, ding(88, .35, 1.2), 9.5)
# S2 12-20
harm(12.0, 20.0, arp=.24, sb=1); kit(13.0, 19.75, .6, clapf=False)
add(sfx, whoosh(.5, .4), 11.85); add(music, ding(76, .3, 1.0), 12.5)
for i in range(3): add(sfx, pop(84 + 2 * i, .35), q(13.2 + i * .35))
add(sfx, whoosh(.4, .45), 16.5); add(music, stab([60, 64, 67, 72], .6, .5), 16.75); add(sfx, ding(91, .4, 1.0), 16.75); add(sfx, pop(79, .5), 17.125)
# S3 20-31.5 deep
add(sfx, whoosh(.6, .5), 19.75)
add(pads, pad([48, 55, 60, 64, 67, 71], 3.0, 1.3, att=.05, rel=1.0), 20.5); add(music, stab([60, 64, 67, 71, 76], .8, 1.0), 20.5); add(drums, boom(.45), 20.5); signature(20.5, .45)
harm(23.0, 31.5, arp=.26, sb=2); kit(23.0, 31.25, .7)
for i in range(2): add(sfx, pop([84, 88][i], .55), 23.25 + i * .625)
add(sfx, ding(86, .35, .8), 26.625); add(sfx, click(1.0), 27.375)
# S4 31.5-44 drive
add(sfx, whoosh(.5, .45), 31.25)
harm(31.5, 44.0, arp=.34, sb=0, bassg=.75, step=S * 2); kit(31.5, 43.75, .9)
for t in (31.75, 34.625, 36.125, 37.375, 38.875, 40.375): add(sfx, click(1.4), t); add(sfx, whoosh(.25, .3), t - .2)
for i in range(4): add(sfx, click(1.1), q(36.5 + i * .12))
for i in range(5): add(sfx, pop(86, .25), q(37.6 + i * .18))
for k in range(24): add(sfx, tick(.6), q(39.3 + k * .045))
for i in range(7): add(sfx, pop(72 + [0, 2, 4, 7, 9, 12, 14][i], .35), q(40.5 + i * .15))
# S5 44-52.5
harm(44.0, 52.5, arp=.3, sb=1); kit(44.0, 52.25, .8)
for i in range(4): add(sfx, pop([76, 79, 83, 86][i], .55), q(44.4 + i * .55))
for i, t in enumerate((48.625, 49.125, 49.75)): add(music, stab([[60, 64, 67], [62, 65, 69], [64, 67, 71]][i], .55, .5), t); add(sfx, whoosh(.25, .3), t - .2)
# S6 52.5-64
add(sfx, whoosh(.5, .45), 52.25)
add(pads, pad([57, 60, 64, 67], 4.2, 1.0, att=.6), 52.5)
for t in beats(52.5, 56.5, 2 * B): add(drums, kick(.5), t)
add(music, stab([60, 64, 67, 71, 74], .9, 1.2), 56.75); add(drums, boom(.5), 56.75); signature(56.75, .5)
kit(56.75, 58.75, .75, clapf=False); harm(56.75, 58.75, arp=.28)
add(sfx, click(2.0), 58.75); signature(58.75, .7)
add(pads, pad([48, 60, 64, 67, 71, 74], 4.8, 1.3, att=.05, rel=2.0), 58.75); add(music, bass(36, 3.0, .6, .1), 58.75)
# ---------- VO + mix ----------
PLACE = [.5, 4.75, 9.5, 12.25, 16.75, 20.25, 23.0, 31.75, 44.25, 52.75, 54.75, 56.75]
vo = np.zeros(N)
for i, t in enumerate(PLACE, 1):
    x, sr = sf.read(f'vo2/l{i:02d}.wav'); x = np.interp(np.arange(0, len(x) * SR / sr) * sr / SR, np.arange(len(x)), x); add(vo, x, t)
vo = vo - onepole_lp(vo, 80); act = np.abs(vo) > 1e-3; vo *= 10 ** (-12 / 20) / np.sqrt(np.mean(vo[act] ** 2))
env = np.convolve(np.abs(vo), np.ones(2205) / 2205, 'same'); gate = (env > .008).astype(float)
k = int(.15 * SR); att = np.convolve(gate, np.ones(k) / k, 'same'); vduck = 1 - (1 - 10 ** (-9 / 20)) * np.clip(att * 1.5, 0, 1)
irn = int(1.6 * SR); ti = np.arange(irn) / SR
ir = rng.standard_normal(irn) * np.exp(-ti * 3.0); ir = onepole_lp(ir, 6000); ir /= np.sqrt((ir ** 2).sum())
wet = fft_conv(pads * .45 + sfx * .4 + music * .35, ir) * .3
duck = np.ones(N)
for t in beats(3, 64):
    i = int(t * SR); n = int(.18 * SR); duck[i:i + n] = np.minimum(duck[i:i + n], .7 + .3 * np.linspace(0, 1, n) ** .7)
bed = (drums * .7 + (music * .7 + pads * .8 + wet) * duck + sfx * .6) * vduck
mix = bed * .8 + vo
mix[:200] *= np.linspace(0, 1, 200); m = int(1.0 * SR); mix[-m:] *= np.linspace(1, 0, m) ** 1.5
mix = np.tanh(mix * 1.2) / np.tanh(1.2); mix *= 10 ** (-1 / 20) / np.max(np.abs(mix))
st = np.clip(np.stack([mix + wet * .04, mix - wet * .04], 1), -1, 1)
with wave.open('music_u2.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype('<i2').tobytes())
print('ok')
