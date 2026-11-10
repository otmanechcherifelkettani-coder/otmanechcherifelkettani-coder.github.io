"""Cut the 63.5 s v3 university masters into 60/30/15 s deliverables (16:9 + 9:16).
Cuts fall on the beat grid and between VO lines; the final card is baked in as frame 0."""
import subprocess
OUT = '../../university-film/v3'
CUTS = {'60s': [(0, 60)], '30s': [(0, 11.85), (20.6, 31.35), (55.6, 63.0)], '15s': [(9.6, 11.85), (20.6, 23.35), (52.6, 62.6)]}
for fmt, size, src in (('16x9', '1920:1080', 'out/u3_h.mp4'), ('9x16', '1080:1920', 'out/u3_v.mp4')):
    poster = f'{OUT}/poster-{fmt}.jpg'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '61', '-i', src, '-frames:v', '1', '-q:v', '2', poster], check=True)
    for name, segs in CUTS.items():
        fc, vl, al = [], [], []
        for k, (a, b) in enumerate(segs):
            last = k == len(segs) - 1
            fd = .5 if (last and name != '15s') else (.6 if last else .015)
            fc.append(f'[1:v]trim={a}:{b},setpts=PTS-STARTPTS,format=yuv420p,setsar=1[v{k}]')
            fi = ',afade=t=in:st=0:d=0.015' if k else ''
            fc.append(f'[2:a]atrim={a}:{b},asetpts=PTS-STARTPTS{fi},afade=t=out:st={b - a - fd}:d={fd}[a{k}]')
            vl.append(f'[v{k}]'); al.append(f'[a{k}]')
        n = len(segs)
        fc.append(''.join(vl) + f'concat=n={n}:v=1:a=0[vc]'); fc.append(''.join(al) + f'concat=n={n}:v=0:a=1[ac]')
        fc.append(f'[0:v]scale={size},format=yuv420p,setsar=1[p];[vc]trim=start_frame=1,setpts=PTS-STARTPTS[vr];[p][vr]concat=n=2:v=1[v]')
        out = f'{OUT}/shipping-ai-that-works-university-v3-{name}-{fmt}.mp4'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-framerate', '30', '-t', '0.0334', '-i', poster, '-i', src, '-i', 'music_u3_norm.wav',
                        '-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[ac]', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', out], check=True)
        d = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', out], capture_output=True, text=True).stdout.strip()
        print(out, d, flush=True)
