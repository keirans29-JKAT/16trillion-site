# Learn videos

Animated explainers for the Learn pages, drawn frame by frame with Pillow and encoded with ffmpeg (1920×1080, 30 fps, no sound).

- `videos.py` — the storyboard for each video (scenes and their text). Edit wording here.
- `engine.py` — the drawing and rendering code (scene types, brand colours, fonts).
- Render: `cd tools/video && python3 render_all.py [slug ...]` → `out/<slug>.mp4`, then copy to `public/assets/video/` and make a poster:
  `ffmpeg -ss 3 -i out/<slug>.mp4 -frames:v 1 -vf scale=1280:-1 -q:v 4 ../../public/assets/video/<slug>.jpg`
- Rebuild the pages: `python3 tools/build_learn.py`

Fonts are Bodoni Moda, IBM Plex Sans and Noto Serif (SIL Open Font License).
