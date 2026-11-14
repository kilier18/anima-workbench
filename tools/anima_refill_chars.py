# -*- coding: utf-8 -*-
"""把 18 条 AI 拟人回填进前端数据 wb_chars.json（前端 loadData 直接读这个静态文件），
并在作品分类里给 ai_gijinka 正名；同时去掉 kanpa 名字里的 ★用户最爱。"""
import json, sys, shutil, os
sys.stdout.reconfigure(encoding="utf-8")

CJ = r"D:\ComfyUI\ComfyUI_windows_portable\ComfyUI\custom_nodes\Comfyui-Anima-Wardrobe-V5\presets\anima_v4_characters.json"
WB = r"D:\ComfyUI\webui\data\wb_chars.json"
SJ = r"D:\ComfyUI\webui\data\anima_styles.json"

c = json.load(open(CJ, encoding="utf-8"))
ai = [x for x in c["characters"] if x.get("work") == "ai_gijinka"]
print("角色库 AI 拟人:", len(ai))

wb = json.load(open(WB, encoding="utf-8"))
kept = [x for x in wb["chars"] if x.get("w") != "ai_gijinka"]
rows = []
for x in ai:
    g = x.get("tags") or []
    if not g:
        g = [x.get("trigger") or x.get("tag")]
    rows.append({
        "t": x["tag"],
        "zh": x.get("zh") or x.get("name"),
        "w": "ai_gijinka",
        "p": x.get("pop") or 0,
        "g": g,
        "th": 1,
        "src": "lora",
        "lora": x.get("lora"),
        "lora_w": x.get("lora_w"),
    })
wb["chars"] = sorted(kept + rows, key=lambda r: -(r.get("p") or 0))
works = [w for w in wb.get("works", []) if not (isinstance(w, list) and any(str(y) == "ai_gijinka" for y in w))]
wb["works"] = [["ai_gijinka", len(rows)]] + works
wb.setdefault("works_zh", {})["ai_gijinka"] = "AI 拟人（大模型娘）"
shutil.copy2(WB, WB + ".bak2")
json.dump(wb, open(WB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wb_chars: %d 条, works 首位=%s, 总计 works %d" % (len(wb["chars"]), wb["works"][0], len(wb["works"])))
print("  前 6:", [(r["t"], r["zh"], r["p"]) for r in wb["chars"][:6]])

s = json.load(open(SJ, encoding="utf-8"))
n = 0
for x in s["styles"]:
    if "★用户最爱" in str(x.get("zh", "")):
        x["zh"] = x["zh"].replace(" ★用户最爱", "").replace("★用户最爱", "").strip()
        n += 1
        print("改名:", x["id"], "->", x["zh"])
s["version"] = int(s.get("version") or 0) + 1
json.dump(s, open(SJ, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("kanpa 改名 %d 处" % n)
