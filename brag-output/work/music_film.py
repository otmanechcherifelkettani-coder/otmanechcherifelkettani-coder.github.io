"""Score for the Cadence Academy brand film: 96 BPM (beat .625 s, bar 2.5 s), A minor -> C major.
Every hit sits on the beat grid counted from t=0. Hard stop to silence at 14.375 s."""
import numpy as np, wave

SR = 44100
DUR = 60.0
N = int(SR * DUR)
B = 0.625          # beat
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

# ---------- stems ----------
drums = np.zeros(N); music = np.zeros(N); pads = np.zeros(N); sfx = np.zeros(N); post = np.zeros(N)
def beats(a, b, step=B):
    k0 = int(np.ceil(a / step - 1e-9)); k1 = int(np.floor((b - 1e-9) / step))
    return [k * step for k in range(k0, k1 + 1)]

# chords (bass root, pad voicing, arp)
Am = (45, [57, 60, 64], [69, 72, 76, 81]); F = (41, [57, 60, 65], [69, 72, 77, 81]); C = (48, [55, 60, 64], [67, 72, 76, 79])
G = (43, [55, 59, 62], [67, 71, 74, 79]); Dm = (50, [57, 62, 65], [69, 74, 77, 81])

# --- 0-2.5 intro: drone + clock
pads[:] += 0
add(pads, sub(33, 8.0, .9), 0.0)                                # A1 drone through the noise
for t in beats(0.3125, 2.5, B / 2): add(sfx, tick(.6), t)
add(sfx, blip(69, .35), .45)

# --- 2.5-5.6 buzzwords
for k, nt in enumerate([69, 72, 76, 79, 81]):
    t = 2.5 + k * B
    add(sfx, thock(45, .9), t); add(sfx, blip(nt, .55), t)
for t in beats(2.5, 5.625): add(drums, kick(.55), t)
for t in beats(2.5, 5.625, B / 2): add(drums, hat(.35), t + B / 4)
for i in range(12): add(sfx, tick(.5), 2.6 + i * .2)

# --- 5.6-8.4 arp builds
add(pads, pad(Am[1], 3.2, .8), 5.625)
for k, t in enumerate(beats(5.625, 8.4375, S)):
    add(music, pluck(Am[2][k % 4], .25 + .35 * (t - 5.6) / 2.8, bright=.6 + .6 * (t - 5.6) / 2.8), t)
for t in beats(5.625, 8.4375): add(drums, kick(.8), t)
for t in beats(5.625, 8.4375, B / 2): add(drums, hat(.4), t + B / 4)
add(sfx, whoosh(.6, .5), 7.85)

# --- 8.4375-14.375 chaos
CH = [(8.4375, Am), (10.0, (46, [58, 61, 64], [70, 73, 76, 82])), (11.25, Am), (12.5, (46, [58, 61, 63], [70, 73, 75, 82]))]
for i, (a, ch) in enumerate(CH):
    b = CH[i + 1][0] if i + 1 < len(CH) else 14.375
    add(pads, pad(ch[1] + [ch[1][0] + 1], b - a + .2, 1.0 + .3 * i), a)
    for t in beats(a, b, B / 2): add(music, bass(ch[0], .14, 1.0), t); add(music, bass(ch[0] + 12, .1, .6), t + B / 4)
for k, t in enumerate(beats(8.4375, 14.375, S)):
    nt = [69, 72, 76, 70, 81, 75][k % 6] + (12 if k % 7 == 6 else 0)        # 6-note cycle against 4/4 -> drift
    add(music, pluck(nt, .45 + .25 * (t - 8.4) / 6, bright=1.4), t)
for t in beats(8.4375, 14.375):
    add(drums, kick(1.0), t)
    if round(t / B) % 2 == 1: add(drums, clap(.9), t)
for t in beats(8.4375, 14.375, S): add(drums, hat(.28 + .1 * ((round(t / S)) % 2 == 0)), t)
# glitch stutters on a 32nd grid
for t0 in (11.875, 12.8125, 13.4375, 13.75, 14.0625):
    for k in range(6): add(sfx, tick(1.2), t0 + k * S / 2)
for i in range(16): add(sfx, blip([82, 75, 70, 81][i % 4], .28), 10.9 + i * .2)   # fragment pops (visual cues)
add(sfx, riser(3.2, 1.1), 14.375 - 3.2)
add(drums, clap(.0), 0)

# --- silence 14.375-17.5: one breath note on the line
add(post, keys([45, 57, 64], .55, 3.0), 14.95)

# --- 17.5-19.4 snap to grid
add(pads, pad(C[1], 2.6, .7, att=.6), 17.5)
for k, t in enumerate(beats(17.6875, 18.5, S / 2)): add(sfx, tick(.9 - .04 * k), t)
add(sfx, thock(36, .6), 18.4375)

# --- 19.4-30 pipeline + headlines
PROG2 = [(17.5, F), (20.0, C), (22.5, Am), (25.0, G), (27.5, F)]
for i, (a, ch) in enumerate(PROG2):
    b = PROG2[i + 1][0] if i + 1 < len(PROG2) else 30.0
    if a >= 20: add(pads, pad(ch[1], b - a + .3, .9), a)
    if a >= 20:
        for t in beats(a, b, B / 2): add(music, bass(ch[0], .16, .8, .2), t)
    for k, t in enumerate(beats(max(a, 19.375), b, B / 2)): add(music, pluck(ch[2][k % 4], .4, bright=.8), t)
for k, nt in enumerate([72, 74, 76, 79, 81]): add(sfx, blip(nt, .7), 19.375 + k * B)     # pipeline nodes
for t in beats(20.0, 29.375): add(drums, kick(.7 if t < 22.5 else .85), t)
for t in beats(22.5, 29.375, B / 2): add(drums, hat(.35), t + B / 4)
for t in beats(25.0, 29.375):
    if round(t / B) % 2 == 1: add(drums, clap(.55), t)
add(sfx, blip(84, .35), 23.75); add(sfx, blip(88, .45), 26.25)
add(pads, pad([65, 69, 72, 76], 3.0, .8, att=.4), 26.25)
add(sfx, whoosh(.5, .45), 26.85)
for k in range(5): add(drums, clap(.25 + .12 * k), 29.375 + k * S)
add(sfx, riser(1.0, .7), 29.0)

# --- 30-42.5 method groove
PROG3 = [(30.0, C), (32.5, G), (35.0, Am), (37.5, F), (40.0, G)]
for i, (a, ch) in enumerate(PROG3):
    b = PROG3[i + 1][0] if i + 1 < len(PROG3) else 42.5
    add(pads, pad(ch[1], b - a + .3, 1.0), a)
    for t in beats(a, b, B / 2): add(music, bass(ch[0], .2, 1.0), t); add(music, bass(ch[0] + 12, .12, .5), t + B / 4)
    for k, t in enumerate(beats(a, b, S)): add(music, pluck(ch[2][k % 4] + (12 if k % 8 == 7 else 0), .42, bright=1.0), t)
    add(sfx, whoosh(.35, .5), a - .3); add(sfx, blip(ch[2][-1] + 12, .55), a)
for t in beats(30.0, 42.5):
    add(drums, kick(1.0), t)
    if round(t / B) % 2 == 1: add(drums, clap(.85), t)
for t in beats(30.0, 42.5, S): add(drums, hat(.3 if round(t / S) % 2 else .2), t)
for t in beats(30.0, 42.5, B): add(drums, hat(.25, True), t + B / 2)
# in-panel cues (soft, under the music, quantized to sixteenths)
q = lambda x: round(x / S) * S
for i in range(5): add(sfx, tick(1.0), q(32.5 + .45 + i * .09))
for i in range(3): add(sfx, blip(70, .3), q(32.5 + .95 + i * .08))
for t in (35.0 + .55, 35.0 + .95, 35.0 + 1.35): add(sfx, blip(84, .35), q(t))
for i in range(12): add(sfx, blip([79, 81, 84, 86][i % 4], .22), q(37.5 + .4 + i * .075))
for i in range(7): add(sfx, blip([67, 69, 72, 74, 76, 79, 81][i], .32), q(40.0 + .15 + i * .1))

# --- 42.5-50 principle: half-time, a chord per line
PROG4 = [(42.5, F, [53, 57, 60, 64]), (44.375, G, [55, 59, 62, 67]), (46.25, Am, [57, 60, 64, 69]), (48.125, F, [53, 57, 60, 67])]
for i, (a, ch, kv) in enumerate(PROG4):
    b = PROG4[i + 1][0] if i + 1 < len(PROG4) else 50.0
    add(pads, pad(ch[1] + [ch[1][0] + 12], b - a + .4, 1.15), a)
    if i < 3: add(music, keys(kv, .9, 2.4), a)
    for t in beats(a, b, B): add(music, bass(ch[0], .5, .8, .15), t)
    for k, t in enumerate(beats(a, b, B / 2)): add(music, pluck(ch[2][k % 4], .28, bright=.7), t)
for t in beats(42.5, 50.0, 2 * B): add(drums, kick(.75), t)
for t in beats(42.5, 50.0, B / 2): add(drums, hat(.22), t + B / 4)

# --- 50-52.5 thesis line 1: drums out, riser
add(pads, pad([55, 60, 62, 67], 2.8, 1.0, att=.2), 50.0)
add(music, keys([43, 55, 62], .7, 2.4), 50.0)
add(sfx, riser(2.5, 1.3, 200, 4000), 50.0)

# --- 52.5 impact "Shipping it is."
add(drums, boom(1.1), 52.5); add(drums, kick(1.2), 52.5)
add(pads, pad([48, 55, 60, 64, 67, 72], 3.4, 1.7, att=.02, rel=1.0), 52.5)
add(music, keys([48, 60, 64, 67, 72], 1.0, 3.0), 52.5)
for t in beats(53.75, 55.3): add(drums, kick(.6), t)
for t in beats(53.75, 55.3, B / 2): add(drums, hat(.22), t + B / 4)
add(sfx, whoosh(.6, .45), 54.9)

# --- 55.3-60 end card
add(pads, pad([48, 55, 62, 64, 67, 71], 4.9, 1.5, att=.3, rel=1.6), 55.0)
add(music, bass(36, 4.5, .9, .1), 55.0)
for k, nt in enumerate([72, 76, 79, 83, 84]): add(sfx, blip(nt, .5), 55.625 + k * B / 2)     # end-card dots
for k, t in enumerate(beats(55.0, 58.75, B / 2)): add(music, pluck([67, 72, 76, 79][k % 4], .25 * (1 - (t - 55) / 4.2), bright=.6), t)
for t in beats(55.0, 57.5): add(drums, kick(.45), t)

# ---------- mix ----------
irn = int(1.8 * SR); ti = np.arange(irn) / SR
ir = rng.standard_normal(irn) * np.exp(-ti * 2.8); ir = onepole_lp(ir, 5200); ir /= np.sqrt((ir ** 2).sum())
wet = fft_conv(pads * .5 + sfx * .45 + music * .3, ir) * .32

duck = np.ones(N)
def kick_times():
    ts = beats(8.4375, 14.375) + beats(30.0, 42.5) + beats(25.0, 29.375)
    return ts
for t in kick_times():
    i = int(t * SR); n = int(.24 * SR); duck[i:i + n] = np.minimum(duck[i:i + n], .5 + .5 * np.linspace(0, 1, n) ** .7)

mix = drums * .85 + (music * .8 + pads + wet) * duck + sfx * .65
# the hard stop: kill everything 14.375 -> 17.5 (short 6 ms ramp to avoid a click)
a, b = int(14.375 * SR), int(17.5 * SR); r = int(.006 * SR)
mix[a - r:a] *= np.linspace(1, 0, r); mix[a:b] = 0
fi = int(.25 * SR); mix[b:b + fi] *= np.linspace(0, 1, fi)
# breath note + its own reverb in the silence
pw = post + fft_conv(post, ir) * .5
mix += pw
fo = np.ones(N); m = int(1.4 * SR); fo[-m:] = np.linspace(1, 0, m) ** 1.6; fo[:300] = np.linspace(0, 1, 300)
mix *= fo
mix = np.tanh(mix * 1.3) / np.tanh(1.3)
mix *= 10 ** (-1 / 20) / np.max(np.abs(mix))
st = np.stack([mix, mix], 1)
st[:, 0] += wet * .06 * fo; st[:, 1] -= wet * .06 * fo
st[a:b] = np.stack([mix[a:b], mix[a:b]], 1)
st = np.clip(st, -1, 1)
with wave.open('music_film.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype('<i2').tobytes())
print('ok', N / SR)
