# -*- coding: utf-8 -*-
"""给 18 条 AI 拟人角色生成缩略图，落到插件 presets/user_thumbs/<thumb_slug>.jpg。
每个角色用自己的 LoRA + wb_chars.json 里的 g 标签，统一半身白底构图。
"""
import json, os, subprocess, sys, shutil

sys.stdout.reconfigure(encoding="utf-8")

PY = r"D:\ComfyUI\ComfyUI_windows_portable\python_embeded\python.exe"
RUN = r"D:\ComfyUI\tools\anima_run_char.py"
CJ = r"D:\ComfyUI\ComfyUI_windows_portable\ComfyUI\custom_nodes\Comfyui-Anima-Wardrobe-V5\presets\anima_v4_characters.json"
WB = r"D:\ComfyUI\webui\data\wb_chars.json"
OUT_DIR = r"D:\ComfyUI\_style_test\musume_thumbs"
THUMB_DIR = r"D:\ComfyUI\ComfyUI_windows_portable\ComfyUI\custom_nodes\Comfyui-Anima-Wardrobe-V5\presets\user_thumbs"

c = json.load(open(CJ, encoding="utf-8"))
wb = json.load(open(WB, encoding="utf-8"))
gmap = {x["t"]: x.get("g") or [] for x in wb["chars"] if x.get("w") == "ai_gijinka"}

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)

EXTRA = ", upper body, portrait, white background, simple background, looking at viewer"

plan = []
for x in c["characters"]:
    if x.get("work") != "ai_gijinka":
        continue
    tags = gmap.get(x["tag"]) or list(x.get("tags") or [])
    seen, clean = set(), []
    for t in tags:
        k = t.strip().lower()
        if k and k not in seen:
            seen.add(k)
            clean.append(t.strip())
    prompt = ", ".join(clean) + EXTRA
    plan.append({
        "tag": x["tag"],
        "thumb": x.get("thumb") or x["tag"],
        "lora": x.get("lora"),
        "w": x.get("lora_w") or 1.0,
        "prompt": prompt,
    })

print("待生成 %d 张" % len(plan))
ok = fail = 0
for i, p in enumerate(plan, 1):
    slug = p["tag"]
    print("[%2d/%d] %s  thumb=%s  lora=%s@%.2f" % (i, len(plan), slug, p["thumb"], os.path.basename(p["lora"] or "-"), p["w"]))
    cmd = [PY, RUN, "musume_thumbs", slug, p["prompt"], "--seed", "20251114",
           "--lora", "%s|%.2f" % (p["lora"], p["w"])]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("   FAIL", (r.stdout or "")[-200:], (r.stderr or "")[-300:])
        fail += 1
        continue
    f = os.path.join(OUT_DIR, slug + "_00001_.png")
    if not os.path.exists(f):
        cands = sorted([x for x in os.listdir(OUT_DIR) if x.startswith(slug)])
        if not cands:
            print("   MISS 输出文件")
            fail += 1
            continue
        f = os.path.join(OUT_DIR, cands[-1])
    from PIL import Image
    im = Image.open(f).convert("RGB")
    im.thumbnail((320, 320), Image.LANCZOS)
    dst = os.path.join(THUMB_DIR, p["thumb"] + ".jpg")
    im.save(dst, quality=88)
    print("   -> %s (%dx%d, %d B)" % (os.path.basename(dst), im.width, im.height, os.path.getsize(dst)))
    ok += 1

print("\n完成 %d 成功 / %d 失败，目录 %s" % (ok, fail, THUMB_DIR))
have = set(os.path.splitext(f)[0] for f in os.listdir(THUMB_DIR))
missing = [p["thumb"] for p in plan if p["thumb"] not in have]
print("缺失 slug:", missing or "无")
