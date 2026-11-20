"""Small animation engine for 16Trillion Learn videos: navy and gold, 1920x1080, 30 fps.

Each video is a list of scenes. Each scene is rendered to its own MP4 (frames piped to ffmpeg),
then the scenes are joined with the concat demuxer. Elements fade and slide in; every scene fades
out over its last 0.5 s, so no crossfade between files is needed.
"""
import math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, 'fonts')
BG = (7, 19, 34); NAVY = (12, 30, 52); SURF = (14, 32, 54); LINE = (30, 54, 81)
GOLD = (201, 169, 97); GOLD2 = (217, 192, 147); CREAM = (250, 244, 228); INK = (243, 237, 223)
INK2 = (198, 204, 214); MUTED = (141, 152, 168); BLUE = (91, 147, 230); SLATE = (58, 83, 115)
RED = (239, 122, 114); GREEN = (89, 192, 138)
X0, X1 = 170, 1750  # content margins

_fc = {}
FAM = {'serif': ('bodoni-600.ttf', 'noto-600.ttf'), 'serif-i': ('bodoni-600i.ttf', 'noto-600.ttf'),
       'sans': ('plex-400.ttf', 'plexx-400.ttf'), 'sans-m': ('plex-500.ttf', 'plexx-400.ttf'), 'sans-b': ('plex-600.ttf', 'plexx-600.ttf')}
_cm = {}
def font(fn, size):
    k = (fn, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(os.path.join(FD, fn), size)
    return _fc[k]
def cmap(fn):
    if fn not in _cm:
        from fontTools.ttLib import TTFont
        _cm[fn] = set(TTFont(os.path.join(FD, fn)).getBestCmap())
    return _cm[fn]

def runs(text, fam):
    p, f = FAM[fam]; out = []; cp = cmap(p)
    for ch in text:
        fn = p if (ord(ch) in cp or ch == ' ') else f
        if out and out[-1][0] == fn: out[-1][1] += ch
        else: out.append([fn, ch])
    return out

def tw(text, fam, size, track=0):
    return sum(font(fn, size).getlength(s) for fn, s in runs(text, fam)) + track * max(0, len(text) - 1)

def mix(c, a, bg=BG):
    a = max(0.0, min(1.0, a)); return tuple(int(bg[i] + (c[i] - bg[i]) * a) for i in range(3))

def ease(t): t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3

def text(d, x, y, s, fam, size, color, a=1.0, track=0, anchor='l', bg=BG):
    """Draws mixed-font text with its top-left (or centre/right) at x, y; alpha blends toward bg."""
    w = tw(s, fam, size, track)
    if anchor == 'c': x -= w / 2
    elif anchor == 'r': x -= w
    col = mix(color, a, bg)
    for fn, part in runs(s, fam):
        f = font(fn, size)
        if track:
            for ch in part:
                d.text((x, y), ch, font=f, fill=col); x += f.getlength(ch) + track
        else:
            d.text((x, y), part, font=f, fill=col); x += f.getlength(part)
    return w

def wrap(s, fam, size, width):
    words, lines, cur = s.split(), [], ''
    for wd in words:
        t = (cur + ' ' + wd).strip()
        if tw(t, fam, size) <= width or not cur: cur = t
        else: lines.append(cur); cur = wd
    if cur: lines.append(cur)
    return lines

def para(d, x, y, s, fam, size, color, width, a=1.0, lh=1.45, bg=BG):
    for i, ln in enumerate(wrap(s, fam, size, width)):
        text(d, x, y + i * size * lh, ln, fam, size, color, a, bg=bg)
    return len(wrap(s, fam, size, width)) * size * lh

def rrect(d, box, r, fill):
    d.rounded_rectangle(box, r, fill=fill)

# ---------- background ----------
def make_bg():
    img = Image.new('RGB', (W, H), BG)
    px = img.load()
    cx, cy = W * 0.82, H * 0.18
    for yy in range(0, H, 2):
        for xx in range(0, W, 2):
            dd = math.hypot((xx - cx) / 1.6, yy - cy) / 900
            a = max(0.0, 1 - dd) ** 2 * 0.9
            c = mix(SURF, a)
            px[xx, yy] = c
            if xx + 1 < W: px[xx + 1, yy] = c
            if yy + 1 < H:
                px[xx, yy + 1] = c
                if xx + 1 < W: px[xx + 1, yy + 1] = c
    d = ImageDraw.Draw(img)
    gc = mix(GOLD, 0.10)
    ox, oy, R = 1640, 300, 430
    d.ellipse((ox - R, oy - R, ox + R, oy + R), outline=gc, width=2)
    for rx in (320, 190, 60):
        d.ellipse((ox - rx, oy - R, ox + rx, oy + R), outline=gc, width=2)
    d.ellipse((ox - R, oy - 150, ox + R, oy + 150), outline=gc, width=2)
    d.line((ox - R, oy, ox + R, oy), fill=gc, width=2)
    return img
BGIMG = None
def bg():
    global BGIMG
    if BGIMG is None:
        p = os.path.join(HERE, 'bg.png')
        if os.path.exists(p): BGIMG = Image.open(p).convert('RGB')
        else: BGIMG = make_bg(); BGIMG.save(p)
    return BGIMG

LOGO = None
def logo(size):
    global LOGO
    if LOGO is None: LOGO = Image.open(os.path.join(HERE, 'logo.png')).convert('RGBA')
    return LOGO.resize((size, size), Image.LANCZOS)

# ---------- shared pieces ----------
def appear(t, start, dur=0.6):
    e = ease((t - start) / dur); return e, (1 - e) * 26

def eyebrow(d, t, s, y=150, start=0.0):
    a, dy = appear(t, start)
    d.line((X0, y + 17, X0 + 64, y + 17), fill=mix(GOLD, a), width=2)
    text(d, X0 + 88, y + dy * 0.3, s.upper(), 'sans-b', 26, GOLD, a, track=7)

def heading(d, t, s, y=210, start=0.15, size=84, width=None, color=CREAM):
    a, dy = appear(t, start, 0.7)
    lines = wrap(s, 'serif', size, width or (X1 - X0))
    for i, ln in enumerate(lines):
        text(d, X0, y + dy + i * size * 1.12, ln, 'serif', size, color, a)
    return y + len(lines) * size * 1.12

def footer_brand(d, a=1.0):
    text(d, X0, H - 78, '16T₹illion', 'serif', 30, CREAM, a * 0.55)
    text(d, X1, H - 72, '16trillion.com/learn', 'sans', 22, MUTED, a * 0.8, anchor='r')

# ---------- scenes ----------
# Each scene is (duration, draw(img, d, t), settle) where frames are identical between settle and duration-0.5.

def words(*ss): return sum(len(str(s).split()) for s in ss)
def dur_for(n, base=3.0): return round(base + n / 2.7, 1)

def sc_title(title, sub, kicker='Learn'):
    D = dur_for(words(title, sub), 3.2)
    def draw(img, d, t):
        eyebrow(d, t, f'16T₹illion · {kicker}', y=330)
        y = heading(d, t, title, y=395, size=104, width=1300)
        a, dy = appear(t, 0.6, 0.8)
        para(d, X0, y + 40 + dy, sub, 'sans', 40, INK2, 1250, a)
    return D, draw, 1.6

def sc_statement(eb, head, body, extra=None):
    D = dur_for(words(head, body), 3.0)
    def draw(img, d, t):
        eyebrow(d, t, eb)
        y = heading(d, t, head, width=1450)
        a, dy = appear(t, 0.7, 0.8)
        para(d, X0, y + 46 + dy, body, 'sans', 42, INK2, 1400, a)
        footer_brand(d)
    return D, draw, 1.6

def sc_bullets(eb, head, items, start=1.0, gap=None):
    n = len(items); step = gap or max(1.4, min(2.6, 9.0 / n))
    D = round(start + step * n + 1.6 + words(*items) / 4.0, 1)
    def draw(img, d, t):
        eyebrow(d, t, eb)
        y = heading(d, t, head, width=1450) + 85
        for i, it in enumerate(items):
            a, dy = appear(t, start + i * step, 0.6)
            if a <= 0: break
            d.ellipse((X0, y + 22 + dy, X0 + 14, y + 36 + dy), fill=mix(GOLD, a))
            h = para(d, X0 + 44, y + dy, it, 'sans', 40, INK, 1450, a)
            y += h + 22
        footer_brand(d)
    return D, draw, start + step * n + 0.6

def sc_compare(eb, head, left, right):
    D = dur_for(words(head, *left[1], *right[1]), 4.0)
    def card(d, t, x, w, title, items, hi, start):
        a, dy = appear(t, start, 0.7)
        top = 430 + dy
        fill = mix(CREAM, a * 0.96) if hi else mix(SURF, a)
        rrect(d, (x, top, x + w, 930 + dy), 18, fill)
        cbg = CREAM if hi else SURF
        tc = (107, 82, 32) if hi else MUTED
        text(d, x + 50, top + 46, title.upper(), 'sans-b', 26, tc, 1, track=4, bg=cbg)
        yy = top + 112
        for i, it in enumerate(items):
            b, _ = appear(t, start + 0.5 + i * 0.7, 0.5)
            col = NAVY if hi else INK2
            d.ellipse((x + 50, yy + 18, x + 62, yy + 30), fill=mix(GOLD if hi else MUTED, b, cbg))
            yy += para(d, x + 84, yy, it, 'sans', 36, col, w - 130, b, bg=cbg) + 18
    def draw(img, d, t):
        eyebrow(d, t, eb)
        heading(d, t, head, width=1500, size=76)
        w = (X1 - X0 - 50) // 2
        card(d, t, X0, w, left[0], left[1], False, 0.9)
        card(d, t, X0 + w + 50, w, right[0], right[1], True, 2.2)
        footer_brand(d)
    return D, draw, 2.2 + 0.5 + 0.7 * max(len(left[1]), len(right[1])) + 0.5

def sc_cards(eb, head, cards, note=''):
    D = dur_for(words(head, note, *[c[1] for c in cards]), 4.0)
    def draw(img, d, t):
        eyebrow(d, t, eb)
        heading(d, t, head, width=1500, size=76)
        n = len(cards); gap = 40; w = (X1 - X0 - gap * (n - 1)) / n
        for i, (big, cap, col) in enumerate(cards):
            a, dy = appear(t, 0.9 + i * 0.8, 0.7)
            x = X0 + i * (w + gap); top = 440 + dy
            rrect(d, (x, top, x + w, top + 380), 18, mix(SURF, a))
            d.rectangle((x, top + 18, x + 6, top + 362), fill=mix(col, a, SURF))
            text(d, x + 50, top + 50, big, 'sans-b', 92 if n < 4 else 72, col, a, bg=SURF)
            para(d, x + 50, top + 190, cap, 'sans', 34, INK2, w - 90, a, bg=SURF)
        if note:
            a, _ = appear(t, 1.0 + n * 0.8, 0.7)
            para(d, X0, 870, note, 'sans', 30, MUTED, 1560, a)
        footer_brand(d)
    return D, draw, 1.0 + len(cards) * 0.8 + 0.7

def fmt_l(v):
    return f'₹{v / 100:.2f} Cr' if v >= 100 else f'₹{v:.0f} L'

def sc_lines(eb, head, series, years, note='', fmt=fmt_l, xlabel='Year', ymin=0):
    """series: [(name, color, [values per year 0..years])]. Lines draw left to right."""
    D = 11.0 + words(note) / 3
    def draw(img, d, t):
        eyebrow(d, t, eb)
        heading(d, t, head, width=1500, size=72)
        gx0, gx1, gy0, gy1 = X0 + 150, X1 - 260, 400, 820
        a0, _ = appear(t, 0.6, 0.6)
        vmax = max(max(s[2]) for s in series) * 1.08; vmin = ymin
        Y = lambda v: gy1 - (gy1 - gy0) * (v - vmin) / (vmax - vmin)
        for k in range(5):
            v = vmin + (vmax - vmin) * k / 4; yy = Y(v)
            d.line((gx0, yy, gx1, yy), fill=mix(LINE, a0), width=1)
            text(d, gx0 - 20, yy - 16, fmt(v), 'sans', 24, MUTED, a0, anchor='r')
        for yv in range(0, years + 1, max(1, years // 5)):
            xx = gx0 + (gx1 - gx0) * yv / years
            text(d, xx, gy1 + 16, f'{xlabel} {yv}', 'sans', 24, MUTED, a0, anchor='c')
        upto = ease((t - 1.2) / 5.5) * years
        ends = []
        for name, col, vals in series:
            pts = []
            for yv in range(years + 1):
                if yv > upto: break
                pts.append((gx0 + (gx1 - gx0) * yv / years, Y(vals[yv])))
            i0 = int(upto); f = upto - i0
            cur = vals[i0] if i0 >= years else vals[i0] + (vals[i0 + 1] - vals[i0]) * f
            if i0 < years: pts.append((gx0 + (gx1 - gx0) * upto / years, Y(cur)))
            if len(pts) > 1: d.line(pts, fill=col, width=6, joint='curve')
            if pts:
                ex, ey = pts[-1]; d.ellipse((ex - 9, ey - 9, ex + 9, ey + 9), fill=col)
                ends.append([ey, ex, cur, name, col])
        ends.sort()
        for k in range(1, len(ends)):
            if ends[k][0] - ends[k - 1][0] < 76: ends[k][0] = ends[k - 1][0] + 76
        for ey, ex, cur, name, col in ends:
            text(d, ex + 22, ey - 24, fmt(cur), 'sans-b', 34, col)
            text(d, ex + 22, ey + 16, name, 'sans', 24, INK2)
        if note:
            a, _ = appear(t, 7.2, 0.7)
            para(d, X0, 900, note, 'sans', 27, MUTED, 1580, a)
        footer_brand(d)
    return D, draw, 8.0

def sc_bars(eb, head, bars, note='', unit='%'):
    """bars: [(label, value, label_text, color)]; negative values draw downward from a zero line."""
    D = dur_for(words(head, note, *[b[0] for b in bars]), 5.5)
    def draw(img, d, t):
        eyebrow(d, t, eb)
        heading(d, t, head, width=1500, size=72)
        n = len(bars); vmax = max(abs(b[1]) for b in bars)
        neg = any(b[1] < 0 for b in bars)
        zero = 470 if neg else 860; hmax = 360
        a0, _ = appear(t, 0.6, 0.5)
        bw = 220; gap = (X1 - X0 - n * bw) / (n + 1)
        d.line((X0, zero, X1, zero), fill=mix(LINE, a0), width=2)
        for i, (lab, v, lt, col) in enumerate(bars):
            g = ease((t - 1.2 - i * 0.6) / 1.2)
            x = X0 + gap + i * (bw + gap); h = hmax * abs(v) / vmax * g
            if v < 0: box = (x, zero, x + bw, zero + h); ty = zero + h + 18; ly = zero - 60
            else: box = (x, zero - h, x + bw, zero); ty = zero - h - 64; ly = zero + 20
            if h > 1: d.rectangle(box, fill=col)
            text(d, x + bw / 2, ty, lt, 'sans-b', 44, INK2 if col == SLATE else col, g, anchor='c')
            for k, ln in enumerate(wrap(lab, 'sans', 28, bw + 120)):
                text(d, x + bw / 2, ly + k * 36, ln, 'sans', 28, INK2, a0, anchor='c')
        if note:
            a, _ = appear(t, 1.8 + n * 0.6, 0.7)
            para(d, X0, 960 if not neg else 920, note, 'sans', 28, MUTED, 1560, a)
        footer_brand(d)
    return D, draw, 2.6 + len(bars) * 0.6

def sc_stack(eb, head, rows, legend, note=''):
    """rows: [(label, [shares summing to 100])]; legend: [(name, color)]."""
    D = dur_for(words(head, note), 6.5)
    def draw(img, d, t):
        eyebrow(d, t, eb)
        heading(d, t, head, width=1500, size=72)
        a0, _ = appear(t, 0.5, 0.5)
        lx = X0
        for name, col in legend:
            d.rounded_rectangle((lx, 418, lx + 26, 444), 5, fill=mix(col, a0)); lx += 40
            lx += text(d, lx, 412, name, 'sans', 28, INK2, a0) + 44
        bx0, bx1 = X0 + 380, X1
        for r, (lab, shares) in enumerate(rows):
            y = 500 + r * 150
            a, dy = appear(t, 0.9 + r * 1.6, 0.6)
            text(d, X0, y + 24, lab, 'sans-m', 32, INK, a)
            g = ease((t - 1.1 - r * 1.6) / 1.0); x = bx0
            for k, sh in enumerate(shares):
                w = (bx1 - bx0) * sh / 100 * g
                if w > 1:
                    d.rectangle((x, y, x + w - 3, y + 88), fill=legend[k][1])
                    if w > 90 and g > 0.95: text(d, x + 20, y + 24, f'{sh}%', 'sans-b', 34, BG if k == 0 else CREAM, 1, bg=legend[k][1])
                x += w
        if note:
            a, _ = appear(t, 1.2 + len(rows) * 1.6, 0.7)
            para(d, X0, 960, note, 'sans', 28, MUTED, 1560, a)
        footer_brand(d)
    return D, draw, 1.8 + len(rows) * 1.6

def sc_end(line='Education, not advice. Illustrations are not forecasts or assured returns.'):
    D = 6.0
    def draw(img, d, t):
        a, dy = appear(t, 0.2, 0.9)
        if a > 0:
            lg = logo(300); r, g, b_, al = lg.split()
            al = al.point(lambda v: int(v * a))
            img.paste(lg.convert('RGB'), (W // 2 - 150, int(250 + dy)), al)
        b, _ = appear(t, 0.9, 0.8)
        text(d, W / 2, 610, 'Fee-only financial planning and investment advice', 'sans', 40, INK, b, anchor='c')
        text(d, W / 2, 680, '16trillion.com', 'sans-b', 44, GOLD2, b, anchor='c')
        c, _ = appear(t, 1.6, 0.8)
        text(d, W / 2, 900, line, 'sans', 26, MUTED, c, anchor='c')
    return D, draw, 2.4

# ---------- rendering ----------
def render_scene(scene, path, fade_in=True):
    D, draw, settle = scene
    n = int(round(D * FPS)); tmp = path[:-4] + '.part.mp4'
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', str(FPS), tmp], stdin=subprocess.PIPE)
    base = bg(); cache = None
    for i in range(n):
        t = i / FPS
        out_a = min(1.0, (D - t) / 0.5)
        if settle < t < D - 0.5 and cache is not None:
            p.stdin.write(cache); continue
        img = base.copy(); d = ImageDraw.Draw(img)
        draw(img, d, t)
        if out_a < 1: img = Image.blend(base, img, max(0.0, out_a))
        b = img.tobytes()
        if settle < t < D - 0.5: cache = b
        p.stdin.write(b)
    p.stdin.close()
    if p.wait() != 0: raise SystemExit('ffmpeg failed: ' + path)
    os.replace(tmp, path)

def still(scene, t, path):
    D, draw, settle = scene
    img = bg().copy(); d = ImageDraw.Draw(img); draw(img, d, t); img.save(path)

def render_video(name, scenes, outdir):
    os.makedirs(outdir, exist_ok=True)
    work = os.path.join(outdir, 'parts', name); os.makedirs(work, exist_ok=True)
    files = []
    for i, sc in enumerate(scenes):
        f = os.path.join(work, f'{i:02d}.mp4'); render_scene(sc, f); files.append(f)
    lst = os.path.join(work, 'list.txt')
    open(lst, 'w').write(''.join(f"file '{f}'\n" for f in files))
    out = os.path.join(outdir, name + '.mp4'); tmp = out[:-4] + '.part.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, out)
    return out, sum(s[0] for s in scenes)
