"""Cut the 61 s workshop masters into 60/30/15 s deliverables (16:9 + 9:16).
Segments are on 2 s bar lines so music and picture stay on the grid. Final card is baked in as frame 0."""
import subprocess, sys
OUT = '../workshop-film'
CUTS = {'60s': [(0, 60)], '30s': [(4, 8), (18, 30), (46, 60)], '15s': [(4, 8), (46, 50), (54, 61)]}
for fmt, size in (('16x9', '1920:1080'), ('9x16', '1080:1920')):
    src = f"ws_{'h' if fmt == '16x9' else 'v'}_noaudio.mp4"
    poster = f'{OUT}/poster-{fmt}.jpg'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '58.6', '-i', src, '-frames:v', '1', '-q:v', '2', poster], check=True)
    for name, segs in CUTS.items():
        fc = []; vl = []; al = []
        for k, (a, b) in enumerate(segs):
            last = k == len(segs) - 1
            fc.append(f'[1:v]trim={a}:{b},setpts=PTS-STARTPTS,format=yuv420p,setsar=1[v{k}]')
            fo = f',afade=t=out:st={b - a - (0.35 if (last and name == "60s") else 0.012)}:d={0.35 if (last and name == "60s") else 0.012}'
            fi = ',afade=t=in:st=0:d=0.012' if k else ''
            fc.append(f'[2:a]atrim={a}:{b},asetpts=PTS-STARTPTS{fi}{fo}[a{k}]')
            vl.append(f'[v{k}]'); al.append(f'[a{k}]')
        n = len(segs)
        fc.append(''.join(vl) + f'concat=n={n}:v=1:a=0[vc]')
        fc.append(''.join(al) + f'concat=n={n}:v=0:a=1[ac]')
        # poster as frame 0 (replace, not add)
        fc.append(f'[0:v]scale={size},format=yuv420p,setsar=1[p];[vc]trim=start_frame=1,setpts=PTS-STARTPTS[vr];[p][vr]concat=n=2:v=1[v]')
        out = f'{OUT}/launching-ai-agents-{name}-{fmt}.mp4'
        cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-framerate', '30', '-t', '0.0334', '-i', poster, '-i', src, '-i', 'music_workshop.wav',
               '-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[ac]', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
               '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', out]
        subprocess.run(cmd, check=True)
        d = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', out], capture_output=True, text=True).stdout.strip()
        print(out, d)
