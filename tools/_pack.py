# -*- coding: utf-8 -*-
"""打发行包 anima-workbench-v4.0.zip（白名单，只打运行所需 + 画风库）。"""
import os, zipfile, json

ROOT = r"D:\ComfyUI"
OUT_DIR = os.path.join(ROOT, "dist")
OUT = os.path.join(OUT_DIR, "anima-workbench-v4.0.zip")

FILES = [
    "README.md", "DEPLOY.md", "install.cmd", "install.ps1",
    "ComfyUI控制台.ps1", "extra_model_paths.yaml", ".gitignore",
    r"_setup\start_engine.cmd", r"_setup\start_assistant.cmd",
    r"_setup\start_ollama.cmd", r"_setup\get_outdir.py",
    r"webui\assistant.py", r"webui\planner.py", r"webui\workbench.html",
    r"webui\anima_guide.html", r"webui\tag_zh.json", r"webui\styles.json",
    r"webui\favorites.json",
    r"docs\CHANGELOG.md",
]
TOOLS = [
    "gen_workbench.py", "build_atoms.py", "health_check.py", "comfy_proxy.py", "verify_repo.py",
    "anima_thumbs.py", "anima_build_styles_json.py", "anima_lora_inspect.py",
]
# data 全打，但排除本地运行配置
SKIP_DATA = {"wb_config.json"}

os.makedirs(OUT_DIR, exist_ok=True)
missing, added = [], 0
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for rel in FILES:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            missing.append(rel); continue
        z.write(p, "anima-workbench/" + rel.replace("\\", "/")); added += 1
    for name in TOOLS:
        rel = r"tools" + "\\" + name
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            missing.append(rel); continue
        z.write(p, "anima-workbench/tools/" + name); added += 1
    ddir = os.path.join(ROOT, r"webui\data")
    for name in sorted(os.listdir(ddir)):
        if not name.endswith(".json") or name in SKIP_DATA:
            continue
        z.write(os.path.join(ddir, name), "anima-workbench/webui/data/" + name); added += 1
    tdir = os.path.join(ROOT, r"webui\static\style_thumbs")
    if os.path.isdir(tdir):
        for name in sorted(os.listdir(tdir)):
            if name.lower().endswith((".jpg", ".png")):
                z.write(os.path.join(tdir, name), "anima-workbench/webui/static/style_thumbs/" + name); added += 1

size = os.path.getsize(OUT)
print("WROTE", OUT, "%.1f MB" % (size / 1048576), "files", added)
if missing:
    print("MISSING", len(missing))
    for m in missing[:20]:
        print("  ", m)
