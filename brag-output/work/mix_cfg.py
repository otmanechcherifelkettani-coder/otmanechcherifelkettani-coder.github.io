"""Mix the voice-over over the music bed: VO lines placed per scene, music ducked under speech."""
import numpy as np, wave

SR = 44100

def read(path):
    with wave.open(path) as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        x = np.frombuffer(w.readframes(n), '<i2').astype(float) / 32768
    x = x.reshape(-1, ch)
    assert sr == SR, (path, sr)
    return x

bed = read('music_cfg_bed.wav')            # stereo
N = len(bed)
vo = np.zeros(N)
# (file, start time on the output timeline)
place = [('vo5/a.wav', .25), ('vo5/b.wav', 3.50), ('vo5/c.wav', 8.75), ('vo5/d.wav', 13.35),
         ('vo5/e.wav', 18.00), ('vo5/f.wav', 24.00), ('vo5/g.wav', 29.15), ('vo5/h.wav', 35.45)]
for f, t in place:
    x = read(f)[:, 0]
    i = int(t * SR); j = min(N, i + len(x))
    assert i + len(x) <= N, f
    vo[i:j] += x[:j - i]
    print(f, f'{t:.2f} -> {t + len(x) / SR:.2f}')

# voice: gentle high-pass and presence via simple filters, then level to ~ -16 dBFS RMS while speaking
def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); z = 0.0
    for k in range(len(x)): z = (1 - a) * x[k] + a * z; y[k] = z
    return y
vo = vo - onepole_lp(vo, 90)
active = np.abs(vo) > 1e-3
rms = np.sqrt(np.mean(vo[active] ** 2))
vo *= 10 ** (-13 / 20) / rms

# duck envelope: smoothed speech activity, music down ~9 dB under voice
env = np.convolve(np.abs(vo), np.ones(int(.05 * SR)) / int(.05 * SR), 'same')
gate = (env > 0.01).astype(float)
k = int(.12 * SR)
att = np.convolve(gate, np.ones(k) / k, 'same')            # ~120 ms attack/release
duck = 1 - (1 - 10 ** (-12 / 20)) * np.clip(att * 1.6, 0, 1)

mix = bed * duck[:, None] + vo[:, None] * np.array([1.0, 1.0])
mix = np.tanh(mix * 1.2) / np.tanh(1.2)
mix *= 10 ** (-1 / 20) / np.max(np.abs(mix))
with wave.open('music_cfg.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
print('ok', N / SR)
