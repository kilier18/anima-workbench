# -*- coding: utf-8 -*-
"""把误写进用户图库的 18 张角色图收回测试目录，并生成插件缩略图。"""
import json, os, shutil, sys
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

LIB = r"F:\Users\pinn\Pictures\libido\musume_thumbs"
DST = r"D:\ComfyUI\_style_test\musume_thumbs"
THUMB = r"D:\ComfyUI\ComfyUI_windows_portable\ComfyUI\custom_nodes\Comfyui-Anima-Wardrobe-V5\presets\user_thumbs"
CJ = r"D:\ComfyUI\ComfyUI_windows_portable\ComfyUI\custom_nodes\Comfyui-Anima-Wardrobe-V5\presets\anima_v4_characters.json"

c = json.load(open(CJ, encoding="utf-8"))
tmap = {x["tag"]: (x.get("thumb") or x["tag"]) for x in c["characters"] if x.get("work") == "ai_gijinka"}

os.makedirs(DST, exist_ok=True)
os.makedirs(THUMB, exist_ok=True)

ok, miss = 0, []
for f in sorted(os.listdir(LIB)):
    if not f.endswith(".png"):
        continue
    tag = f.rsplit("_00001_", 1)[0]
    src = os.path.join(LIB, f)
    shutil.move(src, os.path.join(DST, f))
    if tag == "probe":
        continue
    slug = tmap.get(tag)
    if not slug:
        miss.append(tag)
        continue
    im = Image.open(os.path.join(DST, f)).convert("RGB")
    im.thumbnail((320, 320), Image.LANCZOS)
    dst = os.path.join(THUMB, slug + ".jpg")
    im.save(dst, quality=88, optimize=True)
    print("%-24s -> %-26s %dx%d %d B" % (tag, os.path.basename(dst), im.width, im.height, os.path.getsize(dst)))
    ok += 1

try:
    if not os.listdir(LIB):
        os.rmdir(LIB)
        print("清空并删除图库目录", LIB)
except Exception as e:
    print("图库目录:", e)

have = set(os.path.splitext(x)[0] for x in os.listdir(THUMB))
print("\n生成 %d 张；user_thumbs 现有 %d；缺失: %s" % (ok, len(have), [v for v in tmap.values() if v not in have] or "无"))
print("未匹配 tag:", miss or "无")
