# -*- coding: utf-8 -*-
"""打发行包 anima-workbench-v5.0.zip（白名单，只打运行所需 + 画风缩略图 + 四份文档）。"""
import os, zipfile, hashlib, io

ROOT = r"D:\ComfyUI"
VER = "v5.0"
OUT_DIR = os.path.join(ROOT, "dist")
OUT = os.path.join(OUT_DIR, "anima-workbench-%s.zip" % VER)

FILES = [
    "README.md", "DEPLOY.md", "install.cmd", "install.ps1",
    "ComfyUI控制台.ps1", "extra_model_paths.yaml", ".gitignore",
    r"_setup\start_engine.cmd", r"_setup\start_assistant.cmd",
    r"_setup\start_ollama.cmd", r"_setup\get_outdir.py",
    r"webui\assistant.py", r"webui\planner.py", r"webui\workbench.html",
    r"webui\anima_guide.html", r"webui\tag_zh.json", r"webui\styles.json",
    r"webui\favorites.json",
    r"docs\CHANGELOG.md",
    r"docs\提示词与场景-v3.md",
    r"docs\Anima知识-v3.md",
    r"docs\multi-turn-连续动作-方案.md",
    r"docs\workbench-维护手册.md",
]
TOOLS = [
    "gen_workbench.py", "build_atoms.py", "health_check.py", "comfy_proxy.py", "verify_repo.py",
    "review_sheet.py", "gallery_8088.py", "restart_assistant.ps1",
    "anima_thumbs.py", "anima_build_styles_json.py", "anima_lora_inspect.py",
]
# data 全打，但排除本地运行配置
SKIP_DATA = {"wb_config.json"}

os.makedirs(OUT_DIR, exist_ok=True)
missing, added, total = [], 0, 0
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for rel in FILES:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            missing.append(rel); continue
        z.write(p, "anima-workbench/" + rel.replace("\\", "/")); added += 1; total += os.path.getsize(p)
    for name in TOOLS:
        rel = "tools/" + name
        p = os.path.join(ROOT, "tools", name)
        if not os.path.exists(p):
            missing.append(rel); continue
        z.write(p, "anima-workbench/" + rel); added += 1; total += os.path.getsize(p)
    ddir = os.path.join(ROOT, r"webui\data")
    for name in sorted(os.listdir(ddir)):
        if not name.endswith(".json") or name in SKIP_DATA:
            continue
        p = os.path.join(ddir, name)
        z.write(p, "anima-workbench/webui/data/" + name); added += 1; total += os.path.getsize(p)
    tdir = os.path.join(ROOT, r"webui\static\style_thumbs")
    if os.path.isdir(tdir):
        for name in sorted(os.listdir(tdir)):
            if name.lower().endswith((".jpg", ".png")):
                p = os.path.join(tdir, name)
                z.write(p, "anima-workbench/webui/static/style_thumbs/" + name); added += 1; total += os.path.getsize(p)

size = os.path.getsize(OUT)
h = hashlib.sha256()
with open(OUT, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
print("WROTE", OUT)
print("  files %d  raw %.1f MB  zip %.1f MB  sha256 %s" % (added, total / 1048576, size / 1048576, h.hexdigest()[:16]))
if missing:
    print("MISSING", len(missing))
    for m in missing:
        print("   ", m)

# 清单一并写出，便于发布后核对
with io.open(os.path.join(OUT_DIR, "MANIFEST-%s.txt" % VER), "w", encoding="utf-8", newline="\n") as f:
    f.write("# anima-workbench-%s.zip\n# sha256 %s\n# bytes %d\n" % (VER, h.hexdigest(), size))
    with zipfile.ZipFile(OUT) as z:
        for i in z.infolist():
            f.write("%10d  %s\n" % (i.file_size, i.filename))
print("manifest ->", os.path.join(OUT_DIR, "MANIFEST-%s.txt" % VER))
