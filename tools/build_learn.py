"""Builds the Learn pages (public/learn/) from tools/learn_articles.py.

Run from the repository root:  python3 tools/build_learn.py
The header, footer and <head> are copied from public/index.html so the pages match the homepage.
"""
import html, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from learn_articles import ARTICLES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
home = open(os.path.join(ROOT, 'public/index.html'), encoding='utf-8').read()
head = home[:home.index('</head>')]
head = re.sub(r'<title>.*?</title>', '<title>{TITLE}</title>', head, flags=re.S)
head = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="{DESC}">', head)
header = home[home.index('<header'):home.index('</header>') + 9].replace('href="#top"', 'href="/"')
header = re.sub(r'href="#([a-z]+)"', r'href="/#\1"', header)
header = header.replace('<a href="/learn/">Learn</a>', '<a href="/learn/" aria-current="page" style="color: #d9c093">Learn</a>')
footer = home[home.index('<footer'):home.index('</footer>') + 9]

PROSE = '''<style>
.prose{font-size:18px;line-height:1.75;color:#c6ccd6}
.prose h2{font-family:'Bodoni Moda','Noto Serif',Georgia,serif;font-weight:600;font-size:32px;line-height:1.2;color:#faf4e4;margin:48px 0 12px}
.prose p{margin:0 0 18px}.prose ul{margin:0 0 18px;padding-left:22px}.prose li{margin:0 0 8px}
.prose b{color:#faf4e4;font-weight:600}.prose a{color:#d9c093}
.card{display:flex;flex-direction:column;gap:12px;background:#0e2036;border:1px solid #1e3651;border-radius:10px;padding:28px;text-decoration:none;color:inherit;transition:border-color .15s}
.card:hover{border-color:#c9a961}
@media (max-width:700px){.prose{font-size:17px}.prose h2{font-size:26px}}
</style>'''

def page(title, desc, main):
    h = head.replace('{TITLE}', html.escape(title)).replace('{DESC}', html.escape(desc))
    return f'{h}{PROSE}\n</head>\n<body>\n{header}\n{main}\n{footer}\n</body>\n</html>\n'

def eyebrow(t): return f'<p style="margin: 0; color: #c9a961; font-size: 14px; letter-spacing: 0.32em; text-transform: uppercase; font-weight: 600">{t}</p>'

CTA = '''<div style="margin-top: 56px; border-top: 1px solid #1e3651; padding-top: 32px; display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between">
<p style="margin: 0; font-size: 17px; color: #c6ccd6">Questions about your own situation?</p>
<a href="/#contact" style="background: #c9a961; color: #0c1e34; padding: 16px 28px; border-radius: 999px; font-weight: 600; text-decoration: none; font-size: 14px; letter-spacing: 0.14em; text-transform: uppercase">Book a free discovery call</a>
</div>
<p style="margin: 24px 0 0; font-size: 13px; line-height: 1.6; color: #8d98a8">This article is general education, not investment, tax or legal advice for your circumstances. Illustrations are not forecasts or assured returns.</p>'''


def video_block(a):
    """A self-hosted explainer video, if public/assets/video/<slug>.mp4 exists (swap for a YouTube embed later)."""
    if not os.path.exists(os.path.join(ROOT, 'public/assets/video', a['slug'] + '.mp4')): return ''
    return (f'<figure style="margin: 12px 0 8px"><video controls playsinline preload="none" poster="/assets/video/{a["slug"]}.jpg" '
            f'style="width: 100%; aspect-ratio: 16 / 9; border-radius: 10px; border: 1px solid #1e3651; background: #071322" '
            f'aria-label="Animated explainer: {html.escape(a["title"])}"><source src="/assets/video/{a["slug"]}.mp4" type="video/mp4"></video>'
            f'<figcaption style="margin-top: 8px; font-size: 13px; color: #8d98a8">Animated explainer · no sound</figcaption></figure>')

os.makedirs(os.path.join(ROOT, 'public/learn'), exist_ok=True)
for i, a in enumerate(ARTICLES):
    others = [b for b in ARTICLES if b is not a][:3]
    related = ''.join(f'<li><a href="/learn/{b["slug"]}/">{html.escape(b["title"])}</a></li>' for b in others)
    reviewed = f'<p style="margin: 0; font-size: 14px; color: #d9c093; border: 1px solid #1e3651; border-radius: 8px; padding: 12px 16px">{html.escape(a["reviewed"])}</p>' if a.get('reviewed') else ''
    main = f'''<main>
<article style="padding: 88px 32px 112px">
<div style="max-width: 760px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px">
<a href="/learn/" style="font-size: 14px; text-decoration: none">← All explainers</a>
{eyebrow(f'Learn · {a["read"]} min read')}
<h1 style="margin: 0; font-family: 'Bodoni Moda', 'Noto Serif', Georgia, serif; font-size: 56px; line-height: 1.08; font-weight: 600; color: #faf4e4">{html.escape(a["title"])}</h1>
<p style="margin: 0; font-size: 21px; line-height: 1.6; color: #c6ccd6">{html.escape(a["dek"])}</p>
{reviewed}
{video_block(a)}
<div class="prose">{a["body"]}</div>
<aside style="background: #0e2036; border: 1px solid #1e3651; border-left: 3px solid #c9a961; border-radius: 8px; padding: 22px 24px">
<p style="margin: 0 0 6px; font-size: 13px; letter-spacing: 0.16em; text-transform: uppercase; color: #d9c093; font-weight: 600">In short</p>
<p style="margin: 0; font-size: 17px; line-height: 1.6; color: #f3eddf">{html.escape(a["short"])}</p>
</aside>
<nav aria-label="More explainers" style="margin-top: 16px"><p style="margin: 0 0 8px; font-size: 13px; letter-spacing: 0.16em; text-transform: uppercase; color: #8d98a8">Read next</p><ul style="margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 6px; font-size: 16px">{related}</ul></nav>
{CTA}
</div>
</article>
</main>'''
    d = os.path.join(ROOT, 'public/learn', a['slug']); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(page(f'{a["title"]} — 16T₹illion Learn', a['dek'], main))

cards = ''.join(f'''<a class="card" href="/learn/{a["slug"]}/"><span style="font-size: 13px; letter-spacing: 0.16em; text-transform: uppercase; color: #8d98a8">{a["read"]} min read{" · video" if os.path.exists(os.path.join(ROOT, "public/assets/video", a["slug"] + ".mp4")) else ""}</span><h2 style="margin: 0; font-family: 'Bodoni Moda', 'Noto Serif', Georgia, serif; font-size: 28px; line-height: 1.2; font-weight: 600; color: #faf4e4">{html.escape(a["title"])}</h2><p style="margin: 0; font-size: 16px; line-height: 1.6; color: #c6ccd6">{html.escape(a["dek"])}</p><span style="margin-top: auto; color: #d9c093; font-weight: 600; font-size: 15px">Read →</span></a>''' for a in ARTICLES)
main = f'''<main>
<section style="padding: 96px 32px 40px; background: radial-gradient(1200px 500px at 80% 0%, #0e2036 0%, #071322 70%)">
<div style="max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px">
{eyebrow('Learn')}
<h1 style="margin: 0; font-family: 'Bodoni Moda', 'Noto Serif', Georgia, serif; font-size: 64px; line-height: 1.05; font-weight: 600; color: #faf4e4">Money, explained plainly.</h1>
<p style="margin: 0; font-size: 18px; line-height: 1.6; color: #c6ccd6; max-width: 760px">Short explainers on the ideas behind good financial decisions. No fund names, no return promises: just how things work, so you can ask better questions.</p>
</div>
</section>
<section style="padding: 24px 32px 112px">
<div style="max-width: 1200px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr)); gap: 24px">{cards}</div>
</section>
</main>'''
open(os.path.join(ROOT, 'public/learn/index.html'), 'w', encoding='utf-8').write(page('Learn — 16T₹illion Wealth Advisory', 'Plain-language explainers on asset allocation, Direct vs Regular plans, risk profiles, SIPs, mutual fund tax, gold and fee-only advice.', main))
print('built', len(ARTICLES), 'articles')
