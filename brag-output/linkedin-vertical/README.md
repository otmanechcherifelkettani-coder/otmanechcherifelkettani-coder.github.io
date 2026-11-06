# LinkedIn vertical cut

- `brag.mp4`: 1080×1920 (9:16), 30 fps, 22.5 s, H.264 + AAC, -14 LUFS. Content is kept clear of the bottom ~300 px where LinkedIn overlays captions and buttons.
- `brag.jpg`: poster (the ×10 hook frame), also baked in as frame 0 so the feed thumbnail stops the scroll.
- `share-copy.txt`: post text.

Source: `../work/video-vertical.html` + `../work/music_vertical.py`; render with
`W=1080 H=1920 DUR=22.5 PAGE=video-vertical.html OUT=vert_noaudio.mp4 node render.js`.
