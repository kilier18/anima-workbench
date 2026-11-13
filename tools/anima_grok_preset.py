# -*- coding: utf-8 -*-
"""ZipZipPipe 版 Grok 娘入库：替换 Ani / Mika 四条，写入角色库 + 画风卡。"""
import json, os

CHAR = r"D:\ComfyUI\ComfyUI_windows_portable\ComfyUI\custom_nodes\Comfyui-Anima-Wardrobe-V5\presets\anima_v4_characters.json"
STYLE = r"D:\ComfyUI\webui\data\anima_styles.json"
LORA = r"Anima\packs\ai-girls-pack.safetensors"

TRIG_N = ("aigirls, grok, two bat wing hair ornaments, one on each side of head, "
          "gold crown, black red short dress, black pantyhose, smirk, blue eyes, blonde twintails")
TRIG_Q = "chibi, 2head, " + TRIG_N

TAGS = ["aigirls", "grok", "1girl", "full body", "standing", "blonde hair", "long hair",
        "twintails", "gold crown", "two bat wing hair ornaments, one on each side of head",
        "blue eyes", "sharp eyes", "smirk", "raised eyebrow", "black and red dress",
        "short dress", "red lining", "gold trim", "black pantyhose", "black boots"]

DROP_TAGS = {"grok-ani", "grok-ani-chibi", "grok-mika", "grok-mika-chibi"}

NEW = [
    {"tag": "grok-tan", "name": "grok-tan", "zh": "Grok娘（ZipZipPipe版）", "work": "ai_gijinka",
     "trigger": TRIG_N, "pop": 34500, "hair": "blonde twintails", "eyes": "blue",
     "tags": list(TAGS), "src": "anima", "thumb": "musume_grok_normal"},
    {"tag": "grok-tan-chibi", "name": "grok-tan", "zh": "Grok娘（Q版）", "work": "ai_gijinka",
     "trigger": TRIG_Q, "pop": 34000, "hair": "blonde twintails", "eyes": "blue",
     "tags": list(TAGS), "src": "anima", "thumb": "musume_grok_chibi"},
]

# ---- 角色库 ----
d = json.load(open(CHAR, encoding="utf-8"))
before = len(d["characters"])
d["characters"] = [c for c in d["characters"] if c.get("tag") not in DROP_TAGS]
removed = before - len(d["characters"])
for i, n in enumerate(NEW):
    n["pop"] = 34500 - i * 500
    d["characters"].append(n)
for w in d["works"]:
    if w.get("id") == "ai_gijinka":
        w["count"] = sum(1 for c in d["characters"] if c.get("work") == "ai_gijinka")
        print("work count ->", w["count"])
json.dump(d, open(CHAR, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("chars: removed", removed, "now", len(d["characters"]))

# ---- 画风卡 ----
s = json.load(open(STYLE, encoding="utf-8"))
drop_ids = {"musume_grok_ani", "musume_grok_ani_chibi", "musume_grok_mika", "musume_grok_mika_chibi"}
s["styles"] = [x for x in s["styles"] if x["id"] not in drop_ids]
base = [x for x in s["styles"] if x["id"] == "musume_whale_normal"]
proto = dict(base[0]) if base else {}
for sid, zh, trig, st in [("musume_grok_normal", "Grok娘（ZipZipPipe版）", TRIG_N, 1.0),
                          ("musume_grok_chibi", "Grok娘（Q版）", TRIG_Q, 0.85)]:
    row = dict(proto)
    row.update({"id": sid, "zh": zh, "name": "grok", "group": "AI拟人", "lora": LORA,
                "mb": 132.3, "trig": trig, "strength": st, "turbo": 0.7, "verdict": "keep",
                "touhou_artist": False, "on_disk": True, "thumb": "/style_thumbs/%s.jpg" % sid,
                "name_zh": zh})
    s["styles"].append(row)
    print("added", sid)
s["version"] = int(s.get("version", 0)) + 1
json.dump(s, open(STYLE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("styles now", len(s["styles"]), "version", s["version"])
