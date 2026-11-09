"""Score for the brag video: 120 BPM, A minor -> C major, every hit on the beat grid from t=0."""
import numpy as np, wave

SR = 44100
DUR = 101.0
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

# --- arrangement: calm corporate bed, 96 BPM ---
drums = np.zeros(N); music = np.zeros(N); sfx = np.zeros(N); pads = np.zeros(N)
BEAT = 60 / 96
BAR = 4 * BEAT
Am7 = (45, [57, 60, 64, 67], [69, 72, 76, 72]); Fmaj7 = (41, [57, 60, 64, 65], [69, 72, 76, 72])
C = (48, [55, 60, 64, 67], [67, 72, 76, 72]); G6 = (43, [55, 59, 62, 64], [67, 71, 74, 71])
seq = [Am7, Fmaj7, C, G6]
END = 98.0
nb = int(END / BAR) + 1
for b in range(nb):
    start = b * BAR
    root, pv, arp = seq[b % 4]
    add(pads, pad(pv, BAR + .5, .9), start)
    for k in range(8):                                  # soft 8th-note arpeggio
        t = start + k * BEAT / 2
        if t >= END: break
        g = .28 if t < 4 else .38
        add(music, pluck(arp[k % 4], g, .5), t)
    if start >= 4.0 and start < END:
        for k in (0, 2):
            add(music, bass(root, BEAT * 1.6, .55), start + k * BEAT)
for k in range(int(DUR / BEAT)):
    t = k * BEAT
    if 4.0 <= t < END:
        if k % 4 in (0, 2): add(drums, kick(.42), t)
        add(drums, hat(.16), t + BEAT / 2)
# understated section markers
for t in (4.0, 14.2, 31.3, 40.3, 60.0, 70.1, 80.2, 92.2): add(sfx, blip(81, .22), t)
add(pads, pad([48, 55, 60, 64, 67, 72], 3.0, 1.2), 98.0)

irn = int(1.6 * SR); ti = np.arange(irn) / SR
ir = rng.standard_normal(irn) * np.exp(-ti * 2.8); ir = onepole_lp(ir, 4500); ir /= np.sqrt((ir ** 2).sum())
wet = fft_conv(pads * .6 + sfx * .5 + music * .4, ir) * .4
mix = drums * .7 + music * .7 + pads + wet + sfx * .6
fo = np.ones(N); m = int(2.0 * SR); fo[-m:] = np.linspace(1, 0, m) ** 1.5; fo[:200] = np.linspace(0, 1, 200)
mix *= fo
mix = np.tanh(mix * 1.2) / np.tanh(1.2)
mix *= 10 ** (-1 / 20) / np.max(np.abs(mix))
st = np.stack([mix + wet * .05 * fo, mix - wet * .05 * fo], 1)
st = np.clip(st, -1, 1)
with wave.open('music_ecoles2_bed.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype('<i2').tobytes())
print('ok', N / SR)
