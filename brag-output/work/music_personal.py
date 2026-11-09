"""Score for the personal AI-strategy film: 96 BPM (beat .625 s, bar 2.5 s), A minor -> C major.
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
q = lambda x: round(x / S) * S
Am = (45, [57, 60, 64], [69, 72, 76, 81]); F = (41, [57, 60, 65], [69, 72, 77, 81]); C = (48, [55, 60, 64], [67, 72, 76, 79])
G = (43, [55, 59, 62], [67, 71, 74, 79])

def groove(a, b, full=True, clapf=True):
    for t in beats(a, b):
        add(drums, kick(1.0 if full else .75), t)
        if clapf and round(t / B) % 2 == 1: add(drums, clap(.85 if full else .55), t)
    for t in beats(a, b, S if full else B / 2): add(drums, hat((.3 if round(t / S) % 2 else .2) if full else .32), t + (0 if full else B / 4))

def chords(prog, end, arp_step=S, arp_g=.42, bass_g=1.0, pad_g=1.0):
    for i, (a, ch) in enumerate(prog):
        b = prog[i + 1][0] if i + 1 < len(prog) else end
        add(pads, pad(ch[1], b - a + .3, pad_g), a)
        for t in beats(a, b, B / 2): add(music, bass(ch[0], .2, bass_g), t); add(music, bass(ch[0] + 12, .12, bass_g * .5), t + B / 4)
        if arp_g: 
            for k, t in enumerate(beats(a, b, arp_step)): add(music, pluck(ch[2][k % 4] + (12 if k % 8 == 7 else 0), arp_g, bright=1.0), t)

# 01 OPPORTUNITY (0-9.375)
add(pads, sub(33, 9.6, .9), 0.0)
for t in beats(0.3125, 2.5, B / 2): add(sfx, tick(.6), t)
add(sfx, blip(69, .35), .45)
for k, nt in enumerate([69, 72, 76, 81]):
    t = 2.5 + k * B; add(sfx, thock(45, .9), t); add(sfx, blip(nt, .55), t)
for t in beats(2.5, 5.625): add(drums, kick(.55), t)
for t in beats(2.5, 5.625, B / 2): add(drums, hat(.35), t + B / 4)
add(pads, pad(Am[1], 4.0, .8), 5.625)
for k, t in enumerate(beats(5.625, 9.375, S)):
    add(music, pluck(Am[2][k % 4], .25 + .3 * (t - 5.6) / 3.8, bright=.6 + .5 * (t - 5.6) / 3.8), t)
for t in beats(5.625, 9.375): add(drums, kick(.7), t)
for t in beats(5.625, 9.375, B / 2): add(drums, hat(.38), t + B / 4)
add(sfx, whoosh(.6, .5), 8.8)

# 02 EXPERIENCE (9.375-25): confident, warm
add(pads, pad(F[1], 1.0, .7), 9.375)
chords([(10.0, F), (12.5, C), (15.0, Am), (17.5, G), (20.0, F), (22.5, G)], 25.0, arp_step=B / 2, arp_g=.38, bass_g=.85, pad_g=.95)
groove(10.0, 15.0, full=False, clapf=False); groove(15.0, 24.6875, full=False)
for k in range(3): add(sfx, blip([72, 76, 79][k], .45), q(9.7 + k * .3))
add(sfx, blip(84, .55), 11.0)
add(sfx, whoosh(.5, .45), 14.0); add(sfx, thock(40, .6), 14.375)
for k in range(8): add(sfx, blip([79, 83, 86, 88][k % 4], .25), q(15.0 + k * .18))
for k in range(4): add(sfx, blip([72, 74, 76, 79][k], .45), q(20.5 + k * .35))
for t in (20.7, 21.05, 21.4): add(sfx, tick(1.0), q(t))
add(sfx, blip(84, .5), q(24.1))
add(sfx, riser(1.2, .5), 23.8)

# 03 CHALLENGE (25-32.5) then hard stop
CH = [(25.0, Am), (27.5, (46, [58, 61, 64], [70, 73, 76, 82])), (30.0, (46, [58, 61, 63], [70, 73, 75, 82]))]
for i, (a, ch) in enumerate(CH):
    b = CH[i + 1][0] if i + 1 < len(CH) else 32.5
    add(pads, pad(ch[1] + [ch[1][0] + 1], b - a + .2, 1.0 + .3 * i), a)
    for t in beats(a, b, B / 2): add(music, bass(ch[0], .14, 1.0), t); add(music, bass(ch[0] + 12, .1, .6), t + B / 4)
for k, t in enumerate(beats(25.0, 32.5, S)):
    add(music, pluck([69, 72, 76, 70, 81, 75][k % 6] + (12 if k % 7 == 6 else 0), .38 + .3 * (t - 25) / 7.5, bright=1.4), t)
for t in beats(25.0, 32.5):
    add(drums, kick(1.0), t)
    if round(t / B) % 2 == 1 and t >= 26.25: add(drums, clap(.9), t)
for t in beats(26.25, 32.5, S): add(drums, hat(.28 + .1 * ((round(t / S)) % 2 == 0)), t)
for t0 in (29.375, 30.3125, 31.25, 31.5625, 31.875, 32.1875):
    for k in range(6): add(sfx, tick(1.2), t0 + k * S / 2)
for i in range(16): add(sfx, blip([82, 75, 70, 81][i % 4], .26), q(28.0 + i * .25))
add(sfx, riser(3.4, 1.1), 32.5 - 3.4)
add(post, keys([45, 57, 64], .55, 3.0), 32.8125)
STOP = (32.5, 35.625)

# 04 APPROACH (35.625-47.5)
add(pads, pad(C[1], 2.2, .7, att=.6), 35.625)
for k, t in enumerate(beats(35.8125, 36.625, S / 2)): add(sfx, tick(.9 - .04 * k), t)
add(sfx, thock(36, .6), 36.5625)
for k in range(6): add(sfx, blip([72, 74, 76, 79, 81, 84][k], .45), q(37.95 + k * .12))
chords([(37.5, C), (40.0, G), (42.5, Am), (45.0, F)], 47.5, arp_g=.42)
groove(37.5, 47.5)
for t in beats(37.5, 47.5, B): add(drums, hat(.25, True), t + B / 2)
add(sfx, whoosh(.35, .5), 42.2); add(sfx, blip(88, .5), 42.5)
for i in range(4): add(sfx, tick(1.0), q(43.05 + i * .08))
for t in (43.4, 43.5): add(sfx, blip(81, .3), q(t))
add(sfx, whoosh(.4, .45), 47.1)

# 05 DIFFERENCE (47.5-55)
for i, (a, kv, ch) in enumerate([(47.5, [53, 57, 60, 64], F), (48.125, [55, 59, 62, 67], G), (48.75, [57, 60, 64, 69], Am)]):
    add(music, keys(kv, .75, 1.8), a)
add(pads, pad([57, 60, 64, 65], 3.8, 1.0), 47.5)
for t in beats(47.5, 51.25, 2 * B): add(drums, kick(.75), t)
for t in (49.375, 49.6875, 50.0): add(sfx, thock(38, .8), t); add(sfx, tick(1.6), t)
add(music, keys([48, 55, 64, 67], .85, 3.6), 51.25)
add(pads, pad([55, 60, 62, 67], 3.9, 1.0, att=.4), 51.25)
for t in beats(51.25, 55.0): add(drums, kick(.6 + .1 * (t - 51.25)), t)
for t in beats(52.5, 55.0, S): add(drums, hat(.18 + .05 * (t - 52.5)), t)
add(sfx, riser(2.5, 1.0, 200, 4000), 52.5)

# 06 NAME (55-60)
add(drums, boom(1.1), 55.0); add(drums, kick(1.2), 55.0)
add(pads, pad([48, 55, 60, 64, 67, 72], 5.0, 1.6, att=.02, rel=1.6), 55.0)
add(music, keys([48, 60, 64, 67, 72], 1.0, 4.0), 55.0)
add(music, bass(36, 4.5, .9, .1), 55.0)
for k in range(5): add(sfx, blip([72, 76, 79, 83, 84][k], .5), 55.5 + k * .08)
for k, t in enumerate(beats(56.25, 59.4, B / 2)): add(music, pluck([67, 72, 76, 79][k % 4], .25 * (1 - (t - 56) / 3.6), bright=.6), t)
for t in beats(56.25, 58.75): add(drums, kick(.45), t)

# ---------- mix ----------
irn = int(1.8 * SR); ti = np.arange(irn) / SR
ir = rng.standard_normal(irn) * np.exp(-ti * 2.8); ir = onepole_lp(ir, 5200); ir /= np.sqrt((ir ** 2).sum())
wet = fft_conv(pads * .5 + sfx * .45 + music * .3, ir) * .32
duck = np.ones(N)
for t in beats(25.0, 32.5) + beats(37.5, 47.5) + beats(15.0, 24.6875):
    i = int(t * SR); n = int(.24 * SR); duck[i:i + n] = np.minimum(duck[i:i + n], .5 + .5 * np.linspace(0, 1, n) ** .7)
mix = drums * .85 + (music * .8 + pads + wet) * duck + sfx * .65
a, b = int(STOP[0] * SR), int(STOP[1] * SR); r = int(.006 * SR)
mix[a - r:a] *= np.linspace(1, 0, r); mix[a:b] = 0
fi = int(.25 * SR); mix[b:b + fi] *= np.linspace(0, 1, fi)
mix += post + fft_conv(post, ir) * .5
fo = np.ones(N); m = int(1.4 * SR); fo[-m:] = np.linspace(1, 0, m) ** 1.6; fo[:300] = np.linspace(0, 1, 300)
mix *= fo
mix = np.tanh(mix * 1.3) / np.tanh(1.3)
mix *= 10 ** (-1 / 20) / np.max(np.abs(mix))
st = np.stack([mix, mix], 1)
wf = wet * .06 * fo; wf[a:b] = 0
st[:, 0] += wf; st[:, 1] -= wf
st = np.clip(st, -1, 1)
with wave.open('music_personal.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype('<i2').tobytes())
print('ok', N / SR)
