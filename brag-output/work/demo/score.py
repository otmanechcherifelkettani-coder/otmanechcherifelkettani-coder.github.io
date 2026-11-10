"""Original score + SFX + VO mix for the university demo film (numpy only). Writes out/mix.wav."""
import json, numpy as np, soundfile as sf
tl = json.load(open('tl.json')); T = {int(k): v for k, v in tl['T'].items()}; Dd = {int(k): v for k, v in tl['D'].items()}; END = tl['END']
SR = 44100; N = int(SR * (END + .05)); rng = np.random.default_rng(7); B = .6; BAR = 4 * B
midi = lambda n: 440.0 * 2 ** ((n - 69) / 12)
def add(buf, sig, t, g=1.):
    i = int(t * SR)
    if i < 0: sig = sig[-i:]; i = 0
    n = min(len(sig), len(buf) - i)
    if n > 0: buf[i:i + n] += g * sig[:n]
def filt(x, lo=None, hi=None):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); g = np.ones_like(f)
    if hi: g *= 1 / np.sqrt(1 + (f / hi) ** 4)
    if lo: g *= 1 - 1 / np.sqrt(1 + (f / lo) ** 4)
    return np.fft.irfft(X * g, len(x))
def tt(L): return np.arange(int(L * SR)) / SR
def pad(notes, L, att=1.2, rel=1.6):
    t = tt(L + rel); e = np.minimum(1, t / att) * np.where(t > L, np.exp(-(t - L) * 3 / rel), 1)
    s = sum(np.sin(2 * np.pi * midi(n) * t * d + ph) + .3 * np.sin(4 * np.pi * midi(n) * t * d) for n in notes for d, ph in ((1, 0), (1.004, 1), (.996, 2))) / (3 * len(notes))
    return .5 * s * e
def keys(n, L=2.6):
    t = tt(L); f = midi(n)
    s = sum(a * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (1.3 + k * 1.1)) for k, a in ((1, 1), (2, .4), (3, .18), (4, .07)))
    return .25 * s * np.minimum(1, t / .005)
def pluck(n, L=.5):
    t = tt(L); f = midi(n); s = np.sin(2 * np.pi * f * t + 1.6 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 18)) * np.exp(-t * 9)
    return .2 * s * np.minimum(1, t / .003)
def kick(): t = tt(.35); return .9 * np.sin(2 * np.pi * (48 * t + 90 * (1 - np.exp(-t * 28)) / 28)) * np.exp(-t * 11)
def hat(): t = tt(.06); return .1 * filt(rng.standard_normal(len(t)), lo=6000) * np.exp(-t * 90)
def sub(n, L): t = tt(L); return .5 * np.sin(2 * np.pi * midi(n) * t) * np.minimum(1, t / .02) * np.minimum(1, (L - t) / .08)
def whoosh(L=.9, up=True):
    t = tt(L); x = rng.standard_normal(len(t)); e = np.sin(np.pi * (t / L) ** (1.6 if up else .6)) ** 2
    y = filt(x, lo=500, hi=3500) * e; return .22 * y
def riser(L=2.0):
    t = tt(L); x = filt(rng.standard_normal(len(t)), lo=900, hi=7000) * (t / L) ** 2.2
    return .2 * x + .12 * np.sin(2 * np.pi * (180 * t + 160 * t * t / L)) * (t / L) ** 2
def impact():
    t = tt(2.4); return .9 * np.sin(2 * np.pi * (38 * t + 50 * (1 - np.exp(-t * 14)) / 14)) * np.exp(-t * 2.4) + .25 * filt(rng.standard_normal(len(t)), hi=1800) * np.exp(-t * 6)
def tick(f=1900): t = tt(.05); return .12 * np.sin(2 * np.pi * f * t) * np.exp(-t * 85)
def pop(f=660): t = tt(.16); return .2 * np.sin(2 * np.pi * (f * t + 300 * t * t)) * np.exp(-t * 26)
def chime(ns, L=3.5):
    out = np.zeros(int((L + .5) * SR))
    for i, n in enumerate(ns): add(out, keys(n, L), i * .07)
    return out

# F major family: Dm9 – Bbmaj7 – Fmaj9 – C6/9 ; one chord per bar
CH = [([50, 57, 60, 64, 65, 69], 38), ([46, 53, 57, 62, 65, 69], 34), ([41, 48, 57, 60, 64, 67], 41), ([48, 55, 57, 62, 64, 67], 36)]
ARP = [0, 2, 3, 4, 5, 4, 3, 2, 1, 3, 4, 5, 4, 3, 2, 4]
t10 = T[10]; bar0 = t10 - round(t10 / BAR) * BAR  # grid offset so the logo hit lands on a downbeat
SEC = lambda t: 0 if t < T[3] - .3 else 1 if t < T[6] - .3 else 2 if t < t10 - .1 else 3 if t < T[16] - 1 else 4 if t < T[19] - .2 else 5 if t < T[21] - .1 else 6
pads, mel, drums, low, fx = (np.zeros(N) for _ in range(5))
b = -1
while True:
    b += 1; t0 = bar0 + b * BAR
    if t0 > END - 1: break
    if t0 < -BAR: continue
    ch, root = CH[b % 4]; s = SEC(max(t0, 0) + .05)
    if s == 6: continue
    add(pads, pad(ch[1:5], BAR), t0, (.75, .8, .6, 1.0, .85, .9)[s])
    if s in (0, 4):
        for k, st in enumerate((0, 1.5, 2.5)): add(mel, keys(ch[(2, 4, 5)[k]] + 12), t0 + st * B, .7)
    if s in (1, 3, 5):
        for k in range(16): add(mel, pluck(ch[ARP[k]] + 12), t0 + k * B / 4, (.55 if k % 4 else .8) * (1.0 if s == 3 else .8))
    if s == 2:
        add(low, sub(root - 12 if root > 36 else root, BAR - .05), t0, .7)
        for k in (0, 2.5): add(mel, keys(ch[4] + 12, 3.0), t0 + k * B, .5)
    if s in (1, 3, 5):
        for k in range(4): add(drums, kick(), t0 + k * B, 1.0 if s == 3 else .75); add(low, sub(root, B * .8), t0 + k * B, .55)
    if s == 3:
        for k in range(8): add(drums, hat(), t0 + k * B / 2 + B / 4, 1.0 if k % 2 else .6)
    if s == 4:
        for k in (0, 2): add(low, sub(root, B * 1.6), t0 + k * B, .5)
# structural moments
add(fx, riser(2.2), t10 - 2.3); add(fx, impact(), t10 - .02); add(mel, chime([62, 65, 69, 72, 76, 81]), t10, .8)
add(fx, riser(1.6), T[21] - 1.7, .8); add(fx, impact(), T[21] - .02, .9); add(mel, chime([53, 60, 65, 69, 72, 77, 81], 6.0), T[21], .9); add(pads, pad([53, 60, 65, 69, 72], 4.0, att=.3, rel=3.0), T[21], 1.0)
E_ = lambda i: T[i] + Dd[i]
for t in (T[2] - .5, T[3] - .5, T[5] - .5, T[6] - .6, T[7] - .5, T[8] - .5, T[9] - .5, E_(10) + .2, T[12] - .5, T[13] - .3, T[14] - .5, T[15] - .5, T[16] - .95, T[19] - .6): add(fx, whoosh(), t, .8)
for i in range(10): add(fx, tick(1500 + 90 * i), T[4] - .25 + i * .07, .6); add(fx, pop(700 + 40 * i), T[4] + Dd[4] * .72 + i * .05, .35)
for t in (T[2] + 1.9, T[5] + 2.3, T[6] + 1.5, T[8] + Dd[8] * .3 + 1.5): add(fx, pop(520), t, .7)
for i in range(7): add(fx, tick(1300), T[11] + 1.35 + i * .11, .7)
for t in (1.6, 2.1, 3.3, 3.7): add(fx, tick(2100), T[12] + t + .18, .8)
add(fx, pop(880), T[12] + 3.9, .7)
for i in range(12): add(fx, tick(1700 + (i % 4) * 120), T[13] + .7 + i * .085, .5)
add(fx, pop(240), T[13] + Dd[13] * .34 + 1.3, .9)
tK = T[13] + Dd[13] * .6 + 1.25; add(fx, tick(900), tK, 1.2); add(fx, pop(780), tK + .05, .7)
for i, f in enumerate((.40, .54, .70, .84)): add(fx, pop(560 + 60 * i), T[14] + Dd[14] * f, .6)
for f in (.40, .53, .70, .86): add(fx, pop(600), T[17] + Dd[17] * f + .8, .5)
add(fx, tick(900), T[21] + 3.2, 1.2); add(fx, pop(780), T[21] + 3.25, .7)

# reverb on pads / melody / fx
irn = int(2.4 * SR); ti = np.arange(irn) / SR; ir = filt(rng.standard_normal(irn) * np.exp(-ti * 2.6), hi=5000); ir /= np.sqrt((ir ** 2).sum())
def rv(x, w):
    n = len(x) + irn; f = 1 << (n - 1).bit_length(); return x + w * np.fft.irfft(np.fft.rfft(x, f) * np.fft.rfft(ir, f), f)[:len(x)]
music = filt(rv(pads, .5), hi=3200) * .55 + rv(mel, .45) * .8 + drums * .5 + filt(low, hi=220) * .7 + rv(fx, .35) * .7
music = filt(music, lo=28); music /= np.max(np.abs(music)); music *= 10 ** (-9 / 20)

vo = np.zeros(N)
for i in T:
    x, sr = sf.read(f'vo/l{i:02d}.wav'); x = np.interp(np.arange(0, len(x) * SR / sr) * sr / SR, np.arange(len(x)), x); add(vo, x, T[i])
vo = filt(vo, lo=75); act = np.abs(vo) > 1e-3; vo *= 10 ** (-19 / 20) / np.sqrt(np.mean(vo[act] ** 2))
vo = np.tanh(vo * 1.6) / 1.6 * 1.9
env = np.convolve((np.abs(vo) > .01).astype(float), np.ones(int(.35 * SR)) / int(.35 * SR), 'same'); duck = 1 - (1 - 10 ** (-9 / 20)) * np.clip(env * 2.2, 0, 1)
duck = np.convolve(duck, np.ones(4410) / 4410, 'same')
mix = vo + music * duck * .62
fo = np.ones(N); k = int(1.6 * SR); fo[-k:] = np.linspace(1, 0, k) ** 1.5; fi = int(.3 * SR); fo[:fi] *= np.linspace(0, 1, fi); mix *= fo
mix /= max(1, np.max(np.abs(mix)) / .97)
st = np.stack([mix, mix], 1); sf.write('out/mix.wav', st, SR)
print('ok', END, 'peak', float(np.max(np.abs(mix))), 'vo rms', float(np.sqrt(np.mean(vo[act] ** 2))))
