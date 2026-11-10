# -*- coding: utf-8 -*-
"""打印当前出图目录（供 start_engine.cmd 读取）。

优先级：webui/data/wb_config.json → 环境变量 COMFY_OUTPUT → D:\\ComfyUI\\output
只输出一行纯路径，方便 cmd 的 for /f 取用。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "webui", "data", "wb_config.json")
DEFAULT = os.path.join(ROOT, "output")

out = ""
try:
    if os.path.exists(CFG):
        with open(CFG, encoding="utf-8") as f:
            out = (json.load(f) or {}).get("output_dir") or ""
except Exception:
    out = ""

if not out.strip():
    out = os.environ.get("COMFY_OUTPUT") or ""
if not out.strip():
    out = DEFAULT

sys.stdout.write(out.strip())
