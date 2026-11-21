"""One-off: turn a photo into portrait data for the hero card.

    pip install "rembg[cpu]" pillow numpy scikit-image
    python scripts/make_portrait.py path/to/photo.jpg

Writes data/portrait-halftone.json, data/portrait-ascii.json and data/portrait-line.json.
Pick one with PORTRAIT_STYLE in render_readme_cards.py. Re-run only when the photo changes;
the daily Action just reads the JSON.
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOX_W, BOX_H = 232, 262            # portrait area in the hero card (px)
CROP = (0.02, 0.10, 1.0, 0.66)     # left, top, right, bottom as fractions of the photo
SS = 3                             # supersampling of the working image


def prepare(src: str):
    from rembg import new_session, remove

    im = Image.open(src).convert("RGB")
    cut = remove(im, session=new_session("u2net_human_seg"))
    w, h = cut.size
    cut = cut.crop((int(CROP[0] * w), int(CROP[1] * h), int(CROP[2] * w), int(CROP[3] * h)))
    scale = min(BOX_W / cut.width, BOX_H / cut.height)
    cut = cut.resize((round(cut.width * scale * SS), round(cut.height * scale * SS)), Image.LANCZOS)
    alpha_img = cut.getchannel("A")
    alpha = np.asarray(alpha_img, dtype=float) / 255
    # equalise only inside the person so the face gets the full tonal range
    gray = ImageOps.equalize(cut.convert("L"), mask=alpha_img.point(lambda a: 255 if a > 90 else 0))
    lum = np.asarray(gray, dtype=float) / 255
    edges = np.asarray(gray.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1.2)), dtype=float) / 255
    a_edge = np.asarray(alpha_img.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(2)), dtype=float) / 255
    return gray, lum, alpha, edges, a_edge


def halftone(lum, alpha, edges, a_edge, step=4.0):
    tone = np.clip((1 - lum) ** 1.7 + 0.9 * edges + 0.8 * a_edge, 0, 1) * (alpha > 0.35)
    H, W = tone.shape
    rows, r_max, y, ri = [], step * 0.62, step / 2, 0
    while y < H / SS:
        row, x = [], step / 2 + (step / 2 if ri % 2 else 0)
        while x < W / SS:
            r = r_max * tone[min(int(y * SS), H - 1), min(int(x * SS), W - 1)] ** 0.8
            if r > 0.35:
                row.append([round(x, 1), round(y, 1), round(r, 2)])
            x += step
        if row:
            rows.append(row)
        y += step * 0.866
        ri += 1
    return {"style": "halftone", "w": round(W / SS), "h": round(H / SS), "rows": rows}


def ascii_art(lum, alpha, edges, a_edge, size=7.4):
    ramp = " .:-=+*#%@"                       # light -> dark, no XML-special characters
    cw, lh = size * 0.6, size * 1.02          # Geist Mono advance is 0.6em
    tone = np.clip((1 - lum) ** 1.35 + 0.8 * edges + 0.9 * a_edge, 0, 1)
    H, W = tone.shape
    rows = []
    for r in range(int(H / SS / lh)):
        line = []
        for c in range(int(W / SS / cw)):
            ys, xs = int(r * lh * SS), int(c * cw * SS)
            cell_a = alpha[ys:ys + int(lh * SS), xs:xs + int(cw * SS)].mean()
            t = tone[ys:ys + int(lh * SS), xs:xs + int(cw * SS)].mean()
            line.append(" " if cell_a < 0.4 else ramp[min(int(t * len(ramp)), len(ramp) - 1)])
        rows.append("".join(line).rstrip())
    return {"style": "ascii", "w": round(W / SS), "h": round(H / SS), "size": size, "lh": lh, "rows": rows}


def line_art(gray, alpha):
    from skimage import measure

    g = np.asarray(gray.filter(ImageFilter.GaussianBlur(4.5)), dtype=float) / 255
    g = np.where(alpha > 0.4, g, 1.0)
    paths = []

    def add(contours, weight, min_len):
        for c in contours:
            c = measure.approximate_polygon(c, tolerance=1.1)
            pts = c[:, ::-1] / SS
            length = np.sum(np.hypot(*np.diff(pts, axis=0).T)) if len(pts) > 1 else 0
            if length >= min_len:
                d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
                paths.append({"d": d, "w": weight, "y": float(pts[:, 1].min()), "len": float(length)})

    add(measure.find_contours(np.asarray(Image.fromarray((alpha * 255).astype("uint8"))
                                         .filter(ImageFilter.GaussianBlur(2)), dtype=float) / 255, 0.5), 1.6, 60)
    for level, weight, min_len in [(0.17, 1.3, 16), (0.36, 0.85, 30)]:
        add(measure.find_contours(g, level), weight, min_len)
    paths.sort(key=lambda p: p["y"])          # draw top to bottom
    H, W = g.shape
    return {"style": "line", "w": round(W / SS), "h": round(H / SS), "paths": paths}


def main(src: str) -> None:
    gray, lum, alpha, edges, a_edge = prepare(src)
    outs = {
        "halftone": halftone(lum, alpha, edges, a_edge),
        "ascii": ascii_art(lum, alpha, edges, a_edge),
        "line": line_art(gray, alpha),
    }
    for name, data in outs.items():
        p = ROOT / "data" / f"portrait-{name}.json"
        p.write_text(json.dumps(data, separators=(",", ":")))
        print(f"{p.name:24} {p.stat().st_size/1024:6.1f} KB")


if __name__ == "__main__":
    if len(sys.argv) == 6:              # optional: photo left top right bottom
        CROP = tuple(float(v) for v in sys.argv[2:6])
    main(sys.argv[1])
