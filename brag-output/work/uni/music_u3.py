"""Calm score for the v3 university film: soft piano, warm pad, light pulse (80 BPM), Onyx VO, ducked mix."""
import json, wave, numpy as np, soundfile as sf
SR = 44100; DUR = 63.5; N = int(SR * DUR); B = .75; rng = np.random.default_rng(3)
def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def add(buf, sig, t):
    i = int(t * SR); n = min(len(sig), len(buf) - i)
    if n > 0: buf[i:i + n] += sig[:n]
def lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.zeros_like(x); s = 0.
    for i in range(len(x)): s = (1 - a) * x[i] + a * s; y[i] = s
    return y
def fconv(x, ir):
    n = len(x) + len(ir); f = 1 << (n - 1).bit_length(); return np.fft.irfft(np.fft.rfft(x, f) * np.fft.rfft(ir, f), f)[:len(x)]
def piano(n, g=1., L=3.2):
    t = np.arange(int(L * SR)) / SR; f = midi(n)
    s = sum(a * np.sin(2 * np.pi * f * k * t * (1 + .0004 * k * k)) * np.exp(-t * (1.1 + k * .9)) for k, a in ((1, 1), (2, .45), (3, .22), (4, .1), (5, .05)))
    att = np.minimum(1, t / .006); return g * .22 * s * att
def pad(notes, L, g=1., att=1.5, rel=1.5):
    t = np.arange(int((L + rel) * SR)) / SR
    e = np.minimum(1, t / att) * np.where(t > L, np.exp(-(t - L) * 3 / rel), 1)
    s = sum(np.sin(2 * np.pi * midi(n) * t * d) for n in notes for d in (1, 1.003, .997)) / (3 * len(notes))
    return g * .5 * s * e
def pulse(n, g=1.):
    t = np.arange(int(.6 * SR)) / SR; return g * .35 * np.sin(2 * np.pi * midi(n) * t) * np.exp(-t * 7) * np.minimum(1, t / .01)
def tick(g=1.):
    t = np.arange(int(.05 * SR)) / SR; return g * .05 * rng.standard_normal(len(t)) * np.exp(-t * 120)

pno, pads, low = np.zeros(N), np.zeros(N), np.zeros(N)
# D major family: Dmaj9 – Bm7 – Gmaj7 – A6sus  (one chord per bar = 4 beats = 3 s)
CH = [([50, 57, 62, 66, 69, 76], 38), ([47, 54, 59, 62, 66, 69], 35), ([43, 50, 55, 59, 62, 66], 31), ([45, 52, 57, 62, 64, 66], 33)]
ARP = [[0, 3, 4, 5, 4, 3, 2, 3], [0, 2, 3, 5, 4, 3, 2, 4]]
bars = int(DUR / 3)
for b in range(bars):
    t0 = b * 3.0; ch, root = CH[b % 4]
    if t0 > 59: break
    add(pads, pad(ch[1:4], 3.0, .55 if b < 7 else .75), t0)
    # piano: sparse in S1/S2, flowing eighths from S3 onward
    dense = 20.5 <= t0 < 49
    pat = ARP[b % 2]
    for k in range(8 if dense else 4):
        tt = t0 + k * (B / 2 if dense else B); add(pno, piano(ch[pat[k % 8]] + 12, .55 if dense else .7), tt)
    if t0 >= 12:  # soft low pulse on each beat from S2
        for k in range(4): add(low, pulse(root, .8 if k == 0 else .45), t0 + k * B)
    if 31.5 <= t0 < 49:
        for k in range(8): add(low, tick(.8 if k % 2 else .4), t0 + k * B / 2)
# moments: title swell (20.5) and resolution chord (55.5)
add(pads, pad([50, 57, 62, 66, 69], 3.0, .9, att=.8), 20.25)
for n in (62, 66, 69, 74): add(pno, piano(n, .6, 5.0), 20.75)
for i, n in enumerate((50, 57, 62, 66, 69, 74, 78)): add(pno, piano(n, .55, 7.0), 55.6 + i * .06)
add(pads, pad([50, 57, 62, 66, 69], 5.0, 1.0, att=.6, rel=3.0), 55.5)
add(low, pulse(38, 1.0), 55.6)

PLACE = [.5, 4.75, 9.75, 12.5, 16.75, 20.75, 24.0, 32.0, 42.75, 49.75, 52.75, 55.75]
vo = np.zeros(N)
for i, t in enumerate(PLACE, 1):
    x, sr = sf.read(f'vo3/l{i:02d}.wav'); x = np.interp(np.arange(0, len(x) * SR / sr) * sr / SR, np.arange(len(x)), x); add(vo, x, t)
vo = vo - lp(vo, 70); act = np.abs(vo) > 1e-3; vo *= 10 ** (-11 / 20) / np.sqrt(np.mean(vo[act] ** 2))
env = np.convolve(np.abs(vo), np.ones(2205) / 2205, 'same'); gate = (env > .008).astype(float)
k = int(.25 * SR); att = np.convolve(gate, np.ones(k) / k, 'same'); vduck = 1 - (1 - 10 ** (-7 / 20)) * np.clip(att * 1.5, 0, 1)
irn = int(2.6 * SR); ti = np.arange(irn) / SR; ir = rng.standard_normal(irn) * np.exp(-ti * 2.2); ir = lp(ir, 5000); ir /= np.sqrt((ir ** 2).sum())
dry = pno * .8 + pads * .7 + lp(low, 900) * .9
wet = fconv(pno * .6 + pads * .4, ir) * .35
bed = (dry + wet) * vduck
vrev = fconv(vo, ir[:int(.8 * SR)]) * .04
mix = bed * .55 + vo + vrev
mix[:300] *= np.linspace(0, 1, 300); m = int(1.5 * SR); mix[-m:] *= np.linspace(1, 0, m) ** 1.5
mix = np.tanh(mix * 1.1) / np.tanh(1.1); mix *= 10 ** (-1 / 20) / np.max(np.abs(mix))
w2 = wet * .05; st = np.clip(np.stack([mix + w2, mix - w2], 1), -1, 1)
with wave.open('music_u3.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype('<i2').tobytes())
print('ok')
