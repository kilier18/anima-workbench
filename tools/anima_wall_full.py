# -*- coding: utf-8 -*-
"""原像素对比墙（不缩放）：把整组图按 1:1 拼起来，带标签条。
用法: python anima_wall_full.py <glob> <输出名> <列数> [标题]
"""
import glob, json, os, shutil, sys
from PIL import Image, ImageDraw, ImageFont

SRC = r"D:\ComfyUI\_style_test"
DROP = r"D:\Tailscale传文件"
pattern = sys.argv[1]
outname = sys.argv[2]
COLS = int(sys.argv[3]) if len(sys.argv) > 3 else 4
TITLE = sys.argv[4] if len(sys.argv) > 4 else ""
BAR = 56
PAD = 12


def font(sz):
    for p in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


F_LABEL = font(26)
F_SMALL = font(20)
F_TITLE = font(34)

files = sorted(glob.glob(os.path.join(SRC, pattern)))
if not files:
    print("NO FILE", pattern)
    sys.exit(1)

imgs = [Image.open(f).convert("RGB") for f in files]
cw = max(i.width for i in imgs)
ch = max(i.height for i in imgs)
nrows = (len(imgs) + COLS - 1) // COLS
HEAD = 64 if TITLE else 0
W = COLS * (cw + PAD) + PAD
H = HEAD + nrows * (ch + BAR + PAD) + PAD
canvas = Image.new("RGB", (W, H), (12, 12, 14))
dr = ImageDraw.Draw(canvas)

if TITLE:
    dr.text((PAD + 4, 14), TITLE, fill=(245, 245, 245), font=F_TITLE)

for i, (im, f) in enumerate(zip(imgs, files)):
    rr, cc = divmod(i, COLS)
    x = PAD + cc * (cw + PAD)
    y = HEAD + PAD + rr * (ch + BAR + PAD)
    canvas.paste(im, (x, y))
    nm = os.path.basename(f).replace("r3_", "").replace("_00001_.png", "")
    dr.text((x + 6, y + ch + 6), nm, fill=(235, 235, 235), font=F_LABEL)
    # 量化指标
    small = im.copy()
    small.thumbnail((192, 192))
    px = list(small.getdata())
    n = len(px)
    lum = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in px) / n
    var = sum((0.299 * r + 0.587 * g + 0.114 * b - lum) ** 2 for r, g, b in px) / n
    sat = sum(max(r, g, b) - min(r, g, b) for r, g, b in px) / n
    dr.text((x + 6 + 300, y + ch + 8), "L%.0f C%.0f S%.0f" % (lum, var ** 0.5, sat), fill=(130, 195, 255), font=F_SMALL)

os.makedirs(DROP, exist_ok=True)
out = os.path.join(DROP, outname)
canvas.save(out)
print("WALL -> %s %s %.1fMB" % (out, canvas.size, os.path.getsize(out) / 1048576))

# 只推拼好的整体对比图，单张不再复制（用户 2026-11-13 指令）
print("WALL ONLY -> %s" % DROP)
