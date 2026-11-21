"""Render animated SVG cards for the GitHub profile README.

    python scripts/render_readme_cards.py            # animated cards -> cards/*.svg
    STATIC=1 python scripts/render_readme_cards.py   # final frame only (for previews)

Reads data/github.json (written by fetch_data.py). Edit the CONFIG block to change the words.
SVGs shown through <img> can't run JS or load anything external, so fonts are subset and
embedded as base64 WOFF, and all motion is CSS keyframes + SMIL.
"""
import base64
import calendar
import datetime as dt
import io
import json
import os
import pathlib
from html import escape

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATIC = os.environ.get("STATIC") == "1"

# ───────────────────────────── CONFIG ─────────────────────────────
NAME = "Abbishek Rajh"
PORTRAIT_STYLE = os.environ.get("PORTRAIT_STYLE", "halftone")   # "halftone" | "ascii" | "line"
HANDLE = "~/abbishekrajh"
LOCATION = "bengaluru, in"
TAGLINES = [
    "Three years of making data make sense. Now pointing it at markets.",
    "Building where AI, finance and quant meet.",
]
PILLARS = [  # (title, accent key, blurb)
    ("Data", "data", "Dashboards and pipelines that explain the metric, not just plot it."),
    ("AI", "ai", "LLMs and ML models put to work on real business workflows."),
    ("Finance", "fin", "An equity-research lens: statements, valuation, the story in the numbers."),
    ("Quant", "quant", "Risk, portfolio maths and models tested against data."),
]
TICKER = ["PYTHON", "SQL", "PANDAS", "SCIKIT-LEARN", "LLMS", "POWER BI", "MICROSTRATEGY",
          "AWS", "SALESFORCE", "STATISTICS", "VALUATION", "RISK"]
TITLES = {"mstr-pbi-migration": "MicroStrategy to Power BI", "16vc-portfolio-risk-monitor": "16VC Portfolio Risk Monitor"}
# Project cards, in order. Descriptions here win over (empty) GitHub descriptions.
PROJECTS = [
    ("16vc-portfolio-risk-monitor", "fin", "Portfolio risk monitoring: exposures and risk signals at a glance."),
    ("matrix-decomposition-app", "quant", "Matrix decompositions, computed and visualised: the linear algebra under factor models."),
    ("automated-data-cleaning-and-visualization", "data", "An automated pipeline that cleans raw data and turns it into charts."),
    ("mstr-pbi-migration", "data", "Migrating MicroStrategy reporting to Power BI."),
]
# ──────────────────────────────────────────────────────────────────

W = 840
INK, MUTED, FAINT = "#1E1A15", "#6F665A", "#B9AE9C"
PAPER, CARD_BG, LINE = "#F6F1E7", "#FBF8F1", "#E4D9C5"
GOLD = "#C9A25E"
ACCENT = {"data": "#1F6F78", "ai": "#5B4BB7", "fin": "#2E7D4F", "quant": "#B5651D"}
LABEL = {"data": "DATA", "ai": "AI", "fin": "FINANCE", "quant": "QUANT"}

CHARS = "".join(chr(c) for c in range(32, 127)) + "→↗▲▼·—–’“”"
FONT_FILES = {
    "Serif": "InstrumentSerif-Regular.ttf",
    "SerifIt": "InstrumentSerif-Italic.ttf",
    "Sans": "Geist.ttf",
    "Mono": "GeistMono.ttf",
}
_fonts: dict = {}
_metrics: dict = {}


def font_face(fam: str) -> str:
    if fam not in _fonts:
        path = ROOT / "fonts" / FONT_FILES[fam]
        opts = subset.Options()
        opts.flavor = "woff"
        opts.layout_features = ["kern", "liga"]
        f = TTFont(path)
        s = subset.Subsetter(opts)
        s.populate(text=CHARS)
        s.subset(f)
        buf = io.BytesIO()
        f.flavor = "woff"
        f.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        weight = "100 900" if "fvar" in f else "400"
        _fonts[fam] = (f"@font-face{{font-family:'{fam}';src:url(data:font/woff;base64,{b64}) "
                       f"format('woff');font-weight:{weight};}}")
    return _fonts[fam]


def text_w(s: str, fam: str, size: float) -> float:
    """Advance width of a string at the default instance (good enough for layout)."""
    if fam not in _metrics:
        f = TTFont(ROOT / "fonts" / FONT_FILES[fam])
        _metrics[fam] = (f.getBestCmap(), f["hmtx"].metrics, f["head"].unitsPerEm)
    cmap, hmtx, upm = _metrics[fam]
    return sum(hmtx[cmap.get(ord(c), cmap[ord("?")])][0] for c in s) * size / upm


def wrap(s: str, fam: str, size: float, max_w: float) -> list[str]:
    lines, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if text_w(trial, fam, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur] if cur else lines


BASE_CSS = """
.serif{font-family:'Serif',Georgia,serif}.it{font-family:'SerifIt',Georgia,serif;font-style:italic}
.sans{font-family:'Sans',system-ui,sans-serif}.mono{font-family:'Mono',ui-monospace,monospace}
.up{opacity:0;animation:up .8s cubic-bezier(.2,.7,.2,1) forwards}
@keyframes up{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.fade{opacity:0;animation:fade .6s ease-out forwards}@keyframes fade{to{opacity:1}}
.tilt{opacity:0;transform-box:fill-box;transform-origin:50% 100%;
 animation:tilt .9s cubic-bezier(.3,1.4,.5,1) forwards}
@keyframes tilt{0%{opacity:0;transform:translateY(18px) rotate(-3deg) scale(.96)}
 60%{opacity:1}100%{opacity:1;transform:none}}
.rise{opacity:0;transform-box:fill-box;transform-origin:50% 100%;
 animation:rise .9s cubic-bezier(.2,1.35,.4,1) forwards}
@keyframes rise{0%{opacity:0;transform:translateY(30px) rotate(8deg) scale(.9)}40%{opacity:1}
 100%{opacity:1;transform:none}}
.pop{opacity:0;animation:pop .45s ease-out forwards}
@keyframes pop{from{opacity:0;transform:translateY(-5px)}to{opacity:1;transform:none}}
.grow{transform-box:fill-box;transform-origin:50% 100%;transform:scaleY(0);
 animation:grow 1s cubic-bezier(.2,.8,.2,1) forwards}@keyframes grow{to{transform:scaleY(1)}}
.fillx{transform-box:fill-box;transform-origin:0 50%;transform:scaleX(0);
 animation:fillx 1.2s cubic-bezier(.2,.8,.2,1) forwards}@keyframes fillx{to{transform:scaleX(1)}}
.draw{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 1.8s ease-in-out forwards}
@keyframes draw{to{stroke-dashoffset:0}}
.redraw{stroke-dasharray:1;stroke-dashoffset:1;animation:redraw 4.5s ease-in-out infinite}
@keyframes redraw{0%{stroke-dashoffset:1;opacity:1}40%,85%{stroke-dashoffset:0;opacity:1}
 100%{stroke-dashoffset:0;opacity:0}}
.bob{transform-box:fill-box;transform-origin:50% 100%;animation:bob 1.4s ease-in-out infinite alternate}
@keyframes bob{from{transform:scaleY(.35)}to{transform:scaleY(1)}}
.pulse{animation:pulse 2.2s ease-in-out infinite}@keyframes pulse{0%,100%{opacity:.18}50%{opacity:.9}}
.ring{transform-box:fill-box;transform-origin:center;animation:ring 2s ease-out infinite}
@keyframes ring{from{transform:scale(.5);opacity:.9}to{transform:scale(2.8);opacity:0}}
.sweep{animation:sweep 3s ease-in-out infinite alternate}@keyframes sweep{to{transform:translateX(44px)}}
.nudge{animation:nudge 1.3s ease-in-out infinite alternate}
@keyframes nudge{to{transform:translate(2px,-2px)}}
.spin{transform-box:fill-box;transform-origin:center;animation:spin 40s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.blink{animation:blink 1s steps(1) infinite}@keyframes blink{50%{opacity:0}}
.trace{stroke-dasharray:1;stroke-dashoffset:1;animation:trace 1.8s ease-in-out forwards}
@keyframes trace{0%{stroke-dashoffset:1;opacity:1}70%{stroke-dashoffset:0;opacity:1}
 100%{stroke-dashoffset:0;opacity:0}}
.cnt{visibility:hidden}
@media (prefers-reduced-motion: reduce){ __FINAL__ }
"""
FINAL_CSS = """
.up,.fade,.tilt,.rise,.pop,.grow,.fillx,.draw,.redraw,.bob,.pulse,.sweep,.nudge,.spin,.tape{
 animation:none!important;opacity:1!important;transform:none!important;stroke-dashoffset:0!important}
.ring,.trace,.blink{display:none}
.cnt{display:none}.cnt.final{display:inline;visibility:visible!important}
"""
BASE_CSS = BASE_CSS.replace("__FINAL__", FINAL_CSS)
STATIC_CSS = FINAL_CSS


def svg(h: int, body: str, fams: list[str], extra_css: str = "", bg: bool = True, w: int = W) -> str:
    css = "".join(font_face(f) for f in fams) + BASE_CSS + extra_css + (STATIC_CSS if STATIC else "")
    frame = (f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="14" fill="{CARD_BG}" '
             f'stroke="{LINE}"/>') if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f"<style>{css}</style>{frame}{body}</svg>")


def d(delay: float) -> str:
    return f'style="animation-delay:{delay:.2f}s"'


def count_up(x, y, value: int, cls: str, attrs: str, begin: float, dur: float = 1.2, frames: int = 14) -> str:
    """Count-up number: CSS can't change text, so stack SMIL-toggled frames."""
    out = []
    for i in range(frames + 1):
        t = i / frames
        v = round(value * (1 - (1 - t) ** 3))
        start = begin + dur * t
        final = i == frames
        anim = f'<set attributeName="visibility" to="visible" begin="{start:.2f}s"'
        anim += ' fill="freeze"/>' if final else f' end="{begin + dur * (i + 1) / frames:.2f}s"/>'
        out.append(f'<text x="{x}" y="{y}" class="cnt {cls}{" final" if final else ""}" {attrs}>'
                   f'{v:,}{anim}</text>')
    return "".join(out)


def ring_dot(cx, cy, color, delay, r=3.2) -> str:
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="none" stroke="{color}" stroke-width="1.2" '
            f'class="ring" {d(delay)}/><circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{color}" '
            f'class="fade" {d(delay - .3)}/>')


# ───────────────────────────── data ─────────────────────────────
def load_data() -> dict:
    return json.loads((ROOT / "data" / "github.json").read_text())


def stats(days: list[dict]) -> dict:
    counts = [x["count"] for x in days]
    longest = cur = 0
    for c in counts:
        cur = cur + 1 if c > 0 else 0
        longest = max(longest, cur)
    current = 0
    for c in reversed(counts[:-1] if counts and counts[-1] == 0 else counts):
        if c == 0:
            break
        current += 1
    months: dict = {}
    for x in days:
        months[x["date"][:7]] = months.get(x["date"][:7], 0) + x["count"]
    return {"active": sum(1 for c in counts if c > 0), "longest": longest, "current": current,
            "months": sorted(months.items())[-12:], "days": len(counts)}


# ───────────────────────────── cards ─────────────────────────────
def portrait(px: float, py: float, start: float) -> str:
    p = ROOT / "data" / f"portrait-{PORTRAIT_STYLE}.json"
    if not p.exists():
        return ""
    pd = json.loads(p.read_text())
    out = [f'<circle cx="{px + pd["w"]*.52:.0f}" cy="{py + pd["h"]*.46:.0f}" r="{pd["w"]*.47:.0f}" fill="none" '
           f'stroke="{GOLD}" stroke-width="1.2" stroke-dasharray="2 7" stroke-linecap="round" '
           f'class="spin fade" {d(start)}/>']
    if pd["style"] == "halftone":
        # dots "print" row by row
        rows = pd["rows"]
        for i, row in enumerate(rows):
            dots = "".join(f'<circle cx="{px+x:.1f}" cy="{py+y:.1f}" r="{r}"/>' for x, y, r in row)
            out.append(f'<g class="pop" {d(start + i * 1.6 / len(rows))}>{dots}</g>')
        return f'<g clip-path="url(#card)" fill="url(#shine)">{"".join(out)}</g>'

    if pd["style"] == "ascii":
        # terminal print: each row types out left to right while a cursor walks down the rows
        size, lh, rows = pd["size"], pd["lh"], pd["rows"]
        cw = size * 0.6
        per, typ = 1.9 / len(rows), .16
        for i, row in enumerate(rows):
            if not row.strip():
                continue
            y = py + (i + 1) * lh
            t = start + i * per
            text = (f'<text x="{px:.1f}" y="{y:.1f}" xml:space="preserve" class="mono" font-size="{size}" '
                    f'letter-spacing="0">{escape(row)}</text>')
            if STATIC:
                out.append(text)
            else:
                full = len(row) * cw + 2
                out.append(f'<clipPath id="r{i}"><rect x="{px-1:.1f}" y="{y-lh:.1f}" height="{lh+1.5:.1f}" width="0">'
                           f'<animate attributeName="width" from="0" to="{full:.1f}" dur="{typ}s" begin="{t:.2f}s" '
                           f'fill="freeze"/></rect></clipPath><g clip-path="url(#r{i})">{text}</g>')
        if not STATIC:
            ys = ";".join(f"{py + i*lh + 1:.1f}" for i in range(len(rows)))
            xs = ";".join(f"{px + len(r)*cw + 1:.1f}" for r in rows)
            dur = per * len(rows)
            out.append(f'<rect width="{cw:.1f}" height="{lh:.1f}" fill="{GOLD}" class="blink" x="{px}" y="{py}">'
                       f'<animate attributeName="y" values="{ys}" calcMode="discrete" dur="{dur:.2f}s" '
                       f'begin="{start:.2f}s" fill="freeze"/>'
                       f'<animate attributeName="x" values="{xs}" calcMode="discrete" dur="{dur:.2f}s" '
                       f'begin="{start:.2f}s" fill="freeze"/></rect>')
        return f'<g clip-path="url(#card)" fill="url(#shine)">{"".join(out)}</g>'

    # line art: every contour sketches itself in, top to bottom
    paths = pd["paths"]
    for i, pth in enumerate(paths):
        dur = min(1.5, .35 + pth["len"] / 260)
        out.append(f'<path d="{pth["d"]}" pathLength="1" fill="none" '
                   f'stroke-width="{pth["w"]}" stroke-linecap="round" stroke-linejoin="round" class="draw" '
                   f'style="animation-delay:{start + i * 2.0 / len(paths):.2f}s;animation-duration:{dur:.2f}s"/>')
    ring, lines = out[0], "".join(out[1:])
    return (f'<g clip-path="url(#card)">{ring}<g transform="translate({px} {py})" stroke="url(#shine)">'
            f'{lines}</g></g>')


def hero() -> str:
    h = 280
    b = [f'<defs><clipPath id="card"><rect x="1" y="1" width="{W-2}" height="{h-2}" rx="13"/></clipPath>'
         f'<linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W}" y2="0"'
         f' gradientTransform="translate(-{W} 0)">'
         f'<stop offset="0" stop-color="{INK}"/><stop offset=".43" stop-color="{INK}"/>'
         f'<stop offset=".5" stop-color="{GOLD}"/><stop offset=".57" stop-color="{INK}"/>'
         f'<stop offset="1" stop-color="{INK}"/>'
         + ("" if STATIC else
            f'<animateTransform attributeName="gradientTransform" type="translate" '
            f'values="-{W} 0;{W} 0;{W} 0" keyTimes="0;.4;1" dur="6s" begin="2.6s" repeatCount="indefinite"/>')
         + "</linearGradient></defs>"]

    # 1. "$ whoami" typed out with a moving cursor
    cmd, x0, y0 = "$ whoami", 48, 60
    cw = text_w("a", "Mono", 14)
    full = cw * len(cmd)
    t0, per = .25, .08
    if STATIC:
        b.append(f'<text x="{x0}" y="{y0}" class="mono" font-size="14" fill="{MUTED}">{cmd}</text>')
    else:
        vals = ";".join(f"{cw*i:.1f}" for i in range(len(cmd) + 1))
        xs = ";".join(f"{x0 + cw*i + 2:.1f}" for i in range(len(cmd) + 1))
        dur = per * len(cmd)
        b.append(f'<clipPath id="type"><rect x="{x0-2}" y="{y0-16}" height="22" width="0">'
                 f'<animate attributeName="width" values="{vals}" dur="{dur:.2f}s" begin="{t0}s" '
                 f'calcMode="discrete" fill="freeze"/></rect></clipPath>'
                 f'<text x="{x0}" y="{y0}" class="mono" font-size="14" fill="{MUTED}" clip-path="url(#type)">{cmd}</text>'
                 f'<rect x="{x0}" y="{y0-13}" width="8" height="16" fill="{GOLD}" class="blink">'
                 f'<animate attributeName="x" values="{xs}" dur="{dur:.2f}s" begin="{t0}s" '
                 f'calcMode="discrete" fill="freeze"/></rect>')

    # 2. name: each letter rises in, then the gold shine sweeps across it (and the portrait)
    x, start = 44.0, t0 + per * len(cmd) + .2
    for i, ch in enumerate(NAME):
        if ch != " ":
            b.append(f'<text x="{x:.1f}" y="136" class="serif rise" font-size="68" fill="url(#shine)" '
                     f'{d(start + i*.045)}>{escape(ch)}</text>')
        x += text_w(ch, "Serif", 68)

    # 3. taglines + tags
    t = start + len(NAME) * .045 + .2
    for i, line in enumerate(TAGLINES):
        b.append(f'<text x="48" y="{178 + i*25}" class="sans up" font-size="16" fill="{INK if i==0 else MUTED}" '
                 f'{d(t + i*.18)}>{escape(line)}</text>')
    tx = 48.0
    for j, k in enumerate(ACCENT):
        label = LABEL[k].lower()
        b.append(f'<g class="pop" {d(t + .5 + j*.12)}><circle cx="{tx+4:.1f}" cy="{240}" r="4" fill="{ACCENT[k]}"/>'
                 f'<text x="{tx+13:.1f}" y="244" class="mono" font-size="12" fill="{MUTED}">{label}</text></g>')
        tx += 13 + text_w(label, "Mono", 12) + 20
    b.append(f'<text x="{tx+6:.1f}" y="244" class="mono fade" font-size="12" fill="{FAINT}" {d(t + 1.1)}>'
             f'{HANDLE}  ·  {LOCATION}</text>')

    # 4. halftone portrait on the right
    b.append(portrait(588, 44, .3))
    return svg(h, "".join(b), ["Serif", "Sans", "Mono"])


def ticker() -> str:
    h = 46
    items, x = [], 22.0
    loop = 0.0
    for rep in range(2):
        for i, word in enumerate(TICKER):
            up = (i * 7) % 5 != 0
            chg = f"{'+' if up else '-'}{(i * 37 % 41) / 10 + .4:.1f}%"
            items.append(f'<text x="{x:.1f}" y="29" class="mono" font-size="13" fill="{INK}">{word}</text>')
            x += text_w(word, "Mono", 13) + 8
            col = ACCENT["fin"] if up else "#B4483A"
            items.append(f'<text x="{x:.1f}" y="29" class="mono" font-size="11" fill="{col}">'
                         f'{"▲" if up else "▼"} {chg}</text>')
            x += text_w(f"▲ {chg}", "Mono", 11) + 28
        if rep == 0:
            loop = x - 22.0
    css = (f".tape{{animation:tape {loop/40:.1f}s linear infinite}}"
           f"@keyframes tape{{to{{transform:translateX(-{loop:.1f}px)}}}}")
    body = (f'<clipPath id="c"><rect x="1" y="1" width="{W-2}" height="{h-2}" rx="13"/></clipPath>'
            f'<g clip-path="url(#c)"><g class="tape">{"".join(items)}</g></g>')
    return svg(h, body, ["Mono"], css)


def pillar_icon(k: str, ix: float, iy: float, c: str, t: float) -> str:
    """Small looping illustration for each pillar (54 x 30 box)."""
    if k == "data":
        hs = [.5, .85, .6, 1, .72]
        return "".join(
            f'<rect x="{ix + j*11:.1f}" y="{iy + 30 - 30*v:.1f}" width="7" height="{30*v:.1f}" rx="1.5" fill="{c}" '
            f'class="bob" style="animation-delay:{t + j*.18:.2f}s;animation-duration:{1.1 + j*.17:.2f}s"/>'
            for j, v in enumerate(hs))
    if k == "ai":
        layers = [[iy + 8, iy + 22], [iy + 2, iy + 15, iy + 28], [iy + 15]]
        xs = [ix + 4, ix + 27, ix + 50]
        out, n = [], 0
        for L in range(2):
            for y1 in layers[L]:
                for y2 in layers[L + 1]:
                    out.append(f'<line x1="{xs[L]}" y1="{y1}" x2="{xs[L+1]}" y2="{y2}" stroke="{c}" '
                               f'stroke-width="1.2" class="pulse" {d(t + n*.17)}/>')
                    n += 1
        for L, ys in enumerate(layers):
            out += [f'<circle cx="{xs[L]}" cy="{y}" r="3.2" fill="{c}"/>' for y in ys]
        out.append(f'<circle cx="{xs[2]}" cy="{layers[2][0]}" r="3.2" fill="none" stroke="{c}" class="ring" {d(t+.5)}/>')
        return "".join(out)
    if k == "fin":
        ys = [24, 20, 22, 14, 16, 8, 3]
        pts = " ".join(f"{ix + j*9:.1f},{iy + y}" for j, y in enumerate(ys))
        return (f'<polyline points="{pts}" pathLength="1" fill="none" stroke="{c}" stroke-width="2" '
                f'stroke-linejoin="round" stroke-linecap="round" class="redraw" {d(t)}/>'
                f'<line x1="{ix}" x2="{ix+54}" y1="{iy+30}" y2="{iy+30}" stroke="{LINE}"/>'
                + ring_dot(ix + 54, iy + 3, c, t + 1.9, 2.6))
    # quant: bell curve with a sweeping marker
    import math
    pts = [(ix + j * 2.7, iy + 29 - 26 * math.exp(-((j - 10) / 4.2) ** 2)) for j in range(21)]
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return (f'<path d="{path} L{ix+54},{iy+29} L{ix},{iy+29}Z" fill="{c}" fill-opacity=".12" class="fade" {d(t)}/>'
            f'<path d="{path}" pathLength="1" fill="none" stroke="{c}" stroke-width="2" class="redraw" {d(t)}/>'
            f'<line x1="{ix+5}" x2="{ix+5}" y1="{iy}" y2="{iy+30}" stroke="{INK}" stroke-width="1" '
            f'stroke-dasharray="2 2" class="sweep" {d(t + .4)}/>')


def pillars() -> str:
    h = 196
    b = [f'<text x="28" y="40" class="mono fade" font-size="12" fill="{MUTED}" letter-spacing="1.5">WHAT I WORK ON</text>']
    tw, gap, x0 = 186, 12, 28
    for i, (title, k, blurb) in enumerate(PILLARS):
        x = x0 + i * (tw + gap)
        c = ACCENT[k]
        delay = .25 + i * .14
        g = [f'<rect x="{x}" y="58" width="{tw}" height="116" rx="10" fill="{PAPER}" stroke="{LINE}"/>',
             f'<rect x="{x+14}" y="58" width="{tw-28}" height="3" rx="1.5" fill="{c}" class="fillx" {d(delay+.4)}/>',
             f'<text x="{x+16}" y="102" class="serif" font-size="32" fill="{INK}">{title}</text>']
        for j, line in enumerate(wrap(blurb, "Sans", 12.5, tw - 32)):
            g.append(f'<text x="{x+16}" y="{128 + j*17}" class="sans" font-size="12.5" fill="{MUTED}">{escape(line)}</text>')
        b.append(f'<g class="tilt" {d(delay)}>{"".join(g)}</g>')
        b.append(f'<g class="fade" {d(delay + .5)}>{pillar_icon(k, x + tw - 70, 74, c, delay + .8)}</g>')
    return svg(h, "".join(b), ["Serif", "Sans", "Mono"])


def stat_tiles(data: dict, s: dict) -> str:
    h = 132
    months = [v for _, v in s["months"]]
    vals = [(data["total_contributions"], "CONTRIBUTIONS · 12 MO", "data"),
            (data["public_repos"], "PUBLIC REPOS", "ai"),
            (s["longest"], "LONGEST STREAK · DAYS", "fin"),
            (s["active"], "ACTIVE DAYS", "quant")]
    tw, gap, x0 = 186, 12, 28
    b = []
    for i, (v, label, k) in enumerate(vals):
        x = x0 + i * (tw + gap)
        c = ACCENT[k]
        delay = .2 + i * .14
        b.append(f'<g class="tilt" {d(delay)}><rect x="{x}" y="22" width="{tw}" height="88" rx="10" fill="{PAPER}" '
                 f'stroke="{LINE}"/><rect x="{x}" y="34" width="3" height="64" rx="1.5" fill="{c}"/>'
                 f'<text x="{x+18}" y="96" class="mono" font-size="10.5" fill="{MUTED}" letter-spacing="1">{label}</text></g>')
        b.append(count_up(x + 18, 74, v, "serif", f'font-size="42" fill="{INK}"', begin=delay + .35))
        vx, vy, vw = x + tw - 74, 40, 58        # mini viz box
        t = delay + .6
        if k == "data" and months:
            peak = max(months + [1])
            pts = [(vx + j * vw / (len(months) - 1), vy + 26 - 24 * m / peak) for j, m in enumerate(months)]
            b.append(f'<polyline points="{" ".join(f"{a:.1f},{b_:.1f}" for a, b_ in pts)}" pathLength="1" fill="none" '
                     f'stroke="{c}" stroke-width="1.6" stroke-linejoin="round" class="draw" {d(t)}/>')
            b.append(ring_dot(*pts[-1], c, t + 1.8, 2.4))
        elif k == "ai":
            n = min(v, 12)
            b += [f'<rect x="{vx + (j % 4)*15:.0f}" y="{vy + 2 + (j // 4)*13}" width="10" height="10" rx="2.5" '
                  f'fill="{c}" fill-opacity="{.9 - .06*j:.2f}" class="pop" {d(t + j*.12)}/>' for j in range(n)]
        else:
            frac = (s["current"] / max(s["longest"], 1)) if k == "fin" else s["active"] / max(s["days"], 1)
            note = f'now {s["current"]}' if k == "fin" else f'{frac:.0%} of days'
            b.append(f'<text x="{vx+vw}" y="{vy+12}" text-anchor="end" class="mono fade" font-size="10" '
                     f'fill="{MUTED}" {d(t + .8)}>{note}</text>'
                     f'<rect x="{vx}" y="{vy+20}" width="{vw}" height="5" rx="2.5" fill="{LINE}" class="fade" {d(t)}/>'
                     f'<rect x="{vx}" y="{vy+20}" width="{max(vw*frac, 5):.1f}" height="5" rx="2.5" fill="{c}" '
                     f'class="fillx" {d(t + .2)}/>')
    return svg(h, "".join(b), ["Serif", "Mono"])


def activity(s: dict) -> str:
    h = 262
    months = s["months"]
    vals = [v for _, v in months]
    peak = max(vals + [1])
    avg = sum(vals) / max(len(vals), 1)
    b = [f'<text x="28" y="48" class="serif up" font-size="30" fill="{INK}" {d(0)}>A year at the keyboard</text>',
         f'<text x="{W-28}" y="46" text-anchor="end" class="mono fade" font-size="11" fill="{MUTED}" {d(.2)}>'
         f'MONTHLY CONTRIBUTIONS · UPDATED DAILY</text>']
    base, top, x0 = 212, 84, 40
    bw = (W - 2 * x0) / max(len(months), 1)
    b.append(f'<line x1="{x0}" x2="{W-x0}" y1="{base}" y2="{base}" stroke="{LINE}"/>')
    peak_i = vals.index(peak) if vals else 0
    for i, (ym, v) in enumerate(months):
        bh = max((v / peak) * (base - top), 2 if v else 0)
        x = x0 + i * bw + bw * .18
        last = i == len(months) - 1
        col = ACCENT["quant"] if last else ACCENT["data"]
        delay = .35 + i * .07
        if bh:
            b.append(f'<rect x="{x:.1f}" y="{base-bh:.1f}" width="{bw*.64:.1f}" height="{bh:.1f}" rx="4" '
                     f'fill="{col}" fill-opacity="{1 if last else .85}" class="grow" {d(delay)}/>')
        b.append(f'<text x="{x + bw*.32:.1f}" y="{base-bh-9:.1f}" text-anchor="middle" class="mono fade" '
                 f'font-size="11" fill="{INK}" {d(delay + .7)}>{v}</text>')
        if i == peak_i and v:
            b.append(ring_dot(x + bw * .32, base - bh - 26, GOLD, delay + 1.6, 3))
        mon = calendar.month_abbr[int(ym[5:])].upper()
        b.append(f'<text x="{x + bw*.32:.1f}" y="{base+22}" text-anchor="middle" class="mono fade" '
                 f'font-size="10.5" fill="{MUTED}" {d(.3)}>{mon}</text>')
    ay = base - (avg / peak) * (base - top)
    b.append(f'<line x1="{x0}" x2="{W-x0}" y1="{ay:.1f}" y2="{ay:.1f}" pathLength="1" stroke="{GOLD}" '
             f'stroke-width="1.4" stroke-dasharray="1" class="draw" {d(1.5)}/>'
             f'<text x="{x0+2}" y="{ay-6:.1f}" class="mono fade" font-size="10.5" '
             f'fill="{GOLD}" {d(2.6)}>avg {avg:.0f}</text>')
    return svg(h, "".join(b), ["Serif", "Mono"])


def project(i: int, repo: str, k: str, blurb: str, meta: dict) -> str:
    w, h = 412, 168
    title = TITLES.get(repo, " ".join(p.capitalize() for p in repo.split("-")).replace(" And ", " and "))
    c = ACCENT[k]
    size = 25
    while text_w(title, "Serif", size) > w - 60 and size > 17:
        size -= 1
    t = .2 + (i % 2) * .2
    b = [f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="14" fill="{CARD_BG}" stroke="{LINE}" '
         f'class="fade" {d(t + .6)}/>',
         f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="13.5" fill="none" stroke="{c}" stroke-width="1.6" '
         f'pathLength="1" class="trace" {d(t)}/>',
         f'<g class="up" {d(t + .5)}><rect x="22" y="24" width="{text_w(LABEL[k], "Mono", 10)+18:.0f}" height="20" '
         f'rx="10" fill="{c}" fill-opacity=".12"/>'
         f'<text x="31" y="38" class="mono" font-size="10" fill="{c}" letter-spacing=".5">{LABEL[k]}</text></g>',
         f'<g class="fade" {d(t + .9)}><text x="{w-24}" y="40" text-anchor="end" class="sans nudge" font-size="18" '
         f'fill="{MUTED}">↗</text></g>',
         f'<text x="22" y="78" class="serif up" font-size="{size}" fill="{INK}" {d(t + .6)}>{escape(title)}</text>']
    for j, line in enumerate(wrap(meta.get("description") or blurb, "Sans", 13, w - 44)[:2]):
        b.append(f'<text x="22" y="{104 + j*18}" class="sans up" font-size="13" fill="{MUTED}" '
                 f'{d(t + .75 + j*.08)}>{escape(line)}</text>')
    foot = f'<text x="22" y="148" class="mono" font-size="11" fill="{FAINT}">{repo}</text>'
    if meta.get("language"):
        lx = w - 22 - text_w(meta["language"], "Mono", 11)
        foot += (f'<circle cx="{lx-10:.1f}" cy="144" r="4" fill="{c}"/>'
                 f'<text x="{w-22}" y="148" text-anchor="end" class="mono" font-size="11" fill="{MUTED}">{meta["language"]}</text>')
    b.append(f'<g class="fade" {d(t + 1)}>{foot}</g>')
    return svg(h, "".join(b), ["Serif", "Sans", "Mono"], bg=False, w=w)


def main() -> None:
    data = load_data()
    s = stats(data["days"])
    out = ROOT / "cards"
    out.mkdir(exist_ok=True)
    repos = {r["name"]: r for r in data.get("repos", [])}
    files = {"hero.svg": hero(), "ticker.svg": ticker(), "pillars.svg": pillars(),
             "stats.svg": stat_tiles(data, s), "activity.svg": activity(s)}
    for i, (repo, k, blurb) in enumerate(PROJECTS):
        files[f"project-{i+1}.svg"] = project(i, repo, k, blurb, repos.get(repo, {}))
    for name, content in files.items():
        (out / name).write_text(content)
        print(f"{name:16} {len(content)/1024:6.1f} KB")


if __name__ == "__main__":
    main()
