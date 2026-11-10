# -*- coding: utf-8 -*-
"""组合抽词用的原子库（池化版 v4：六类 × 三档）。

设计（用户 m01736 定义）：
  先按「场景类型 × 档位」选池，再从池里抽动作；池之间不混抽，避免画面里凭空多
  一个人或少一个人。场景类型由页面 `<select id="qScene">` 手动指定，auto 时按角色数推断。

  六类 × 三档（主力池，物理文件在 _setup/gen/<cls>_pools.py）
    solo      solo_daily / solo_flirt / solo_sex        单人：生活感 / 自慰暗示 / 明确自慰高潮
    yuri      yuri_daily / yuri_flirt / yuri_sex        女同：甜软贴贴 / 互相挑逗半脱 / 爱抚口交插入
    machine   machine_daily / _flirt / _sex             机械：辅助固定 / 带性意味接触 / 插入控制高潮
    bdsm      bdsm_daily / _flirt / _sex                调教：轻度引导 / 束缚+性暗示 / 命令-服从-快感
    tentacle  tentacle_daily / _flirt / _sex            触手：轻缠 / 缠绕挑逗 / 插入玩弄全身
    triple    triple_daily / _flirt / _sex              3P：亲密三人 / 两人挑逗一人 / 双插轮流夹心

  辅助池
    duo_daily / duo_flirt   普通双人互动（单人档抽中 → 第二人按隐形男补全构图）
    duo_male                单人 + 无脸男（明确性交，需要男性在场）
    group3p                 两女 + 无脸男
    after                   事后

  性别铁律（前端 preflight 按 POOL_RULE 再收一次）
    solo_* / yuri_* / machine_* / tentacle_* → 绝不出现男性词
    duo_male / group3p / triple_*            → 必须有无脸男（隐形男可替代）
    bdsm_sex                                 → 看条目自带

  who 只是统计标签（solo/duo/m/any/trio），不注入 tag；真正的性别收束在页面 preflight。
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"D:\ComfyUI"
sys.path.insert(0, os.path.join(ROOT, "tools"))

from atoms_solo import SOLO_DAILY as _F_SOLO_DAILY, SOLO_FLIRT as _F_SOLO_FLIRT, SOLO_SEX as _F_SOLO_SEX  # noqa: E402
from atoms_duo import DUO_DAILY, DUO_FLIRT, DUO_MALE            # noqa: E402
from atoms_ext import YURI_SEX as _F_YURI_SEX, TENTACLE as _F_TENTACLE  # noqa: E402
from atoms_ext import MACHINE as _F_MACHINE, GROUP3P, AFTER     # noqa: E402

import importlib.util

VOCAB = set()
for line in io.open(os.path.join(ROOT, "_setup", "danbooru.csv"), encoding="utf-8", errors="ignore"):
    n = line.split(",", 1)[0].strip()
    if n:
        VOCAB.add(n)

GEN_DIR = os.path.join(ROOT, "_setup", "gen")


def load_gen(fname, var, fallback=None):
    """从 _setup/gen/<fname>.py 取一个池；文件或变量不存在时退回旧池。"""
    path = os.path.join(GEN_DIR, fname + ".py")
    if not os.path.exists(path):
        return fallback
    spec = importlib.util.spec_from_file_location("gen_" + fname, path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        print("!! 载入 %s 失败：%s" % (path, e))
        return fallback
    return getattr(mod, var, fallback)


# 池 → (kind, who)。who 只做参考统计，抽词时以池名 + POOL_RULE 为准。
POOL_META = {
    # 单人三档
    "solo_daily": ("daily", "solo"),   "solo_flirt": ("flirt", "solo"),   "solo_sex": ("sex", "m"),
    # 女同三档
    "yuri_daily": ("daily", "duo"),    "yuri_flirt": ("flirt", "duo"),    "yuri_sex": ("yuri", "duo"),
    # 机械三档
    "machine_daily": ("machine", "solo"), "machine_flirt": ("machine", "solo"), "machine_sex": ("machine", "solo"),
    # 调教三档
    "bdsm_daily": ("daily", "any"),    "bdsm_flirt": ("flirt", "any"),    "bdsm_sex": ("sex", "any"),
    # 触手三档
    "tentacle_daily": ("tentacle", "solo"), "tentacle_flirt": ("tentacle", "solo"), "tentacle_sex": ("tentacle", "solo"),
    # 3P 三档
    "triple_daily": ("daily", "trio"), "triple_flirt": ("flirt", "trio"), "triple_sex": ("group", "trio"),
    # 催眠三档（第七类：引导/服从）
    "hypno_daily": ("daily", "solo"),  "hypno_flirt": ("flirt", "any"),   "hypno_sex": ("sex", "m"),
    # 辅助池
    "duo_daily": ("daily", "duo"),     "duo_flirt": ("flirt", "duo"),     "duo_male": ("flirt", "m"),
    "group3p": ("group", "trio"),      "after": ("after", "any"),
}

POOLS = {
    "solo_daily": load_gen("solo_pools", "SOLO_DAILY", _F_SOLO_DAILY),
    "solo_flirt": load_gen("solo_pools", "SOLO_FLIRT", _F_SOLO_FLIRT),
    "solo_sex": load_gen("solo_pools", "SOLO_SEX", _F_SOLO_SEX),
    "yuri_daily": load_gen("yuri_pools", "YURI_DAILY"),
    "yuri_flirt": load_gen("yuri_pools", "YURI_FLIRT"),
    "yuri_sex": load_gen("yuri_pools", "YURI_SEX", _F_YURI_SEX),
    "machine_daily": load_gen("machine_pools", "MACHINE_DAILY"),
    "machine_flirt": load_gen("machine_pools", "MACHINE_FLIRT"),
    "machine_sex": load_gen("machine_pools", "MACHINE_SEX", _F_MACHINE),
    "bdsm_daily": load_gen("bdsm_pools", "BDSM_DAILY"),
    "bdsm_flirt": load_gen("bdsm_pools", "BDSM_FLIRT"),
    "bdsm_sex": load_gen("bdsm_pools", "BDSM_SEX"),
    "tentacle_daily": load_gen("tentacle_pools", "TENTACLE_DAILY"),
    "tentacle_flirt": load_gen("tentacle_pools", "TENTACLE_FLIRT"),
    "tentacle_sex": load_gen("tentacle_pools", "TENTACLE_SEX", _F_TENTACLE),
    "triple_daily": load_gen("triple_pools", "TRIPLE_DAILY"),
    "triple_flirt": load_gen("triple_pools", "TRIPLE_FLIRT"),
    "triple_sex": load_gen("triple_pools", "TRIPLE_SEX"),
    "hypno_daily": load_gen("hypno_pools", "HYPNO_DAILY"),
    "hypno_flirt": load_gen("hypno_pools", "HYPNO_FLIRT"),
    "hypno_sex": load_gen("hypno_pools", "HYPNO_SEX"),
    "duo_daily": DUO_DAILY, "duo_flirt": DUO_FLIRT, "duo_male": DUO_MALE,
    "group3p": GROUP3P, "after": AFTER,
}

# ---------------- 强度（表情 / 生理反应） ----------------
INTENSITY = [
    {"lv": 0, "zh": "平静", "tags": ["light_smile"],
     "variants": [["light_smile"], ["closed_eyes", "light_smile"], ["expressionless"]]},
    {"lv": 1, "zh": "微热", "tags": ["blush", "light_smile", "sweat"],
     "variants": [["blush", "light_smile", "sweat"], ["blush", "half-closed_eyes"],
                  ["blush", "parted_lips", "sweat"]]},
    {"lv": 2, "zh": "起伏", "tags": ["half-closed_eyes", "blush", "parted_lips", "sweat", "heavy_breathing"],
     "variants": [["half-closed_eyes", "blush", "parted_lips", "sweat"],
                  ["half-closed_eyes", "blush", "open_mouth", "heavy_breathing"],
                  ["blush", "parted_lips", "sweat", "heavy_breathing"],
                  ["half-closed_eyes", "blush", "light_smile", "sweat"]]},
    {"lv": 3, "zh": "失控", "tags": ["tongue_out", "half-closed_eyes", "blush", "sweat", "heavy_breathing", "trembling"],
     "variants": [["tongue_out", "half-closed_eyes", "blush", "sweat", "heavy_breathing", "trembling"],
                  ["half-closed_eyes", "blush", "tears", "heavy_breathing", "trembling"],
                  ["blush", "parted_lips", "saliva", "sweat", "heavy_breathing"],
                  ["tongue_out", "blush", "saliva", "trembling", "tears"]]},
    {"lv": 4, "zh": "崩坏", "tags": ["torogao", "rolling_eyes", "drooling", "tongue_out", "blush", "excessive_saliva"],
     "variants": [["torogao", "rolling_eyes", "drooling", "tongue_out", "blush", "excessive_saliva"],
                  ["ahegao", "rolling_eyes", "tongue_out", "blush", "tears"],
                  ["tears", "trembling", "heavy_breathing", "blush", "excessive_saliva", "tongue_out"],
                  ["half-closed_eyes", "tongue_out", "sweat", "blush", "parted_lips"]]},
]

PHYS_EXTRA = {  # 按档位可加的爱液/精液类
    "L2": ["pussy_juice", "wet"],
    "L3": ["pussy_juice", "wet", "cum", "cum_in_pussy", "cumdrip", "cum_on_body"],
}

PLACES = [("卧室", ["bedroom"]), ("客厅", ["living_room"]), ("厨房", ["kitchen"]),
          ("浴室", ["bathroom"]), ("教室", ["classroom"]), ("图书馆", ["library"]),
          ("神社", ["shrine"]), ("街道", ["street"]), ("公园", ["park"]),
          ("天台", ["rooftop"]), ("温泉", ["onsen"]), ("咖啡馆", ["cafe"]),
          ("海边", ["beach"]), ("森林", ["forest"]), ("电车里", ["train_interior"]),
          ("电梯里", ["elevator"]), ("阳台", ["balcony"]), ("花园", ["garden"]),
          ("旅馆", ["love_hotel"]), ("办公室", ["office"]), ("浴室镜前", ["bathroom", "mirror"]),
          ("走廊", ["hallway"]), ("储物间", ["storage_room"]), ("地下停车场", ["parking_lot"]),
          ("寝室床上", ["bedroom", "on_bed"]), ("沙发", ["couch"]), ("地毯上", ["on_floor"]),
          ("游泳池边", ["poolside"]), ("更衣室", ["changing_room"]), ("楼梯间", ["stairwell"]),
          ("车内", ["car_interior"]), ("课桌旁", ["classroom", "desk"]),
          ("床边", ["bed", "bedroom"]), ("浴缸里", ["bathtub", "bathroom"]),
          ("窗台", ["window", "indoors"]), ("床头灯下", ["bedroom", "lamp"]),
          ("教室课桌", ["classroom", "desk", "chair"]), ("神社回廊", ["shrine", "hallway"])]
LIGHTS = [("暖光", ["dim_lighting", "lamp"]), ("清晨光", ["morning"]), ("黄昏", ["sunset"]),
          ("夜晚", ["night"]), ("烛光", ["candlelight"]), ("月光", ["moonlight"]),
          ("室内灯", ["indoors", "fluorescent_lamp"]), ("逆光", ["backlighting"]),
          ("斑驳日光", ["dappled_sunlight"]), ("霓虹", ["neon_lights"]),
          ("台灯", ["lamp"]), ("斜射阳光", ["sunbeam"]), ("光斑", ["light_particles"]),
          ("暗调", ["dim_lighting"]), ("落地窗光", ["window", "backlighting"]),
          ("屏幕光", ["light_particles", "dim_lighting"])]
WEATHER = [("晴天", ["day"]), ("下雨", ["rain"]), ("下雪", ["snow"]), ("阴天", ["cloud"]),
           ("起雾", ["fog"]), ("樱花", ["cherry_blossoms"]), ("夜雨", ["night", "rain"]),
           ("星空", ["starry_sky"])]
SHOTS = [{"zh": "全身", "tags": ["full_body"]}, {"zh": "七分身", "tags": ["cowboy_shot"]},
         {"zh": "上半身", "tags": ["upper_body"]}, {"zh": "特写", "tags": ["close-up"]}]
ANGLES = [{"zh": "正面", "tags": []}, {"zh": "侧面", "tags": ["from_side"]},
          {"zh": "背后", "tags": ["from_behind"]}, {"zh": "俯拍", "tags": ["from_above"]},
          {"zh": "仰拍", "tags": ["from_below"]}, {"zh": "斜角", "tags": ["dutch_angle"]},
          {"zh": "第一视角", "tags": ["pov"]}]

# ---------------- 静态词：不算「动作核心」 ----------------
WEAK_STATIC = {
    # 地点与家具
    "bedroom", "living_room", "kitchen", "bathroom", "classroom", "library", "shrine", "street",
    "park", "rooftop", "onsen", "cafe", "beach", "forest", "train_interior", "elevator",
    "balcony", "garden", "love_hotel", "office", "hallway", "storage_room", "parking_lot",
    "couch", "on_floor", "poolside", "changing_room", "stairwell", "car_interior", "desk",
    "bed", "bathtub", "window", "mirror", "under_table", "on_bed", "door", "wall", "indoors",
    "outdoors", "laundry_room", "chair", "sofa", "sitting_on_bed", "sitting_on_floor",
    "sitting_on_stairs", "sitting_on_chair", "washing_machine", "field", "sky", "grass",
    "water", "stairs", "sink", "appliance",
    # 光/天气/构图/机位
    "dim_lighting", "sunlight", "morning", "sunset", "night", "candlelight", "moonlight",
    "fluorescent_lamp", "backlighting", "dappled_sunlight", "neon_lights", "lamp", "sunbeam",
    "light_particles", "day", "rain", "snow", "cloud", "fog", "cherry_blossoms", "starry_sky",
    "full_body", "cowboy_shot", "upper_body", "close-up", "from_side", "from_behind",
    "from_above", "from_below", "dutch_angle", "pov", "pov_hands",
    # 人数词
    "solo", "1girl", "2girls", "1boy", "multiple_boys", "faceless_male", "hetero",
    # 表情/生理
    "light_smile", "blush", "half-closed_eyes", "parted_lips", "tongue_out", "torogao",
    "rolling_eyes", "drooling", "sweat", "heavy_breathing", "trembling", "saliva",
    "excessive_saliva", "tears", "closed_eyes", "looking_at_viewer", "surprised",
    "open_mouth", "closed_mouth", "smile", "laughing", "blush", "shivering", "sleepy",
    "exhausted", "nervous", "bored", "concentrated", "dazed", "thinking", "blinking",
    # 衣物/物件/状态
    "towel", "wet_hair", "breast_milk", "lactation", "wet", "swimsuit", "wet_shirt",
    "breast_slip", "legs_together", "apron", "book", "cellphone", "pillow", "headphones",
    "umbrella", "bicycle", "cup", "towel_around_neck", "bare_shoulders", "wet_clothes",
    "clothes_removed", "see-through", "camera", "cat", "tea", "newspaper", "shoes",
    "blanket", "collarbone", "oversized_clothes", "pool", "hair_tie", "long_hair",
    "bare_legs", "barefoot", "midriff", "underwear", "bra", "panties",
    "torn_clothes", "red_marks", "skin", "neck", "face", "waist", "ankles", "thighs",
}


def filt(tags):
    ok, drop = [], []
    seen = set()
    for t in tags:
        if t not in VOCAB:
            drop.append(t)
            continue
        if t in seen:
            continue
        seen.add(t)
        ok.append(t)
    return ok, drop


def core_of(tags):
    return [t for t in tags if t not in WEAK_STATIC][:3]


def build():
    actions = {}
    all_zh = {}
    banned = {}
    for pool, items in POOLS.items():
        kind, who = POOL_META[pool]
        out, dropped = [], set()
        for zh, tags, lv in items:
            ok, drop = filt(tags)
            dropped |= set(drop)
            if not ok:
                print("  !! %s「%s」全部 tag 不在词表，丢弃" % (pool, zh))
                continue
            if zh in all_zh:
                print("  !! %s「%s」与 %s 重名，跳过" % (pool, zh, all_zh[zh]))
                continue
            all_zh[zh] = pool
            core = core_of(ok)
            if not core:
                print("  !! %s「%s」没有动作核心词（%s）——画面会靠底模发挥" % (pool, zh, ok))
                banned.setdefault(pool, []).append(zh)
            out.append({"zh": zh, "tags": ok, "core": core, "lv": lv, "kind": kind, "who": who})
        actions[pool] = out
        print("%-11s %3d 条（剔除 %s）" % (pool, len(out), sorted(dropped) or "无"))
    return actions, banned


def clean_meta(pool, label):
    out = []
    for row in pool:
        zh, tags = (row[0], row[1]) if isinstance(row, tuple) else (row["zh"], row["tags"])
        ok, drop = filt(tags)
        if not ok:
            print("  !! %s「%s」全部 tag 不在词表，丢弃" % (label, zh))
            continue
        if drop:
            print("  %s「%s」剔除 %s" % (label, zh, drop))
        out.append({"zh": zh, "tags": ok})
    return out


def main():
    actions, banned = build()
    data = {"actions": actions,
            "intensity": INTENSITY,
            "places": clean_meta(PLACES, "地点"),
            "lights": clean_meta(LIGHTS, "光线"),
            "weather": clean_meta(WEATHER, "天气"),
            "shots": SHOTS,
            "angles": ANGLES,
            "phys": {k: filt(v)[0] for k, v in PHYS_EXTRA.items()}}
    n = {k: len(v) for k, v in actions.items()}
    kinds = {}
    whos = {}
    for arr in actions.values():
        for a in arr:
            kinds[a["kind"]] = kinds.get(a["kind"], 0) + 1
            whos[a["who"]] = whos.get(a["who"], 0) + 1
    total = sum(n.values())
    comb = total * len(data["places"]) * len(data["lights"]) * \
        len(data["intensity"]) * len(data["shots"]) * len(data["angles"])
    weak = sum(1 for arr in actions.values() for a in arr if not a["core"])
    data["meta"] = {"actions": n, "total": total, "kinds": kinds, "whos": whos,
                    "weak": weak, "banned": banned,
                    "places": len(data["places"]), "lights": len(data["lights"]),
                    "weather": len(data["weather"]),
                    "intensity": len(data["intensity"]), "shots": len(data["shots"]),
                    "angles": len(data["angles"]), "combinations": comb}
    out = os.path.join(ROOT, "webui", "data", "wb_atoms.json")
    json.dump(data, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n写入 %s" % out)
    print("动作合计 %d 条，kind %s" % (total, kinds))
    print("who %s，无核心词 %d 条" % (whos, weak))
    print("地点 %d，光线 %d，天气 %d，强度 %d，构图 %d，机位 %d → 组合数 %d"
          % (len(data["places"]), len(data["lights"]), len(data["weather"]),
             len(data["intensity"]), len(data["shots"]), len(data["angles"]), comb))


if __name__ == "__main__":
    main()
