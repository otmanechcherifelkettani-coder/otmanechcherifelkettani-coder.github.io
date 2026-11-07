"""Shorten long pauses inside a voice line, then speed up slightly. Prints word-gap cue times of the result."""
import sys, re, subprocess, numpy as np, wave
src, dst, tempo = sys.argv[1], sys.argv[2], float(sys.argv[3])
out = subprocess.run(['ffmpeg','-hide_banner','-i',src,'-af','silencedetect=noise=-38dB:d=0.25','-f','null','-'],capture_output=True,text=True).stderr
ss=[float(x) for x in re.findall(r'silence_start: ([0-9.]+)',out)]; se=[float(x) for x in re.findall(r'silence_end: ([0-9.]+)',out)]
w=wave.open(src); sr=w.getframerate(); x=np.frombuffer(w.readframes(w.getnframes()),'<i2').copy()
keep=.18; parts=[]; pos=0
for a,b in zip(ss,se):
    ia,ib=int(a*sr),int(b*sr); mid=ia+int(keep/2*sr)
    parts.append(x[pos:mid]); pos=ib-int(keep/2*sr)
parts.append(x[pos:]); y=np.concatenate(parts)
tmp=dst+'.tmp.wav'
with wave.open(tmp,'wb') as o: o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr); o.writeframes(y.tobytes())
subprocess.run(['ffmpeg','-loglevel','error','-y','-i',tmp,'-af',f'atempo={tempo}','-ar','44100',dst]); subprocess.run(['rm',tmp])
