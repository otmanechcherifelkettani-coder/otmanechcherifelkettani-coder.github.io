"""Score for the brag video: 120 BPM, A minor -> C major, every hit on the beat grid from t=0."""
import numpy as np, wave

SR = 44100
DUR = 41.3
N = int(SR * DUR)
BEAT = 0.5
rng = np.random.default_rng(7)

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
    if i < len(buf): buf[i:j] += sig[:j - i]

def fft_conv(x, ir):
    n = len(x) + len(ir); m = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)]

# --- instruments ---
def kick(g=1.0):
    n = int(.35 * SR); t = np.arange(n) / SR
    f = 48 + 90 * np.exp(-t * 28); ph = 2 * np.pi * np.cumsum(f) / SR
    return g * np.sin(ph) * np.exp(-t * 9) * 0.9

def clap(g=1.0):
    n = int(.25 * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n); nz = nz - onepole_lp(nz, 900); nz = onepole_lp(nz, 6000)
    e = np.exp(-t * 22) * (1 + .6 * (np.sin(2 * np.pi * 90 * t) > 0) * (t < .03))
    return g * nz * e * .35

def hat(g=1.0, open_=False):
    n = int((.18 if open_ else .05) * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n); nz = nz - onepole_lp(nz, 7000)
    return g * nz * np.exp(-t * (18 if open_ else 70)) * .18

def bass(note, length, g=1.0):
    n = int(length * SR); t = np.arange(n) / SR; f = midi(note)
    x = np.sin(2 * np.pi * f * t) + .35 * np.sin(4 * np.pi * f * t) + .12 * np.sin(6 * np.pi * f * t)
    return g * x * env_adsr(n, .005, .08, .7, .05, length) * .30

def pluck(note, g=1.0, length=.35):
    n = int(length * SR); t = np.arange(n) / SR; f = midi(note)
    x = sum(np.sin(2 * np.pi * f * k * t) / k * np.exp(-t * (6 + 5 * k)) for k in range(1, 6))
    return g * x * np.minimum(1, t * 400) * .22

def pad(notes, length, g=1.0):
    n = int(length * SR); t = np.arange(n) / SR; x = np.zeros(n)
    for nt in notes:
        for det in (-.07, .07):
            f = midi(nt + det)
            x += np.sin(2 * np.pi * f * t) + .25 * np.sin(4 * np.pi * f * t + .3)
    return g * x / len(notes) * env_adsr(n, .25, .3, .8, .5, length) * .10

def blip(note, g=1.0):
    n = int(.22 * SR); t = np.arange(n) / SR; f = midi(note)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 22) + .3 * np.sin(4 * np.pi * f * t) * np.exp(-t * 35)
    return g * x * np.minimum(1, t * 600) * .16

def tick(g=1.0):
    n = int(.03 * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n); nz = nz - onepole_lp(nz, 3000)
    return g * nz * np.exp(-t * 160) * .08

def whoosh(length, g=1.0):
    n = int(length * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n); lo = onepole_lp(nz, 2500); bp = lo - onepole_lp(lo, 400)
    e = (t / length) ** 2.2
    return g * bp * e * .30

def thud(g=1.0):
    n = int(.6 * SR); t = np.arange(n) / SR
    f = 70 * np.exp(-t * 2.5) + 30; ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 5)
    gl = rng.standard_normal(n) * (np.sin(2 * np.pi * 37 * t) > .3) * np.exp(-t * 14) * .25
    return g * (x * .8 + onepole_lp(gl, 3000))

# --- arrangement ---
drums = np.zeros(N); music = np.zeros(N); sfx = np.zeros(N); pads = np.zeros(N)
# chords per bar (root for bass, pad voicing, arp notes)
Am, F, C, G = (45, [57, 60, 64], [69, 72, 76, 72]), (41, [57, 60, 65], [69, 72, 77, 72]), (48, [55, 60, 64], [67, 72, 76, 79]), (43, [55, 59, 62], [67, 71, 74, 79])
seq = [Am, F, C, G] * 4 + [Am, F, C, G][:3] + [G]
prog = [(2 * i, *c) for i, c in enumerate(seq)] + [(40, 48, [55, 60, 64, 67], [72, 76, 79, 84])]
END = 40.0
for start, root, pv, arp in prog:
    blen = 1.3 if start == 40 else 2.0
    add(pads, pad(pv, blen + .4, 1.0 if start >= 3 else .8), start)
    for k in range(int(blen / .25)):
        t = start + k * .25
        if t >= END: break
        add(music, pluck(arp[k % 4] + (12 if (k % 8) == 7 else 0), .42 if t < 3.3 else .65), t)
    for k in range(int(blen / .5)):
        t = start + k * .5
        if t < 1.0 or t >= END: continue
        add(music, bass(root, .23, 1.0), t)
        add(music, bass(root + 12 if k % 2 else root, .2, .8), t + .25)

for k in range(int(DUR / BEAT)):
    t = k * BEAT
    if 1.0 <= t < 3.5: add(drums, kick(.7), t)
    elif 3.5 <= t < END:
        if 15.0 <= t < 15.5: continue
        add(drums, kick(1.0), t)
        if k % 2 == 1: add(drums, clap(.85), t)
    if 0.5 <= t < END:
        add(drums, hat(.55 if t >= 3.5 else .42), t + .25)
        if t >= 3.5: add(drums, hat(.28), t)
for t in np.arange(29.0, 35.0, .125):
    if round(t * 8) % 2 == 1: add(drums, hat(.2), t)
for c in (17.0, 23.0, 34.5):
    for k in range(4): add(drums, clap(.25 + .12 * k), c + k * .125)

for k in range(6): add(sfx, tick(.7), .15 + k * .3)
for t, nt in zip([3.5, 5.01, 6.34, 7.42], [72, 74, 76, 79]): add(sfx, blip(nt, .5), t)
add(sfx, blip(76, .4), 11.0); add(sfx, blip(70, .45), 11.87)
add(sfx, thud(.9), 12.5)
for k in range(8): add(sfx, tick(.85), 13.7 + k * .09)
add(sfx, thud(.5), 15.46); add(sfx, blip(93, .55), 15.65)
for t in (17.4, 23.4, 34.9): add(sfx, whoosh(.4, .7), t)
for t in (3.2, 8.45, 13.05, 28.85): add(sfx, whoosh(.22, .4), t)
for t, nt in zip([19.27, 20.63, 22.40, 23.01], [76, 79, 81, 84]): add(sfx, blip(nt, .55), t + .25)
for t, nt in zip([25.0, 25.68, 26.36], [76, 79, 81]): add(sfx, blip(nt, .5), t)
add(sfx, blip(81, .5), 29.05)
for t, nt in zip([33.05, 34.25, 34.55], [84, 86, 88]): add(sfx, blip(nt, .55), t)
add(sfx, tick(2.2), 38.76); add(sfx, blip(88, .6), 38.76)
add(pads, pad([48, 55, 60, 64, 67, 72], 2.0, 1.6), 39.3)

# reverb on pads + sfx + music (shared space)
irn = int(1.4 * SR); ti = np.arange(irn) / SR
ir = rng.standard_normal(irn) * np.exp(-ti * 3.2); ir = onepole_lp(ir, 5000); ir /= np.sqrt((ir ** 2).sum())
wet_src = pads * .6 + sfx * .5 + music * .35
wet = fft_conv(wet_src, ir) * .35

# sidechain duck from kick grid (after 5s)
duck = np.ones(N)
for k in range(int(DUR / BEAT)):
    t = k * BEAT
    if 5.0 <= t < END:
        i = int(t * SR); n = int(.22 * SR); duck[i:i + n] = np.minimum(duck[i:i + n], .55 + .45 * np.linspace(0, 1, n) ** .7)

mix = drums * .9 + (music * .8 + pads + wet) * duck + sfx * .75
# fade in first ms, fade out last 1.2 s
fo = np.ones(N); m = int(1.2 * SR); fo[-m:] = np.linspace(1, 0, m) ** 1.5; fo[:200] = np.linspace(0, 1, 200)
mix *= fo
# soft clip + normalize to -1 dBFS
mix = np.tanh(mix * 1.4) / np.tanh(1.4)
mix *= 10 ** (-1 / 20) / np.max(np.abs(mix))
st = np.stack([mix, mix], 1)
# tiny stereo width on wet
st[:, 0] += wet * .05 * fo; st[:, 1] -= wet * .05 * fo
st = np.clip(st, -1, 1)
with wave.open('music_cfg_bed.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype('<i2').tobytes())
print('ok', N / SR)
