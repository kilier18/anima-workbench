# -*- coding: utf-8 -*-
"""把 AI 拟人从画风库移除，并清掉备用角色库里的旧条目。
- anima_styles.json : 删 id 以 musume_ 开头的 18 条（AI 拟人（大模型娘）组）
- wb_chars.json     : 删 w=='ai_gijinka' 的角色 + works 里的 ['ai_gijinka', n]
- lib_chars.json    : 同上
角色唯一来源保持 anima_v4_characters.json（18 条，带 lora）。
"""
import json, shutil, sys, os
sys.stdout.reconfigure(encoding="utf-8")

SJ = r"D:\ComfyUI\webui\data\anima_styles.json"
WB = r"D:\ComfyUI\webui\data\wb_chars.json"
LB = r"D:\ComfyUI\webui\data\lib_chars.json"


def bak(p):
    b = p + ".bak"
    if not os.path.exists(b):
        shutil.copy2(p, b)


def dump(p, obj):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


# 1) 画风库去掉 musume_
bak(SJ)
s = json.load(open(SJ, encoding="utf-8"))
before = len(s["styles"])
s["styles"] = [x for x in s["styles"] if not str(x.get("id", "")).startswith("musume_")]
s["version"] = int(s.get("version") or 0) + 1
dump(SJ, s)
print("anima_styles: %d -> %d (version %s)" % (before, len(s["styles"]), s["version"]))
from collections import Counter
print("  分组:", dict(Counter([x.get("group") for x in s["styles"]])))

# 2) 备用角色库清掉 ai_gijinka
for p, ck in ((WB, "chars"), (LB, "chars")):
    bak(p)
    d = json.load(open(p, encoding="utf-8"))
    chars = d.get(ck) or d.get("characters") or []
    n0 = len(chars)
    kept = [c for c in chars if c.get("w") != "ai_gijinka" and c.get("work") != "ai_gijinka"]
    d[ck] = kept
    if isinstance(d.get("works"), list):
        w0 = len(d["works"])
        d["works"] = [w for w in d["works"]
                      if not (isinstance(w, list) and any(str(x) == "ai_gijinka" for x in w))]
        if len(d["works"]) != w0:
            print("  %s works %d -> %d" % (os.path.basename(p), w0, len(d["works"])))
    dump(p, d)
    print("%s: %d -> %d" % (os.path.basename(p), n0, len(kept)))
