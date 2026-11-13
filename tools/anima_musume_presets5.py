# -*- coding: utf-8 -*-
"""把 Grok / Kimi / 智谱GLM / 千问Qwen 的拟人形象写进角色库与画风卡（正常版 + Q版）。"""
import json, os, shutil
from PIL import Image

GRP = "AI 拟人（大模型娘）"
STY = r"D:\ComfyUI\webui\data\anima_styles.json"
PRESETS = (r"D:\ComfyUI\ComfyUI_windows_portable\ComfyUI\custom_nodes"
           r"\Comfyui-Anima-Wardrobe-V5\presets\anima_v4_characters.json")
THUMB = r"D:\ComfyUI\webui\static\style_thumbs"
S7 = r"D:\ComfyUI\_style_test\musume7"

ANI = ["Ani_(Grok)", "1girl", "solo", "blonde hair", "twintails", "long hair", "blue eyes",
       "lace choker", "off-shoulder short dress", "gothic", "corset", "black gloves",
       "asymmetrical legwear", "black thighhighs", "fishnet thighhighs"]
MIKA = ["mika_(xai)", "1girl", "solo", "black hair", "gradient hair", "multicolored hair",
        "medium hair", "yellow eyes", "necklace", "denim jacket", "black cropped shirt",
        "midriff", "navel", "torn jeans", "sneakers"]
KIMI = ["kimi chan", "1girl", "solo"]
GLM = ["glm_fox_girl", "1girl", "solo", "fox ears", "frills", "white shirt", "puffy sleeves", "black bow"]
QWEN = [r"qwen \(girl\)", "1girl", "solo"]

ROWS = [
    # tag, zh, 触发词, tags, lora, mb, 正常图, Q图, pop
    ("grok-ani", "Grok娘 Ani（正常版）", "Ani_(Grok)", ANI, "grok-ani", 43.9, "grok-ani", "grok-ani-q", 34500),
    ("grok-ani-chibi", "Grok娘 Ani（Q版）", "chibi, 2head, Ani_(Grok)", ANI, "grok-ani", 43.9, None, "grok-ani-q", 34000),
    ("grok-mika", "Grok娘 Mika（正常版）", "mika_(xai)", MIKA, "grok-mika", 43.9, "grok-mika", "grok-mika-q", 33500),
    ("grok-mika-chibi", "Grok娘 Mika（Q版）", "chibi, 2head, mika_(xai)", MIKA, "grok-mika", 43.9, None, "grok-mika-q", 33000),
    ("kimi-chan", "Kimi娘（正常版）", "kimi chan", KIMI, "kimi-chan", 132.2, "kimi-chan", "kimi-chan-q", 32500),
    ("kimi-chan-chibi", "Kimi娘（Q版）", "chibi, 2head, kimi chan", KIMI, "kimi-chan", 132.2, None, "kimi-chan-q", 32000),
    ("glm-zhipu", "智谱GLM娘（正常版）", "glm_fox_girl", GLM, "glm-zhipu", 175.1, "glm-zhipu", "glm-zhipu-q", 31500),
    ("glm-zhipu-chibi", "智谱GLM娘（Q版）", "chibi, 2head, glm_fox_girl", GLM, "glm-zhipu", 175.1, None, "glm-zhipu-q", 31000),
    ("qwen-chan", "千问娘（正常版）", r"qwen \(girl\)", QWEN, "qwen-chan", 104.0, "qwen-chan", "qwen-chan-q", 30500),
    ("qwen-chan-chibi", "千问娘（Q版）", r"chibi, 2head, qwen \(girl\)", QWEN, "qwen-chan", 104.0, None, "qwen-chan-q", 30000),
]


def mk(src, dst):
    if not os.path.exists(src):
        print("  MISS", os.path.basename(src)); return False
    im = Image.open(src).convert("RGB")
    im.resize((512, int(512 * im.height / im.width)), Image.LANCZOS).save(dst, "JPEG", quality=86)
    return True


def main():
    bak = PRESETS + ".bak5"
    if not os.path.exists(bak):
        shutil.copy2(PRESETS, bak)
    p = json.load(open(PRESETS, encoding="utf-8"))
    s = json.load(open(STY, encoding="utf-8"))

    for tag, zh, trig, tags, slug, mb, normal_src, q_src, pop in ROWS:
        is_q = tag.endswith("-chibi")
        sid = "musume_" + tag.replace("-", "_")
        thumb = sid + ".jpg"
        mk(os.path.join(S7, (q_src if is_q else (normal_src or q_src)) + "_00001_.png"),
           os.path.join(THUMB, thumb))

        for c in p["characters"]:
            if c.get("tag") == tag:
                c.update({"trigger": trig, "tags": tags, "pop": pop, "zh": zh, "thumb": sid})
                break
        else:
            p["characters"].append({"tag": tag, "name": slug, "zh": zh, "work": "ai_gijinka",
                                    "trigger": trig, "pop": pop, "hair": "", "eyes": "",
                                    "tags": tags, "src": "anima", "thumb": sid})

        lora = r"Anima\packs\%s.safetensors" % slug
        for x in s["styles"]:
            if x["id"] == sid:
                x.update({"zh": zh, "trig": trig, "lora": lora, "strength": 0.85 if is_q else 0.9,
                          "thumb": "/style_thumbs/" + thumb})
                break
        else:
            s["styles"].append({"id": sid, "wall_no": None, "batch": "musume", "name": slug, "zh": zh,
                                "group": GRP, "lora": lora, "mb": mb, "trig": trig,
                                "strength": 0.85 if is_q else 0.9, "turbo": 0.7, "verdict": "keep",
                                "touhou_artist": False, "on_disk": True, "src": "civitai",
                                "thumb": "/style_thumbs/" + thumb})

    p["characters"].sort(key=lambda c: -(c.get("pop") or 0))
    n_ai = sum(1 for c in p["characters"] if c.get("work") == "ai_gijinka")
    for w in p["works"]:
        if isinstance(w, dict) and w.get("id") == "ai_gijinka":
            w["count"] = n_ai
    json.dump(p, open(PRESETS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    s["version"] = s.get("version", 1) + 1
    json.dump(s, open(STY, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("角色库 AI 组 %d 条；画风卡 keep %d 张" % (n_ai, sum(1 for x in s["styles"] if x.get("verdict") == "keep")))
    print("AI 组:", " / ".join(x["zh"] for x in s["styles"] if x.get("group", "").startswith("AI")))


if __name__ == "__main__":
    main()
