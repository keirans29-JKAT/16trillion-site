import sys, time
from videos import *
names = sys.argv[1:] or list(VIDEOS)
for n in names:
    t = time.time(); out, d = render_video(n, VIDEOS[n], '/home/claude/video/out')
    print(n, round(d, 1), 's video in', round(time.time() - t), 's', flush=True)
