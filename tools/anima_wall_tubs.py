# -*- coding: utf-8 -*-
"""画师桶对比墙：标签 = [编号] @画师名，不打色彩指标。
用法: python anima_wall_tubs.py <清单json> <输出名> <列数> [标题]
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

SRC = r"D:\ComfyUI\_style_test"
DROP = r"D:\Tailscale传文件"
LIST = sys.argv[1]
outname = sys.argv[2]
COLS = int(sys.argv[3]) if len(sys.argv) > 3 else 5
TITLE = sys.argv[4] if len(sys.argv) > 4 else ""
BAR = 66
PAD = 14


def font(sz):
    for p in [r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


rows = json.load(open(LIST, encoding="utf-8"))
pairs = []
for r in rows:
    p = os.path.join(SRC, r["file"]) if r.get("file") else None
    if p and os.path.exists(p):
        pairs.append((p, r))
    elif p:
        print("MISSING %s (标号 %s %s)" % (r.get("file"), r.get("idx"), r.get("tag")))
if not pairs:
    print("NO FILE")
    sys.exit(1)

imgs = [Image.open(p).convert("RGB") for p, _ in pairs]
cw = max(i.width for i in imgs)
ch = max(i.height for i in imgs)
nrows = (len(imgs) + COLS - 1) // COLS
HEAD = 74 if TITLE else 0
W = COLS * (cw + PAD) + PAD
H = HEAD + nrows * (ch + BAR + PAD) + PAD
canvas = Image.new("RGB", (W, H), (12, 12, 14))
dr = ImageDraw.Draw(canvas)
F_LABEL = font(34)
F_SM = font(20)
F_TITLE = font(42)

if TITLE:
    dr.text((PAD + 6, 18), TITLE, fill=(245, 245, 245), font=F_TITLE)

for i, (im, (p, r)) in enumerate(zip(imgs, pairs)):
    rr, cc = divmod(i, COLS)
    x = PAD + cc * (cw + PAD)
    y = HEAD + PAD + rr * (ch + BAR + PAD)
    canvas.paste(im, (x, y))
    dr.text((x + 10, y + ch + 6), "%d" % r["idx"], fill=(255, 210, 90), font=F_LABEL)
    tw = dr.textlength("%d" % r["idx"], font=F_LABEL)
    dr.text((x + 16 + tw, y + ch + 12), r["tag"], fill=(240, 240, 240), font=F_LABEL)
    dr.text((x + 10, y + ch + 44), "%d 图" % r["count"], fill=(130, 130, 140), font=F_SM)

os.makedirs(DROP, exist_ok=True)
out = os.path.join(DROP, outname)
canvas.save(out)
print("WALL -> %s %s %.1fMB" % (out, canvas.size, os.path.getsize(out) / 1048576))
