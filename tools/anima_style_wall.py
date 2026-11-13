# -*- coding: utf-8 -*-
"""把画师预览图拼成对比墙（含量化指标），用于肉眼选画风。"""
import json, os, sys
from PIL import Image, ImageDraw

META = r"D:\ComfyUI\logs\anima_style_metrics.json"
OUT_DIR = r"D:\ComfyUI\logs"
CELL = 300
COLS = 4
PAD = 8
BAR = 26


def build(tags=None, out_name="anima_style_wall.png", sort_key="works"):
    d = [x for x in json.load(open(META, encoding="utf-8")) if x.get("lum") and os.path.exists(x.get("file", ""))]
    if tags:
        want = [t.lower() for t in tags]
        d = [x for x in d if any(w in x["tag"].lower() for w in want)]
    d.sort(key=lambda x: -x.get(sort_key, 0))
    if not d:
        print("no entries")
        return None
    rows = (len(d) + COLS - 1) // COLS
    W = COLS * (CELL + PAD) + PAD
    H = rows * (CELL + BAR + PAD) + PAD
    canvas = Image.new("RGB", (W, H), (18, 18, 20))
    dr = ImageDraw.Draw(canvas)
    for i, x in enumerate(d):
        r, c = divmod(i, COLS)
        px = PAD + c * (CELL + PAD)
        py = PAD + r * (CELL + BAR + PAD)
        try:
            im = Image.open(x["file"]).convert("RGB")
        except Exception:
            continue
        im.thumbnail((CELL, CELL))
        canvas.paste(im, (px + (CELL - im.width) // 2, py + (CELL - im.height) // 2))
        label = "%s  w%d" % (x["tag"][:30], x["works"])
        vals = "L%.0f C%.0f S%.0f" % (x["lum"], x["contrast"], x["sat"])
        dr.text((px + 4, py + CELL + 2), label, fill=(235, 235, 235))
        dr.text((px + 4, py + CELL + 13), vals, fill=(150, 200, 255))
    out = os.path.join(OUT_DIR, out_name)
    canvas.save(out, quality=90)
    print("WALL ->", out, canvas.size)
    return out


if __name__ == "__main__":
    tags = sys.argv[1].split(",") if len(sys.argv) > 1 and sys.argv[1] != "-" else None
    build(tags)
