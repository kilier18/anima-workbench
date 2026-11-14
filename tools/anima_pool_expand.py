# -*- coding: utf-8 -*-
"""动作池扩库：R18 池补"半脱/掀衣"条目 + 新建 duo_sfw（男女·健全）池。
幂等：以 zh 去重，重复执行不会翻倍。
"""
import json, io, sys, os

P = r"D:\ComfyUI\webui\data\wb_atoms.json"
sys.stdout.reconfigure(encoding="utf-8")

# ---------- 1. 各 R18 池追加半脱/掀衣条目 ----------
# 只补"衣服状态"，不补新体位（体位池已有），core 用衣物状态词
UNDRESS = {
    "duo_male": [
        ("衣领被扯开，锁骨和肩线全露出来", ["clothes_pull", "collar", "bare_shoulders", "blush"]),
        ("裙子被掀到腰上，动作没停", ["skirt_lift", "panties", "sex", "standing"]),
        ("上衣被推到胸口以上", ["clothes_lift", "breasts_out", "underboob", "sex"]),
        ("内裤只剩一只脚踝挂着", ["panties_around_one_leg", "sex", "on_bed"]),
        ("衣服扯开一半还挂在身上", ["open_clothes", "torn_clothes", "sex", "sweat"]),
        ("扣子全解了，里面什么都没穿", ["undressing", "buttons", "open_shirt", "breasts_out"]),
        ("从背后解开拉链，后背整片露着", ["undressing", "zipper", "bare_back", "sex_from_behind"]),
        ("裙子被推到腰间，髋线露出来", ["clothes_lift", "skirt_lift", "bare_hips", "sex"]),
    ],
    "solo_sex": [
        ("衣服没脱，手从下摆伸进去", ["clothes_lift", "hand_under_skirt", "masturbation"]),
        ("上衣褪到一边肩膀", ["clothes_pull", "bare_shoulders", "masturbation"]),
        ("内裤拨到一边，裙子还穿着", ["panties_aside", "skirt", "fingering"]),
        ("上衣卷到胸口，下面什么都没穿", ["clothes_lift", "breasts_out", "bottomless", "fingering"]),
        ("衣服半褪在手臂上，人已经软了", ["open_clothes", "undressing", "orgasm", "on_bed"]),
    ],
    "bdsm_sex": [
        ("衣服被撕开还挂在绳子上", ["torn_clothes", "bondage", "open_clothes", "sex"]),
        ("项圈连着绳子，裙子被掀起来", ["collar", "leash", "skirt_lift", "sex"]),
        ("被命令自己把衣服脱到一半", ["undressing", "obeying", "blush", "standing"]),
        ("衣料被夹子扯着，整片敞开", ["clothes_pin", "open_clothes", "breasts_out", "trembling"]),
    ],
    "yuri_sex": [
        ("两人的衣服都只剩一边", ["open_clothes", "clothes_pull", "cunnilingus"]),
        ("裙子被对方掀起来", ["skirt_lift", "panties", "tribadism"]),
        ("上衣被推到锁骨，胸口贴着胸口", ["clothes_lift", "breasts_out", "breast_press"]),
        ("内裤挂在一只脚上", ["panties_around_one_leg", "fingering", "on_bed"]),
    ],
    "triple_sex": [
        ("衣服被两边一起扯开", ["clothes_pull", "open_clothes", "group_sex"]),
        ("裙子和内裤都被拽到腿弯", ["clothes_lift", "panties_around_one_leg", "sex"]),
    ],
    "hypno_sex": [
        ("被命令自己脱，手停在半路", ["undressing", "mind_control", "blank_eyes", "standing"]),
        ("衣服被脱到腰上，人还没醒", ["open_clothes", "undressing", "half-closed_eyes"]),
    ],
    "machine_sex": [
        ("衣服被机械臂扯开", ["clothes_pull", "torn_clothes", "machine", "sex"]),
        ("衣料被固定装置拉开", ["open_clothes", "machine", "breasts_out"]),
    ],
    "tentacle_sex": [
        ("触手从衣服破口钻进去", ["torn_clothes", "clothes_lift", "tentacles", "sex"]),
        ("衣服被缠住撕开大半", ["torn_clothes", "open_clothes", "tentacles"]),
    ],
    "after": [
        ("衣服皱在身上没穿好", ["open_clothes", "messy_clothes", "after_sex", "lying"]),
    ],
}

# ---------- 2. 新建 duo_sfw：男女双人·健全 ----------
# 从 duo_daily 里挑"一男一女也成立"的，再补几条男女特有的
DUO_SFW_NEW = [
    ("壁咚，手撑在墙上", ["kabedon", "hand_on_wall", "looking_at_another", "blush"]),
    ("替对方系领带", ["adjusting_necktie", "standing", "looking_at_another"]),
    ("并排坐着比手大小", ["comparing_hands", "sitting", "looking_at_another", "smile"]),
    ("靠在对方肩上睡着", ["head_rest", "sleeping", "sitting", "blush"]),
    ("被摸头，低头笑", ["headpat", "looking_down", "smile", "blush"]),
    ("挽着手臂走在街上", ["arm_hug", "walking", "smile", "outdoors"]),
    ("共撑一把伞，肩膀贴着", ["holding_umbrella", "rain", "shoulder-to-shoulder"]),
    ("从背后被抱住，回头看", ["hug_from_behind", "looking_back", "blush"]),
    ("额头相抵，闭着眼", ["forehead-to-forehead", "closed_eyes", "blush"]),
    ("被公主抱起来", ["princess_carry", "carrying", "looking_at_another"]),
    ("膝枕，低头看着", ["lap_pillow", "lying", "looking_down", "smile"]),
    ("手牵手走在前头", ["holding_hands", "walking", "from_behind"]),
    ("靠在窗边聊到天黑", ["through_window", "standing", "looking_at_another", "evening"]),
    ("一起看手机，头挨着头", ["looking_at_phone", "sitting", "head_rest"]),
    ("递过一杯热饮", ["holding_cup", "reaching", "smile"]),
]
DUO_SFW_FROM_DAILY = [
    "并肩走路", "背靠背坐着", "共撑一把伞", "互相喂食", "公主抱", "背着走", "摸头",
    "捏对方的脸", "靠肩打盹", "膝枕", "紧紧拥抱", "从背后抱住", "搂着肩", "搂着腰",
    "十指相扣", "对视", "一起躺下", "替她把头发梳顺", "帮对方整理领口", "亲额头",
    "扛在肩上", "一起野餐", "一起自拍", "一起看书", "依偎在沙发上", "睡在一起",
    "一起照镜子", "拍对方肩膀", "一起靠着栏杆", "搂着对方手臂", "互相整理头发",
    "抱着转圈", "摸着对方的脸", "举高高", "一起摆姿势", "一起跳双人舞",
    "靠在对方背上", "一起听同一副耳机", "互相靠着睡", "一起看窗外", "一起围着围巾",
]


def core_of(tags):
    """core = 动作核心词（去掉地点/光线/构图/表情类）"""
    drop = set()
    for k in ("places", "lights", "shots", "angles", "weather"):
        for it in A.get(k, []):
            drop.update(str(t).lower() for t in (it.get("tags") or []))
    return [t for t in tags if str(t).lower() not in drop]


A = json.load(open(P, encoding="utf-8"))
acts = A["actions"]

# --- R18 池补条目 ---
added_u = 0
for pool, items in UNDRESS.items():
    if pool not in acts:
        print("跳过不存在的池", pool); continue
    exist = set(x.get("zh", "") for x in acts[pool])
    for zh, tags in items:
        if zh in exist:
            continue
        c = core_of(tags)
        acts[pool].append({"zh": zh, "tags": tags, "core": c,
                           "lv": 4, "kind": "sex", "who": "m"})
        added_u += 1
print("R18 池补半脱条目:", added_u)

# --- duo_sfw ---
if "duo_sfw" not in acts:
    acts["duo_sfw"] = []
exist = set(x.get("zh", "") for x in acts["duo_sfw"])
added_s = 0
for zh, tags in DUO_SFW_NEW:
    if zh in exist:
        continue
    acts["duo_sfw"].append({"zh": zh, "tags": tags, "core": core_of(tags),
                            "lv": 1, "kind": "daily", "who": "duo"})
    added_s += 1
dmap = {x.get("zh"): x for x in acts["duo_daily"]}
for zh in DUO_SFW_FROM_DAILY:
    src = dmap.get(zh)
    if not src or zh in exist:
        continue
    acts["duo_sfw"].append({"zh": zh, "tags": list(src["tags"]),
                            "core": list(src.get("core") or core_of(src["tags"])),
                            "lv": 1, "kind": "daily", "who": "duo"})
    added_s += 1
print("duo_sfw 新建/追加:", added_s, "共", len(acts["duo_sfw"]), "条")

# meta 同步
m = A.setdefault("meta", {})
m.setdefault("actions", {})
for p, v in acts.items():
    m["actions"][p] = len(v)
m["total"] = sum(len(v) for v in acts.values())
json.dump(A, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("总条目", m["total"], "| 池数", len(acts))
