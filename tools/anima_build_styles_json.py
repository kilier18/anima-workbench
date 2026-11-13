# -*- coding: utf-8 -*-
"""生成程序用的画风清单（两批成品包 + 83 桶）：webui/data/anima_styles.json + docs/Anima画风-保留名单.md"""
import json, os

PACK_DIR = r"D:\ComfyUI\models\loras\Anima\packs"
OUT_JSON = r"D:\ComfyUI\webui\data\anima_styles.json"
OUT_MD = r"D:\ComfyUI\docs\Anima画风-保留名单.md"

# 已核实的东方画师（danbooru 别名 + 作品分布确认）
TOUHOU_ARTISTS = {
    "takorin": "なまこ大爆発（namako_daibakuhatsu 的别名），东方像素画同人",
    "namako daibakuhatsu": "同 takorin，桶 #43 与 takorin 包是同一人",
}

# 中文名修正表（slug 片段 -> (分类, 中文名)）
META = [
    ("pako", "画师", "Pako (PakoSun)"), ("incase", "画师", "Incase"),
    ("asml3", "多合一", "ArtistStyleMixLora 3（12 画师）"), ("happoubi", "画师", "八宝備仁"),
    ("modare", "画师", "modare"), ("ogipote", "画师", "Ogipote"), ("mignon", "画师", "mignon"),
    ("wada", "画师", "Wada Arco"), ("nixeu", "画师", "Nixeu"), ("afrobull", "画师", "Afrobull"),
    ("ask", "画师", "ASK"), ("sakimichan", "画师", "sakimichan"), ("wlop", "画师", "wlop"),
    ("fkey", "会社", "FKEY"), ("kantoku", "画师", "kantoku 监督"), ("harada", "画师", "原田雄一"),
    ("mitsuko", "画师", "神童美津子"), ("citron", "会社", "Citron"),
    ("yuzu", "会社", "柚子社"), ("rurudo", "画师", "Rurudo"), ("alice", "同人", "东方爱丽丝 PC-98"),
    ("cutified", "风格", "Cutified 变体"), ("mangekyou", "galgame", "美少女万华镜 16in1"),
    ("tony", "galgame", "Tony Taka 5in1"), ("yoneyama", "画师", "米山舞"),
    ("kanojo", "galgame", "Kanojo×3 5in1"), ("pottsness", "画师", "pottsness"),
    ("moonlight", "galgame", "Moonlight Lady 7in1"),
    # 第二批
    ("velvet", "风格", "Velvet 神话奇幻"), ("vixon", "风格", "Vixon 哥特霓虹"),
    ("hyperrealistic", "风格", "Hyperrealistic 超写实"), ("niji-sweet", "风格", "Niji Sweet Spot"),
    ("748cm", "画师", "748cm / Shiiro"), ("granblue", "IP风格", "碧蓝幻想 v4"),
    ("anime-artistic", "风格", "Anime Artistic"), ("dark-art", "风格", "Dark Art"),
    ("flatline", "风格", "Flatline 平涂"), ("niji-oil", "风格", "Niji 油画"),
    ("memaani", "风格", "MeMaAni 平涂"), ("blue-archive-style", "IP风格", "蔚蓝档案"),
    ("meion", "画师", "meion"), ("theobrobine", "画师", "Theobrobine"),
    ("cartoon-styles", "风格", "Cartoon Styles"), ("impasto", "风格", "厚涂 / 印象派"),
    ("rei17", "画师", "Rei_17 / 三本樱"), ("sky02", "光影", "sky02 光影"),
    ("rucarachi", "画师", "rucarachi"), ("andava", "画师", "Andava"),
    ("dragon-ball", "IP风格", "龙珠"), ("blue-archive-nai5", "IP风格", "蔚蓝档案 nai5"),
    ("valbun", "画师", "Valbun"), ("takorin", "画师·东方", "Takorin たこりん"),
    ("mixplin", "画师", "Mixplin"), ("nijimecha", "风格", "Niji 机甲"),
    ("zaush", "画师", "Zaush"), ("possummachine", "画师", "PossumMachine"),
    ("cherry-gig", "风格", "Cherry-gig 西部"), ("mare-style", "画师", "MARE"),
    ("ghibli", "风格", "吉卜力"),
]


def lookup(slug, label):
    lo = slug.lower()
    for k, g, z in META:
        if k in lo:
            return g, z
    return "画师", label[:40]


styles = []

# ---- 第一批 p5_all ----
d1 = json.load(open(r"D:\ComfyUI\logs\pack_verdict.json", encoding="utf-8"))
led1 = json.load(open(r"D:\ComfyUI\logs\anima_fetch_batch.json", encoding="utf-8"))
for r in json.load(open(r"D:\ComfyUI\logs\p5_all.json", encoding="utf-8")):
    e = led1.get(r["mid"], {})
    fn = os.path.basename(e.get("file", ""))
    slug = os.path.splitext(fn)[0]
    trig = e.get("trig") or []
    if isinstance(trig, str):
        trig = [trig]
    grp, zh = lookup(slug, e.get("name") or "")
    styles.append({
        "id": "p5_%d" % r["idx"], "wall_no": r["idx"], "batch": "p5",
        "name": (e.get("name") or "")[:70], "zh": zh, "group": grp,
        "lora": "Anima\\packs\\" + fn, "mb": e.get("mb"),
        "trig": [t for t in trig if t][:3], "strength": 1.0, "turbo": 0.7,
        "verdict": d1.get(str(r["idx"]), "?"),
        "touhou_artist": False,
        "on_disk": os.path.exists(os.path.join(PACK_DIR, fn)),
        "src": "civitai:%s" % r["mid"],
    })

# ---- 第二批 p6_next ----
d2 = json.load(open(r"D:\ComfyUI\logs\pack_verdict_next_slug.json", encoding="utf-8"))
led2 = json.load(open(r"D:\ComfyUI\logs\anima_next_batch.json", encoding="utf-8"))
by_slug = {}
for mid, v in led2.items():
    by_slug[v.get("slug", "")] = (mid, v)
for r in json.load(open(r"D:\ComfyUI\logs\p6_next.json", encoding="utf-8")):
    slug = r["slug"]
    mid, v = by_slug.get(slug, (r["mid"], {}))
    fn = v.get("file") or (slug + ".safetensors")
    trig = v.get("trig") or []
    if isinstance(trig, str):
        trig = [trig]
    grp, zh = lookup(slug, v.get("label") or r.get("tag") or "")
    styles.append({
        "id": "p6_%s" % slug, "wall_no": None, "batch": "p6",
        "name": (v.get("name") or r.get("tag") or "")[:70], "zh": zh, "group": grp,
        "lora": "Anima\\packs\\" + fn, "mb": v.get("mb"),
        "trig": [t for t in trig if t][:3], "strength": 1.0, "turbo": 0.7,
        "verdict": d2.get(slug, "?"),
        "touhou_artist": slug.lower() in TOUHOU_ARTISTS,
        "on_disk": os.path.exists(os.path.join(PACK_DIR, fn)),
        "src": "civitai:%s" % mid,
    })

# ---- 83 个画师桶（用户判定 drop：1 / 7 / 66）----
DROP_TUB = {1, 7, 66}
tubs = json.load(open(r"D:\ComfyUI\logs\tubs_ledger.json", encoding="utf-8"))
buckets = []
for t in (tubs.values() if isinstance(tubs, dict) else tubs):
    if int(t["idx"]) in DROP_TUB:
        continue
    tag = t["tag"].lstrip("@")
    buckets.append({
        "idx": t["idx"], "tag": t["tag"], "count": t.get("count"),
        "zh": ("东方画师" if tag in TOUHOU_ARTISTS else ""),
        "group": "桶", "lora": "Anima\\ai-styles-dump-anima-v5.safetensors",
        "trig": ["@" + tag], "strength": 1.0,
        "touhou_artist": tag in TOUHOU_ARTISTS,
    })

data = {
    "version": 2,
    "base": "Anima\\miaomiaoHarem_anima12.safetensors",
    "turbo": "Anima\\anima-turbo-lora-v0.2.safetensors",
    "note": "verdict=keep 才进工作台下拉；touhou_artist=true 的是已核实的东方画师",
    "styles": styles,
    "buckets": buckets,
}
os.makedirs(r"D:\ComfyUI\webui\data", exist_ok=True)
json.dump(data, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

keep = [s for s in styles if s["verdict"] == "keep"]
drop = [s for s in styles if s["verdict"] != "keep"]
L = ["# Anima 画风保留名单（程序数据源）", "",
     "机器可读：`D:\\ComfyUI\\webui\\data\\anima_styles.json`（version 2，两批合并）", "",
     "## 一、成品包保留 %d 个" % len(keep), "",
     "| 批次 | 中文名 | 分类 | 触发词 | 体积 | 东方画师 | LoRA 文件 |",
     "|---|---|---|---|---|---|---|"]
for s in sorted(keep, key=lambda x: (x["batch"], x["zh"])):
    L.append("| %s | %s | %s | %s | %sMB | %s | `%s` |" % (
        s["batch"], s["zh"], s["group"],
        ", ".join(s["trig"])[:30].replace("|", "/") or "—",
        s["mb"], "★" if s["touhou_artist"] else "",
        os.path.basename(s["lora"])))
L += ["", "## 二、已判不要 %d 个（文件仍在盘）" % len(drop), "",
      "| 批次 | 名称 |", "|---|---|"]
for s in drop:
    L.append("| %s | %s |" % (s["batch"], s["zh"]))
L += ["", "## 三、ai-styles-dump 画师桶（%d 个保留 / 83）" % len(buckets), "",
      "已剔除：1 @gs-mantis、7 @hllv、66 @aimpressionism。",
      "**东方画师**：43 @namako daibakuhatsu（= Takorin たこりん，东方像素画同人）。", "",
      "完整列表见 json 的 `buckets` 数组。", "",
      "## 四、接入程序", "",
      "1. `assistant.py:1564` 的 `ANIMA_LORAS` 写死三行，改成读 `webui\\data\\anima_styles.json`。",
      "2. `lora_name` 必须带 `Anima\\packs\\` 前缀，否则 `value_not_in_list`。",
      "3. 选中画风 = turbo 0.7 + 该包 1.0，10 步 cfg1 er_sde beta，1024×1536。",
      "4. 角色写全 `角色名, 作品名, 发色, 瞳色, 服装`，否则会漂到别的角色。", ""]
open(OUT_MD, "w", encoding="utf-8").write("\n".join(L))
print("styles=%d (keep %d, drop %d) buckets=%d" % (len(styles), len(keep), len(drop), len(buckets)))
print("->", OUT_JSON)
print("->", OUT_MD)
