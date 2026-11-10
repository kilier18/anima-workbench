# -*- coding: utf-8 -*-
"""两段式提示词生成：LLM 只「填槽」，渲染器负责「联想 + 校验 + 去污染」。

对着用户提的三个毛病：
1) 只给一句话也要出完整画面 —— 槽位缺了按场景模板联想补，补了什么明确标出来（inferred，前端可点删）；
2) 幻觉 —— 角色/作品只认用户原文与词库别名，模型自报的角色一律丢弃；姿态/动作以原文中文线索为准，
   模型编的姿势（原文没说"躺"却给 lying）会被覆盖；
3) 污染 —— 质量词重复、正负串味、取景/机位/姿态互相矛盾、nude 与 panties 并存、中文残留、
   文件名、括号权重，全部按固定规则清掉，不靠模型自觉。
"""

import hashlib, os
import re

CJK = re.compile(r"[\u3000-\u9fff\uff00-\uffef]")

ANGLES = {"from_above", "from_below", "from_side", "from_behind", "dutch_angle", "from_front"}
POSES = {"on_back", "on_side", "on_stomach", "all_fours", "standing", "sitting", "kneeling",
         "lying", "squatting", "crawling", "against_wall", "on_bed", "wariza", "seiza", "hugging",
         "standing_sex", "bent_over"}
FRAMINGS = {"close-up", "upper_body", "cowboy_shot", "full_body", "portrait"}

SEX_ACTS = {"sex", "sex_from_behind", "missionary", "girl_on_top", "fellatio", "paizuri",
            "handjob", "masturbation", "cum_in_pussy", "facial", "anal", "oral",
            "standing_sex"}
ACTIONS_OK = {"sex", "sex_from_behind", "missionary", "girl_on_top", "fellatio", "paizuri",
              "handjob", "masturbation", "cum_in_pussy", "facial", "anal", "hug", "kiss",
              "breast_grab", "licking", "oral", "spread_legs", "standing_sex", "bent_over"}
EYE_COLORS = {"blue_eyes", "red_eyes", "green_eyes", "yellow_eyes", "purple_eyes",
              "brown_eyes", "black_eyes", "grey_eyes", "orange_eyes", "pink_eyes"}
HAIR_COLORS = {"blonde_hair", "brown_hair", "black_hair", "blue_hair", "red_hair", "white_hair",
               "pink_hair", "purple_hair", "green_hair", "grey_hair", "silver_hair", "orange_hair"}
QUALITY = ["masterpiece", "best quality", "very aesthetic", "absurdres", "highres"]
# 是否允许一名不露脸男性入镜（用户 2026-11-06 授权）。False 退回"只有 disembodied_penis"的老路线。
MALE_VISIBLE = True
# 性场景生理反应基础层：出汗 / 发抖 / 喘息（词库核实均存在）
PHYSIO_BASE = ["blush", "sweat", "trembling", "heavy_breathing"]
# 激烈程度线索：抽插/猛/激烈 → 更重的汗与体液
CUE_INTENSE = ("抽插", "猛", "激烈", "用力", "狂", "打桩", "撞击", "不停")
PHYSIO_INTENSE = ["very_sweaty", "pussy_juice_trail", "wet_hair"]
# 高潮 / 中出线索
CUE_CLIMAX = ("高潮", "去了", "忍不住", "中出", "内射", "射在", "射进", "颜射", "喷")
PHYSIO_CLIMAX = ["orgasm", "female_orgasm", "cum_overflow", "arched_back"]
CUE_AHEGAO = ("失神", "翻白眼", "阿黑颜", "ahegao", "崩坏")
CUE_STRONG2 = ("狠", "猛", "用力", "使劲", "狂", "粗暴", "干到", "操到", "打桩", "撞",
               "不停", "连续", "快速", "深插", "深喉", "掐", "抓头发", "撕")

# 动作 → 必然伴生的规范标签（只加"这个动作一定会出现"的东西，不塞场景物件）
COMPANIONS = {
    "sex":              ["spread_legs", "pussy_juice", "vaginal"],
    "sex_from_behind":  ["from_behind", "all_fours", "ass", "pussy_juice"],
    "missionary":       ["spread_legs", "pussy_juice", "from_above"],
    "girl_on_top":      ["straddling", "spread_legs", "pussy_juice"],
    "standing_sex":     ["leg_lift", "pussy_juice", "from_side"],
    "deep_penetration": ["pussy_juice", "pussy_juice_trail", "open_mouth"],
    "fellatio":         ["saliva_on_penis", "open_mouth", "kneeling", "penis"],
    "irrumatio":        ["saliva_on_penis", "open_mouth", "tears", "penis"],
    "deepthroat":       ["saliva_on_penis", "tears", "bulge"],
    "paizuri":          ["breast_press", "penis", "nipples"],
    "handjob":          ["penis", "pussy_juice" ],
    "cunnilingus":      ["spread_legs", "pussy_juice", "tongue_out"],
    "tribadism":        ["yuri", "spread_legs", "pussy"],
    "69":               ["spread_legs", "pussy_juice"],
    "cum_in_pussy":     ["cum", "cum_overflow"],
    "facial":           ["cum_on_body", "cum"],
    "female_ejaculation": ["pussy_juice_trail", "spread_legs", "arched_back"],
    "thigh_sex":        ["legs_together", "penis", "pussy_juice", "clothed_sex"],
    "legjob":           ["legs_together", "penis", "clothed_sex"],
    "pussyjob":         ["legs_together", "penis", "pussy", "clothed_sex"],
    "after_sex":        ["cum", "afterglow", "messy_hair"],
}
COMPANIONS.update({
    "fingering": ["pussy", "pussy_juice", "spread_legs"],
    "anal_fingering": ["anus", "ass"],
    "footjob": ["feet", "penis", "pussy_juice"],
    "double_penetration": ["group_sex", "sex", "penis", "2boys", "spread_legs"],
    "group_sex": ["sex", "penis", "2boys", "multiple_girls"],
    "threesome": ["group_sex", "sex", "penis", "2boys"],
    "spitroast": ["group_sex", "fellatio", "sex", "2boys"],
})
# 性场景 → 表情阶梯（越强越崩坏）
FACE_SEX_BASE   = []                      # 默认不写表情：底模自选最自然
FACE_LIGHT      = ["blush", "smile"]       # 原话点名羞涩 / 害羞 / 脸红 / 微笑才用
CUE_FACE_LIGHT  = ("羞涩", "害羞", "脸红", "害臊", "微笑", "浅笑", "笑意", "娇羞", "不好意思")
FACE_SEX_STRONG = ["ahegao", "tongue_out", "drooling", "half-closed_eyes"]
FACE_SEX_CLIMAX = ["open_mouth", "tongue_out", "rolling_eyes", "blush", "tears"]

# WAI v17 / Illustrious 社区实测：负面 4–6 词最稳，堆 12 词以上反而会把画面压糊
NEG_DEFAULT = ("bad quality, worst quality, worst detail, bad anatomy, bad hands, "
               "muscular_male, muscular, abs, bare_pectorals, back_muscles, "
               "bar censor, mosaic censoring, convenient censoring, pixelated, "
               "mosaic, blur censor, censored genitals")

# 中文线索 → 标签（原文优先于模型，避免"画个灵梦"被模型补成躺着）
CUE_POSE = [("侧躺", ["on_side"]), ("趴跪", ["all_fours"]), ("靠墙", ["against_wall"]),
            ("站", ["standing"]), ("躺", ["lying"]), ("坐", ["sitting"]), ("跪", ["kneeling"]),
            ("趴", ["on_stomach"]), ("蹲", ["squatting"]), ("爬", ["crawling"])]
CUE_ACTION = [("站立位性交", ["standing_sex", "sex_from_behind", "sex"]),
              ("站立性交", ["standing_sex", "sex_from_behind", "sex"]),
              ("站立后入", ["standing_sex", "sex_from_behind", "sex"]),
              ("立位性交", ["standing_sex", "sex_from_behind", "sex"]),
              ("后入", ["sex_from_behind", "sex"]), ("侧入", ["on_side", "sex"]),
              ("正常位", ["missionary", "sex"]), ("骑乘", ["girl_on_top", "sex"]),
              ("插入", ["sex"]), ("抽插", ["sex"]),
("指交", ["fingering"]), ("双指", ["fingering", "pussy"]), ("深入", ["fingering"]),
("阴蒂", ["clitoral_stimulation"]), ("肛门指交", ["anal_fingering", "anus"]),
("互相手淫", ["handjob", "masturbation"]), ("手淫", ["masturbation"]),
("足交", ["footjob"]), ("足底", ["footjob", "feet"]),
("双插", ["double_penetration", "group_sex"]), ("前后", ["double_penetration"]),
("群交", ["group_sex", "multiple_girls"]), ("3P", ["threesome", "group_sex"]),
("串烧", ["spitroast", "group_sex"]), ("三人", ["threesome", "group_sex"]),
("阿黑颜", ["ahegao"]), ("心形瞳孔", ["heart-shaped_pupils"]),
("乳射", ["cum_on_breasts"]), ("腹射", ["cum_on_stomach"]),
("磨豆腐", ["tribadism", "yuri"]),
("传教士", ["missionary", "sex"]), ("对坐", ["girl_on_top", "sitting_on_lap"]),
("抱起来", ["suspended_congress", "carrying"]), ("种付", ["mating_press", "missionary"]),
("69式", ["69"]), ("趴跪", ["all_fours", "kneeling"]), ("蹲坐", ["squatting"]),
("反向骑乘", ["girl_on_top", "reverse_cowgirl_position"]), ("抬腿", ["leg_lift"]),
("侧入", ["sex", "on_side"]), ("贴墙", ["standing_sex", "against_wall"]),
("素股", ["thigh_sex", "legs_together"]), ("股间", ["thigh_sex", "legs_together"]), ("腿交", ["thigh_sex", "legs_together"]), ("大腿夹", ["thigh_sex", "legs_together"]),               ("口交", ["fellatio", "oral"]), ("乳交", ["paizuri"]),
              ("手交", ["handjob"]), ("自慰", ["masturbation"]), ("摸自己", ["masturbation"]), ("自己摸", ["masturbation"]),
              ("内射", ["cum_in_pussy", "cum"]), ("中出", ["cum_in_pussy", "cum"]),
              ("颜射", ["facial", "cum"]), ("接吻", ["kiss"]), ("拥抱", ["hug"]),
              ("摸胸", ["breast_grab"]), ("舔", ["licking"])]
CUE_YURI = [("百合", ["yuri", "2girls"]), ("女女", ["yuri", "2girls"]),
            ("两个女孩", ["yuri", "2girls"]), ("两个女生", ["yuri", "2girls"]),
            ("磨镜", ["tribadism", "yuri", "2girls"]), ("互舔", ["cunnilingus", "yuri", "2girls"]),
            ("舔阴", ["cunnilingus"]), ("磨豆腐", ["tribadism", "yuri", "2girls"])]
CUE_FRAMING = [("特写", "close-up"), ("半身", "upper_body"), ("七分", "cowboy_shot"), ("全身", "full_body")]
CUE_CLOTH = [("黑丝袜", ["black_thighhighs"]),
             ("白丝袜", ["white_thighhighs"]),
             ("过膝袜", ["thighhighs"]), ("长筒袜", ["thighhighs"]), ("丝袜", ["pantyhose"]),
             ("黑丝", ["black_pantyhose"]), ("白丝", ["white_thighhighs"]),
             ("白衬衫", ["white_shirt", "shirt"]), ("衬衣", ["shirt"]), ("衬衫", ["shirt"]),
             ("水手服", ["serafuku", "school_uniform"]), ("校服", ["school_uniform"]),
             ("制服", ["school_uniform"]), ("连衣裙", ["dress"]), ("短裙", ["skirt"]),
             ("裙子", ["skirt"]), ("裤子", ["pants"]), ("和服", ["kimono"]), ("浴衣", ["yukata"]),
             ("泳装", ["swimsuit"]), ("比基尼", ["bikini"]), ("内衣", ["underwear"]),
             ("胸罩", ["bra"]), ("内裤", ["panties"]),
             ("全裸", ["nude"]), ("裸体", ["nude"]), ("裸", ["nude"])]
CUE_SCENE = [("秋天", ["autumn"]), ("秋季", ["autumn"]), ("黄昏", ["dusk"]), ("傍晚", ["twilight"]),
             ("清晨", ["morning"]), ("夜晚", ["night"]), ("夜里", ["night"]), ("白天", ["day"]),
             ("台阶", ["stairs"]), ("阶梯", ["stairs"]), ("楼梯", ["stairs"]), ("神社", ["shrine"]),
             ("鸟居", ["torii"]), ("海边", ["beach", "ocean"]), ("沙滩", ["beach"]), ("海", ["ocean"]),
             ("森林", ["forest"]), ("树林", ["forest"]), ("公园", ["park"]), ("教室", ["classroom"]),
             ("图书馆", ["library"]), ("浴室", ["bathroom"]), ("温泉", ["onsen"]), ("床", ["bed"]),
             ("雪", ["snow"]), ("雨", ["rain"]), ("樱花", ["cherry_blossoms"]), ("花", ["flower"]),
             ("回头", ["turning_head"]), ("回头看", ["turning_head", "looking_back"]), ("笑", ["smile"]),
             ("害羞", ["blush"]), ("哭", ["crying"]), ("生气", ["angry"]), ("惊讶", ["surprised"]),
             ("坐下", ["sitting"]), ("躺下", ["lying"]), ("奔跑", ["running"]), ("走路", ["walking"]), ("走着", ["walking"]), ("走过", ["walking"]),
             ("走向", ["walking"]), ("散步", ["walking"]), ("漫步", ["walking"]),
             ("看书", ["reading"]), ("睡觉", ["sleeping"]), ("弹琴", ["playing_instrument"]),
             ("长发", ["long_hair"]), ("短发", ["short_hair"]), ("双马尾", ["twintails"]),
             ("眼镜", ["glasses"]), ("帽子", ["hat"]), ("校服", ["school_uniform"]), ("和服", ["kimono"]),
             ("泳装", ["swimsuit"]), ("猫耳", ["cat_ears"]), ("翅膀", ["wings"])]

CUE_NSFW = ("裸", "脱", "胸", "乳", "内射", "中出", "射", "性", "做爱", "插", "口交", "自慰", "淫",
            "操", "干我", "干她", "上她", "办她", "弄她", "抽送", "骑上", "坐上去", "含住", "舔下面",
            "口爆", "颜射", "潮吹", "69", "磨镜", "磨豆腐", "插入", "插进", "湿了", "流水", "白浆",
            "精液", "露点", "走光", "翘臀", "夹住", "顶到", "怼", "打桩", "发情", "骚", "呻吟")

# 英文/日式罗马字线索：用户混写英文时也要能落到同一套标签
CUE_ACTION_EN = [
    ("fuck", ["sex"]), ("fucking", ["sex"]), ("creampie", ["cum_in_pussy", "cum"]),
    ("cum inside", ["cum_in_pussy", "cum"]), ("cumshot", ["cum"]), ("facial", ["facial", "cum"]),
    ("blowjob", ["fellatio", "oral"]), ("suck", ["fellatio", "oral"]), ("lick", ["cunnilingus"]),
    ("handjob", ["handjob"]), ("ride", ["girl_on_top", "sex"]), ("cowgirl", ["girl_on_top", "sex"]),
    ("doggystyle", ["sex_from_behind", "all_fours"]), ("from behind", ["sex_from_behind"]),
    ("missionary", ["missionary"]), ("standing sex", ["standing_sex", "standing", "sex"]),
    ("against wall", ["against_wall"]), ("wall slam", ["against_wall"]), ("kiss", ["kiss"]),
    ("hug", ["hug"]), ("grabbing breast", ["grabbing_another's_breast"]),
    ("tribadism", ["tribadism", "yuri"]), ("scissor", ["tribadism", "yuri"]),
    ("squirt", ["female_ejaculation"]), ("69", ["69"]), ("paizuri", ["paizuri"]),
    ("titjob", ["paizuri"]), ("footjob", ["footjob"]),
]

CUE_STATE_EN = [
    ("lying", ["lying"]), ("on back", ["on_back"]), ("on side", ["on_side"]),
    ("on stomach", ["on_stomach"]), ("all fours", ["all_fours"]), ("kneel", ["kneeling"]),
    ("sitting", ["sitting"]), ("squat", ["squatting"]), ("standing", ["standing"]),
    ("bent over", ["bent_over"]), ("on bed", ["on_bed"]),
]

CUE_SCENE_EN = [
    ("bedroom", ["bed", "indoors"]), ("bathroom", ["bathroom"]), ("shower", ["showering"]),
    ("sofa", ["sofa"]), ("couch", ["couch"]), ("office", ["office"]), ("classroom", ["classroom"]),
    ("outdoors", ["outdoors"]), ("beach", ["beach"]), ("forest", ["forest"]),
    ("shrine", ["shrine"]), ("onsen", ["onsen"]), ("car", ["car"]),
]

# ---------------- 语言延展层：中文口语 / 隐语 / 方言 → 真实标签 ----------------
# 全部标签已对本地词库（99372 条）校验，缺失项不进表。
CUE_ACTION_EXT = [
    ("被干", ["sex"]), ("我干", ["sex"]), ("干我", ["sex"]), ("干到", ["sex"]),
    ("上我", ["sex"]), ("被上", ["sex"]), ("弄我", ["sex"]), ("操我", ["sex"]), ("干她", ["sex"]), ("上她", ["sex"]), ("上了她", ["sex"]),
    ("办她", ["sex"]), ("弄她", ["sex"]), ("收拾她", ["sex"]), ("干起来", ["sex"]),
    ("抽送", ["sex"]), ("进进出出", ["sex"]), ("来回", ["sex"]), ("怼", ["sex"]),
    ("打桩", ["sex", "deep_penetration", "rough_sex"]), ("顶到", ["sex", "deep_penetration"]),
    ("插进", ["sex"]), ("插进去", ["sex"]), ("插着", ["sex"]), ("插了进去", ["sex"]),
    ("抽插", ["sex"]), ("插入", ["sex"]),
    ("骑上去", ["girl_on_top", "sex"]), ("骑乘", ["girl_on_top", "sex"]),
    ("骑着", ["girl_on_top", "sex"]), ("骑在", ["girl_on_top", "sex"]),
    ("坐上去", ["girl_on_top", "sex"]), ("坐着动", ["girl_on_top", "sex"]),
    ("女上", ["girl_on_top", "sex"]), ("自己动", ["girl_on_top", "sex"]),
    ("压着", ["missionary", "sex"]), ("扑倒", ["missionary", "sex"]),
    ("按在身下", ["missionary", "sex"]), ("面对面对", ["missionary", "sex"]),
    ("从背后", ["sex_from_behind", "sex"]), ("背对", ["sex_from_behind", "sex"]),
    ("背对镜头", ["sex_from_behind", "sex"]), ("屁股抬高", ["sex_from_behind", "all_fours"]),
    ("撅着", ["sex_from_behind", "all_fours"]), ("撅起", ["sex_from_behind", "all_fours"]),
    ("翘起屁股", ["sex_from_behind", "all_fours"]),
    ("抬腿", ["leg_lift", "sex"]), ("抬起腿", ["leg_lift", "sex"]), ("抱腿", ["leg_lift", "sex"]),
    ("扳腿", ["leg_lift", "sex"]), ("腿张开", ["spread_legs"]),
    ("含住", ["fellatio", "oral"]), ("吞进去", ["fellatio", "oral"]), ("吸", ["fellatio", "oral"]),
    ("嘬", ["fellatio", "oral"]), ("嗦", ["fellatio", "oral"]), ("口", ["fellatio", "oral"]),
    ("舔下面", ["cunnilingus"]), ("舔阴", ["cunnilingus"]), ("吃鲍", ["cunnilingus"]),
    ("撸", ["handjob"]), ("套弄", ["handjob"]), ("搓", ["handjob"]), ("打手枪", ["handjob"]),
    ("揉胸", ["grabbing_another's_breast"]), ("捏胸", ["grabbing_another's_breast"]),
    ("抓胸", ["grabbing_another's_breast"]), ("袭胸", ["grabbing_another's_breast"]),
    ("舔胸", ["licking_nipple"]), ("吸奶", ["licking_nipple", "nipple_stimulation"]),
    ("咬胸", ["licking_nipple"]),
    ("亲", ["kiss"]), ("舌吻", ["french_kiss", "kiss"]), ("咬唇", ["kiss"]), ("索吻", ["kiss"]),
    ("搂", ["hug"]), ("抱", ["hug"]), ("背后抱", ["hug_from_behind"]), ("抱在怀里", ["hug"]),
    ("摸腿", ["hand_on_another's_thigh"]), ("抚弄", ["hand_on_another's_thigh"]),
    ("按住", ["pinned"]), ("压住手腕", ["pinned"]), ("抓手腕", ["pinned"]),
    ("壁咚", ["against_wall"]), ("压墙", ["against_wall"]), ("抵在墙上", ["against_wall"]),
    ("内射", ["cum_in_pussy", "cum"]), ("射里面", ["cum_in_pussy", "cum"]),
    ("射进去", ["cum_in_pussy", "cum"]), ("灌进去", ["cum_in_pussy", "cum"]),
    ("中出", ["cum_in_pussy", "cum"]),
    ("射外面", ["cum"]), ("射肚子上", ["cum", "cum_on_stomach"]), ("弄在身上", ["cum"]),
    ("口爆", ["cum_in_mouth", "cum"]), ("射嘴里", ["cum_in_mouth", "cum"]),
    ("颜射", ["facial", "cum"]), ("射脸上", ["facial", "cum"]),
    ("喷了", ["female_ejaculation"]), ("潮吹", ["female_ejaculation"]),
    ("磨", ["tribadism"]), ("蹭", ["tribadism"]), ("互相舔", ["69", "cunnilingus"]),
    ("磨镜", ["tribadism", "yuri"]), ("磨豆腐", ["tribadism", "yuri"]),
]

CUE_STATE_EXT = [
    ("仰躺", ["on_back"]), ("朝天躺", ["on_back"]), ("朝上躺", ["on_back"]),
    ("侧身", ["on_side"]), ("侧躺", ["on_side"]), ("侧卧", ["on_side"]),
    ("趴着", ["on_stomach"]), ("趴下", ["on_stomach"]), ("卧倒", ["on_stomach"]),
    ("跪坐", ["wariza"]), ("正坐", ["seiza"]), ("坐着", ["sitting"]), ("坐到", ["sitting"]),
    ("蹲着", ["squatting"]), ("贴墙", ["against_wall"]), ("靠着墙", ["against_wall"]),
    ("趴跪", ["all_fours"]), ("四肢着地", ["all_fours"]), ("翘着屁股", ["all_fours"]),
    ("躺下", ["lying"]), ("倒在", ["lying"]), ("床上", ["on_bed"]),
]

CUE_FLUID_EXT = [
    ("湿了", ["pussy_juice"]), ("好湿", ["pussy_juice"]), ("湿得", ["pussy_juice"]), ("湿透", ["pussy_juice_trail"]), ("流水", ["pussy_juice"]),
    ("滴下来", ["pussy_juice_trail"]), ("淌", ["pussy_juice"]), ("水多", ["pussy_juice"]),
    ("白浆", ["cum"]), ("精液", ["cum"]), ("黏液", ["cum"]),
    ("汗水", ["sweat"]), ("口水", ["saliva"]), ("涎", ["saliva"]),
]

CUE_CLOTH_KEEP = ("穿着衣服", "穿着", "不脱衣", "衣服别脱", "别脱", "不脱", "隔着衣服", "衣物完整")

CUE_FACE_USER = [("微笑", ["smile"]), ("笑", ["smile"]), ("坏笑", ["smirk"]),
                 ("邪笑", ["evil_smile"]), ("媚笑", ["seductive_smile"]), ("轻蔑", ["smug"]),
                 ("眨眼", ["one_eye_closed"]), ("单眼", ["one_eye_closed"]),
                 ("闭眼", ["closed_eyes"]), ("无表情", ["expressionless"]),
                 ("面无表情", ["expressionless"]), ("挑逗", ["naughty_face"]),
                 ("翻白眼", ["rolling_eyes"]), ("张嘴", ["open_mouth"]),
                 ("伸舌", ["tongue_out"]), ("吐舌", ["tongue_out"])]

CUE_FACE_EXT = [
    ("脸红", ["blush"]), ("发红", ["blush"]), ("害羞", ["blush"]),
    ("喘", ["heavy_breathing"]), ("喘息", ["heavy_breathing"]), ("上气不接下气", ["heavy_breathing"]),
    ("呻吟", ["parted_lips"]), ("张嘴", ["parted_lips"]), ("叫出来", ["parted_lips"]),
    ("眯眼", ["half-closed_eyes"]), ("半睁", ["half-closed_eyes"]), ("眼神迷离", ["half-closed_eyes"]),
    ("快到了", ["orgasm"]), ("要去了", ["orgasm"]), ("去了", ["orgasm"]),
    ("受不了", ["trembling"]), ("腿软", ["trembling"]), ("发抖", ["trembling"]),
    ("抬头看", ["looking_up"]), ("低头", ["looking_down"]),
]

CUE_CLOTH_EXT = [
    ("半脱", ["undressing"]), ("褪到", ["undressing"]), ("脱一半", ["undressing"]),
    ("撩起", ["shirt_lift"]), ("掀起", ["skirt_lift"]), ("拉起裙子", ["skirt_lift"]),
    ("解开", ["undressing"]), ("敞开", ["shirt_lift"]),
]

CUE_SCENE_EXT = [
    ("沙发", ["sofa"]), ("浴室", ["bathroom"]), ("澡堂", ["bathroom"]),
    ("车里", ["car"]), ("车上", ["car"]), ("办公室", ["office"]),
    ("地毯", ["carpet"]), ("镜子前", ["mirror"]), ("阳台", ["balcony"]),
    ("厨房", ["kitchen"]), ("电梯", ["elevator"]), ("教室", ["classroom"]),
    ("图书馆", ["library"]), ("泳池", ["pool"]), ("温泉", ["onsen"]),
    ("走廊", ["hallway"]), ("天台", ["rooftop"]), ("仓库", ["warehouse"]),
]

CUE_BODY_EXT = [
    ("巨乳", ["huge_breasts"]), ("大胸", ["large_breasts"]), ("贫乳", ["small_breasts"]),
    ("翘臀", ["ass"]), ("屁股", ["ass"]), ("长腿", ["long_legs"]), ("美腿", ["thighs"]),
    ("锁骨", ["collarbone"]), ("肚脐", ["navel"]), ("细腰", ["slim_waist"]),
    ("大腿", ["thighs"]), ("胯", ["hips"]),
]

PLACE_PROPS = {
    "bedroom":   {"props": ["bed", "bed_sheet", "pillow"], "light": ["dim_lighting", "backlighting"]},
    "indoors":   {"props": ["window", "wooden_floor"], "light": ["window_light", "sunlight"]},
    "shrine":    {"props": ["shrine", "torii", "stairs", "stone_lantern", "gravel"], "light": ["dappled_sunlight", "sunset"]},
    "outdoors":  {"props": ["outdoors", "sky", "cloud", "grass"], "light": ["sunlight", "sunbeam"]},
    "bath":      {"props": ["bath", "bathtub", "steam", "tile_floor"], "light": ["dim_lighting"]},
    "classroom": {"props": ["classroom", "desk", "chair", "blackboard"], "light": ["window_light"]},
    "bathroom":  {"props": ["bathroom", "bathtub", "steam", "tile_floor"], "light": ["dim_lighting"]},
    "onsen":     {"props": ["onsen", "steam", "water", "rock"], "light": ["dim_lighting", "sunbeam"]},
    "office":    {"props": ["office", "desk", "chair", "window"], "light": ["window_light"]},
    "kitchen":   {"props": ["kitchen", "counter", "cupboard"], "light": ["window_light"]},
    "car":       {"props": ["car", "car_interior", "steering_wheel"], "light": ["dim_lighting"]},
    "library":   {"props": ["library", "bookshelf", "book"], "light": ["dim_lighting", "window_light"]},
    "warehouse": {"props": ["warehouse", "crate", "concrete_floor"], "light": ["dim_lighting"]},
    "hallway":   {"props": ["hallway", "door", "wooden_floor"], "light": ["dim_lighting"]},
    "pool":      {"props": ["pool", "water", "tile_floor"], "light": ["sunlight", "sunbeam"]},
    "rooftop":   {"props": ["rooftop", "sky", "city", "railing"], "light": ["sunset", "sunbeam"]},
    "balcony":   {"props": ["balcony", "railing", "sky"], "light": ["sunlight"]},
    "sofa":      {"props": ["sofa", "cushion", "living_room"], "light": ["window_light", "dim_lighting"]},
}
TIME_LIGHT = {"night": ["night", "dim_lighting"], "dusk": ["dusk", "sunset", "backlighting"],
              "evening": ["twilight", "backlighting"], "day": ["sunlight", "sunbeam"]}
MOOD_FACE = {"intimate": ["half-closed_eyes", "parted_lips", "blush"],
             "cheerful": ["smile"],
             "melancholy": ["expressionless", "looking_away", "closed_eyes"]}
# 情绪线索：原话没写情绪就不硬塞表情（用户嫌"看向观者"把构图掰正）
CUE_MOOD = [("笑", "cheerful"), ("开心", "cheerful"), ("高兴", "cheerful"),
            ("害羞", "intimate"), ("羞涩", "intimate"), ("色气", "intimate"),
            ("忧郁", "melancholy"), ("难过", "melancholy"), ("无表情", "melancholy")]

# 扩写只做"翻译"，不替用户补全画面：角色外貌 / 服饰 / 道具 / 光源
# 一律只在原话里提到时才输出（YG 2026-11-09 明确要求，别改回去）
NO_AUTOFILL = os.environ.get("EXPAND_NO_AUTOFILL", "1") == "1"

SLOT_SYSTEM = """你在给一个本地绘图流水线填槽。用户会给一句很短的话，可能只有十来个字。
你的任务：把这句话扩成一张完整画面所需的全部信息 —— 缺的地方按常识补，但**不许编角色名、不许编作品名、不许写质量词**。

只输出一个 JSON 对象，所有槽位都要尽量填满：
{
 "subject":{"count":"<1girl|2girls|...>","character":"","copyright":"",
            "traits":["<发型>","<发色>","<眼色>","<体型>"]},
 "pose":{"state":[],"action":[],"contact":[],"fluids":[]},
 "camera":{"framing":"<取景一个>","angle":["<机位一个>"]},
 "face":[],
 "hands":[],
 "clothing":[],
 "setting":{"place":"<地点>","props":["<物件1>","<物件2>"],"time":"<day|night|sunset>"},
 "light":["<光1>","<光2>"],
 "mood":["<氛围词>"],
 "scene_zh":"两三句中文，只描述原话和上面槽位里真有的东西（人物占画面多少、光从哪来、背景有什么）"
}
**尖括号和空数组只是格式示意，里面的值必须按用户原话重新生成，绝对不要照抄示例或沿用示例里出现过的词。**

硬规则：
1. 标签一律 danbooru 下划线小写英文；拿不准宁可不填（后面按词库校验，写错会被删）。
2. **只翻译，不补全**：原话没提到的物件、光源、服饰、外貌一个都不要加。
   setting.props 只在原话提到物件时填（≤2 个）；light 只在原话提到光/时间时填；
   traits 只在原话描述了外貌（发色/发长/胸/体型）时填，其余留空——角色名已经决定长相。
   traits：原话**点名了角色**时留空数组 []（角色名本身已决定外貌，模型猜的发型发色一定会错）；
   没点名角色时才填 4 个左右（发型/发色/眼色/体型）。clothing、face、hands 的填写条件见规则 9、10，不受本条约束。
   camera.angle 只写一个机位。scene_zh 里不许出现原话和槽位之外的外貌（发色、瞳色、衣服），也不许编造原话没有的姿势和动作（例如"回眸一笑"只能写回眸；"骑乘"是体位，不是骑马）。
3. **取景默认 full_body（全身，能看到完整动作）**；用户说"特写/半身/七分"才改。
4. 用户没提到的角色/作品，character 与 copyright 必须为空字符串。
5. 只有原话含性/裸意图时才填 action/contact/fluids/裸体服装；没有就留空。
6. **男性一律不出镜**：性行为只写体位/动作（sex、sex_from_behind、missionary、girl_on_top、fellatio…），
   不写 1boy、不写 male_focus、不写 faceless_male；需要出现阴茎时由下游自动补 disembodied_penis + penis。
7. 原话没说姿势就把 state 留空（下游按"站着"补），不要默认躺着。
8. count 按原话人数判断，单人写 1girl；完全没提人也要写 1girl。
9. **服装槽只在原话提到衣服时填**（原话说了"黑丝袜"就只填黑丝袜，不许自己加衬衫/裙子）；
   原话没提衣服就留空数组 []，让底模按角色本来穿什么画。
10. **face 槽不要默认 smile / looking_at_viewer / open_mouth**；原话没提表情就留空。
11. 原话说"站立位性交 / 站立后入 / 站着做"时：pose.state 填 ["standing"]，action 填 ["standing_sex","sex_from_behind","sex"]。
12. **人数守恒**：subject.count 必须等于原话人数。没提 3P/群交/轮奸/双插/两根/多人 就只能 1girl；没提 百合/女女/磨镜 就不能出现第二女性。
13. **体位守恒**：一个主位不拆成两个。后入就 `sex_from_behind`，不要再加 missionary / girl_on_top；传教士就 missionary，不要加 sex_from_behind。动作词只写原话点到的。
14. **禁止 eye_contact / looking_at_viewer**（除非原话"看镜头/对视/看着我"）——性场景会把人头拧 180°、脊柱掰直。
15. **服装与裸露只来自原话**：没提衣服就 `clothing: []`；没提裸/脱就不能写 nude/topless。角色本身的穿着由底模按角色 tag 决定。
16. **数量上限**：traits ≤ 4，props ≤ 3，light ≤ 2，action ≤ 5。禁止编造品牌、地名、人名、作品名。
17. **输出前自检**：逐个标签问一句"原话里有依据吗？"——找不到依据就删掉；宁缺勿造。
18. **禁止补全人物/服饰/道具**：不要给画面加第二个人、不要加原话没说的衬衫/裙子/丝袜/配饰、
   不要加床/枕头/窗帘/台灯这类陈设。地点与动作用原话的，其余交给下游组合抽词。
"""


def sanitize_plan(plan, text=""):
    """本地小模型扩写防幻觉：人数/服装/表情/机位/体位守恒，多余槽位直接砍掉。"""
    if not isinstance(plan, dict):
        return {}
    t = text or ""
    subj = plan.get("subject") if isinstance(plan.get("subject"), dict) else {}
    multi = any(k in t for k in ("3P", "3p", "三人", "群交", "轮奸", "双插", "两根", "前后夹击", "多人", "多p", "4P"))
    yuri = any(k in t for k in ("百合", "女女", "磨镜", "磨豆腐", "两个女", "双女"))
    if not multi:
        subj["count"] = "2girls" if yuri else "1girl"
    else:
        _pose0 = plan.get("pose") if isinstance(plan.get("pose"), dict) else {}
        _acts0 = [a for a in (_pose0.get("action") or []) if isinstance(a, str)]
        if not (set(_acts0) & {"threesome", "group_sex", "double_penetration"}):
            _acts0.append("threesome")
        _pose0["action"] = _acts0
        plan["pose"] = _pose0
    for k in ("character2", "character_2", "partner", "characters", "extra_characters"):
        subj.pop(k, None)
    plan["subject"] = subj
    if not clothing_mentioned(t):
        plan["clothing"] = []
    if not any(k in t for k in ("床", "枕", "桌", "椅", "窗", "灯", "镜", "书", "杯", "毯", "沙发",
                                "花", "树", "石", "水", "车", "门", "帘", "烛")):
        st = plan.get("setting") if isinstance(plan.get("setting"), dict) else {}
        st["props"] = []
        plan["setting"] = st
    if not any(k in t for k in ("光", "阳光", "月光", "灯", "夜", "白天", "黄昏", "傍晚", "清晨",
                                "阴天", "雨", "霓虹", "烛", "亮")):
        plan["light"] = []
    st2 = plan.get("setting") if isinstance(plan.get("setting"), dict) else {}
    if not any(k in t for k in ("发", "头发", "银", "金", "黑", "棕", "粉", "红发", "巨乳", "贫乳",
                                "大胸", "高个", "娇小")):
        subj["traits"] = []
        plan["subject"] = subj
    face_cue = any(k in t for k in ("表情", "笑", "哭", "喘", "害羞", "崩坏", "阿黑颜", "吐舌", "翻白眼",
                                    "失神", "媚眼", "挑逗", "舔唇", "脸红", "羞涩", "坏笑", "害羞地"))
    if not face_cue:
        plan["face"] = []
    if not any(k in t for k in ("看镜头", "看观者", "对视", "看着我", "直视", "看这边")):
        plan["face"] = [x for x in (plan.get("face") or []) if x not in ("eye_contact", "looking_at_viewer")]
    pose = plan.get("pose") if isinstance(plan.get("pose"), dict) else {}
    acts = [a for a in (pose.get("action") or []) if isinstance(a, str)]
    if any(a in acts for a in ("sex_from_behind", "doggystyle")):
        acts = [a for a in acts if a not in ("missionary", "girl_on_top", "cowgirl_position", "standing_sex", "on_back")]
    pose["action"] = acts[:5]
    plan["pose"] = pose
    plan["clothing"] = [x for x in (plan.get("clothing") or [])][:3]
    st = plan.get("setting") if isinstance(plan.get("setting"), dict) else {}
    st["props"] = [x for x in (st.get("props") or [])][:3]
    plan["setting"] = st
    plan["light"] = [x for x in (plan.get("light") or [])][:2]
    tr = subj.get("traits")
    if isinstance(tr, list):
        subj["traits"] = tr[:4]
    return plan


def _dedup(seq):
    out = []
    for x in seq:
        x = str(x or "").strip().lower()
        if x and x not in out:
            out.append(x)
    return out


def _kind(idx, tag):
    return (idx.get(tag) or {}).get("kind", "")


def clothing_mentioned(t):
    return bool(cloth_cues(t))


def cloth_cues(t):
    """服装线索：最长匹配优先并吃掉已匹配片段，避免"黑丝袜"同时命中 黑丝袜/黑丝/丝袜 出四五个同义标签"""
    left = t or ""
    out = []
    for k, v in sorted(list(CUE_CLOTH) + list(CUE_CLOTH_EXT), key=lambda kv: -len(kv[0])):
        if k in left:
            out += v
            left = left.replace(k, "")
    return _dedup(out)


def cues(text):
    t = text or ""
    pose, act = [], []
    for k, v in CUE_POSE:
        if k in t:
            pose += v
    low = t.lower()
    for k, v in list(CUE_ACTION) + list(CUE_ACTION_EXT) + [(a, b) for a, b in CUE_ACTION_EN if a in low]:
        if k in t:
            act += v
    cloth = cloth_cues(t)
    scene = []
    for k, v in list(CUE_SCENE) + list(CUE_SCENE_EXT) + list(CUE_BODY_EXT) + list(CUE_SCENE_EN):
        if k in t:
            scene += v
    yuri = []
    for k, v in CUE_YURI:
        if k in t:
            yuri += v
    fram = next((v for k, v in CUE_FRAMING if k in t), "")
    state_ext, fluid_ext, face_ext = [], [], []
    for k, v in list(CUE_STATE_EXT) + list(CUE_STATE_EN):
        if k in t:
            state_ext += v
    for k, v in CUE_FLUID_EXT:
        if k in t:
            fluid_ext += v
    for k, v in CUE_FACE_EXT:
        if k in t:
            face_ext += v
    face_user = []
    for k, v in CUE_FACE_USER:
        if k in t:
            face_user += v
    return {"pose": _dedup(pose), "action": _dedup(act), "cloth": cloth,
            "scene": _dedup(scene), "framing": fram, "yuri": _dedup(yuri),
            "state_ext": _dedup(state_ext), "fluid_ext": _dedup(fluid_ext),
            "face_ext": _dedup(face_ext),
            "face_user": _dedup(face_user),
            "cloth_keep": any(k in t for k in CUE_CLOTH_KEEP),
            "nsfw": any(k in t for k in CUE_NSFW)}


ANGLE_MAP = [("69", "from_side"), ("cunnilingus", "from_side"), ("tribadism", "from_side"),
             ("double_penetration", "from_side"), ("group_sex", "from_side"),
             ("spitroast", "from_side"), ("threesome", "from_side"),
             ("suspended_congress", "from_side"), ("standing_sex", "from_side"),
             ("sex_from_behind", "from_behind"), ("mating_press", "from_above"),
             ("missionary", "from_above"), ("paizuri", "from_above"), ("fellatio", "from_above")]


def apply_angle(tags, framing=""):
    """给一组现成标签补机位（场景直出通道用）：只留一个取景词，按行为补一个机位。"""
    tags = [str(t).strip() for t in tags if t]
    fr = framing if framing in FRAMINGS else ""
    have_fr = [t for t in tags if t in FRAMINGS]
    chosen = have_fr[0] if have_fr else fr
    if chosen in ("69",):
        chosen = "cowboy_shot"
    if any(t in ("69", "fellatio", "cunnilingus", "irrumatio") for t in tags) and chosen == "full_body":
        chosen = "cowboy_shot"
    out = [t for t in tags if t not in FRAMINGS]
    # 库里已写死机位的场景优先（例如 24 明确要 from_side），不要被 ANGLE_MAP 覆盖
    have_ang = [t for t in tags if t in ANGLES]
    ang = have_ang[0] if have_ang else next((a for k, a in ANGLE_MAP if k in tags), "")
    out = [t for t in out if t not in ANGLES or t == ang]
    if ang and ang not in out:
        out.append(ang)
    if chosen:
        out.append(chosen)
    return out

def render(plan, text, kitobj, idx, facts, zh_gloss):
    plan = plan or {}
    subj = plan.get("subject") or {}
    pose = plan.get("pose") or {}
    cam = plan.get("camera") or {}
    setting = plan.get("setting") or {}
    facts = list(facts or [])
    c = cues(text)
    # 用户显式点名 → 锁定，不再联想覆盖（反差表情/指定姿势是刻意的）
    _TAG_FACE = {"smile", "smirk", "evil_smile", "seductive_smile", "smug", "one_eye_closed",
                 "closed_eyes", "expressionless", "naughty_face", "rolling_eyes", "open_mouth",
                 "tongue_out", "ahegao", "blush"}
    face_pin = _dedup(list(c["face_ext"]) + list(c["face_user"])
                      + [t for t in _TAG_FACE if t in (text or "").lower()])
    pose_pin = bool(c["pose"] or c["state_ext"])
    # 原话里的场景/时间/动作词，模型漏了也要补回来（属于事实层，不是联想）
    facts = _dedup(facts + [t for t in c["scene"] if t in idx])
    # 只保留角色/作品/通用标签；画师 tag 除非用户点名，否则一律不进（防 alias 模糊命中）
    facts = [t for t in facts if _kind(idx, t) != "artist"]
    if any(k in (text or "") for k in ("画师", "画风", "kanpa", "カンパ", "artist")):
        facts = _dedup(facts + [t for t in (facts or [])])
    facts = [t for t in facts if not (idx.get(t) or {}).get("rating")]
    # 词库 alias 会把「骑乘」解析成骑马（riding）：原话没有马就一律当噪声剔除
    if not any(k in (text or "") for k in ("马", "骑马", "马背")):
        _HORSE = {"riding", "horseback_riding", "horse", "on_horse", "horse_riding",
                  "sitting_on_horse", "reins"}
        facts = [t for t in facts if t not in _HORSE]
    inferred = []

    # 1) 角色 / 作品：只认事实层（模型自报的一律不用）
    chars = [t for t in facts if _kind(idx, t) == "character"]
    char = chars[0] if chars else ""
    copyright_ = next((t for t in facts if _kind(idx, t) == "copyright"), "")

    # 2) 人数
    count = str(subj.get("count") or "").strip().lower()
    if count not in {"1girl", "1boy", "1other", "2girls", "2boys", "multiple_girls", "6+girls", "solo"}:
        count = "1girl"
        inferred.append("count")

    # 3) 取景：原文 > 模型 > 默认
    framing = c["framing"] or str(cam.get("framing") or "").strip().lower().replace("-", "_")
    if framing == "close_up":
        framing = "close-up"
    framing_inferred = False
    if framing not in FRAMINGS:
        # 实测：832×1216 下 full_body 的脸只有 75px（占画面高 6%），8 步档必糊；
        framing = "full_body"
        framing_inferred = True
        inferred.append("framing")

    angles = [a for a in (cam.get("angle") or []) if a in ANGLES][:1]   # 社区规则：机位只留一个
    if not angles:
        angles = ["from_side"]
        inferred.append("angle")

    # 4) 姿态 / 动作：只信原文线索；模型给的姿态一律不用（防"画个灵梦"被补成 lying）
    # 性行为/体位只能由原话引入：模型见过的词表里 sex 系标签极易被补进非性场景
    MODEL_POSE_ACTIONS = {"standing_sex", "bent_over"}
    _EXPLICIT_ONLY = set(SEX_ACTS) | {"sex", "hetero", "penis", "disembodied_penis",
                                      "girl_on_top", "cowgirl_position", "missionary",
                                      "sex_from_behind", "all_fours", "bent_over", "pov",
                                      "cum", "cum_in_pussy", "cum_in_mouth", "facial",
                                      "creampie", "after_sex", "afterglow"}
    actions = _dedup(c["action"] + [a for a in (pose.get("action") or [])
                                   if isinstance(a, str) and a in ACTIONS_OK
                                   and a not in MODEL_POSE_ACTIONS
                                   and a not in _EXPLICIT_ONLY])[:4]
    sex_act = [a for a in actions if a in SEX_ACTS]
    _framing_said = any(k in text for k, _ in CUE_FRAMING) or any(k in text for k in ("全身", "半身", "特写", "七分", "整个人"))
    # 回退：性场景保持 full_body，不再强改 cowboy_shot
    # 非插入式性行为（口/手/舔/女女）同样属于性场景：表情、背景、去污染规则必须一致
    SEX_CTX_EXTRA = {"oral", "cunnilingus", "tribadism", "handjob", "masturbation",
                     "paizuri", "69", "licking", "thigh_sex", "legjob", "pussyjob",
                     "double_penetration", "group_sex", "threesome", "spitroast",
                     "fingering", "anal_fingering", "footjob"}
    sex_ctx = bool(sex_act) or any(a in SEX_CTX_EXTRA for a in actions)
    strong_hint = any(k in (text or "") for k in CUE_STRONG2)         or any(k in (text or "") for k in CUE_INTENSE)         or any(a in {"deep_penetration", "irrumatio", "deepthroat"} for a in actions)
    climax_hint = any(k in (text or "") for k in CUE_CLIMAX)         or any(k in (text or "") for k in CUE_AHEGAO)
    # 非插入式性行为（乳交/口/手/舔/磨镜）不该带 sex/vaginal，也不该同时出两个阴茎标签
    PENETRATING = {"sex", "sex_from_behind", "missionary", "girl_on_top", "standing_sex",
                   "deep_penetration", "doggystyle", "anal"}
    NONPEN = {"paizuri", "fellatio", "irrumatio", "deepthroat", "handjob", "cunnilingus",
              "tribadism", "69", "licking", "masturbation", "thigh_sex", "legjob", "pussyjob"}
    if sex_ctx and (set(actions) & NONPEN) and not (set(actions) & PENETRATING):
        actions = [x for x in actions if x not in {"sex", "vaginal", "spread_legs"}]
        if "penis" in actions:
            actions = [x for x in actions if x != "disembodied_penis"]
    states = _dedup(list(c["pose"]) + list(c["state_ext"]))[:2]
    wall_hint = any(k in (text or "") for k in ("靠墙", "靠在墙", "墙边", "贴墙", "抵墙", "压墙", "抵在墙上"))
    standing_hint = wall_hint or any(k in (text or "") for k in ("站", "立位", "立姿"))
    if wall_hint and "against_wall" not in states:
        states = _dedup(states + ["against_wall"])
    if not states:
        states = ["standing"] if (standing_hint or not sex_ctx) else ["lying"]
        inferred.append("pose")
    # 体位互斥：骑乘不该躺、后背位不该正常位
    if "girl_on_top" in actions:
        actions = [a for a in actions if a not in {"sex_from_behind", "missionary"}]
        states = [s for s in states if s not in {"lying", "on_stomach"}]
    if "sex_from_behind" in actions:
        actions = [a for a in actions if a not in {"missionary", "girl_on_top"}]
    if "missionary" in actions:
        actions = [a for a in actions if a not in {"sex_from_behind", "girl_on_top"}]
    if sex_act:
        # 站立位性交：保留 standing，补 standing_sex，绝不退化成"只是站着"
        if "standing" in states or standing_hint:
            states = ["standing"] + [s for s in states if s in ("against_wall",)]
            if "standing_sex" not in actions:
                actions = ["standing_sex"] + [a for a in actions if a != "standing"]
                inferred.append("standing_sex")
            if "sex" not in actions:
                actions.append("sex")
        else:
            AMAP = {"girl_on_top": "sitting", "missionary": "lying",
                    "sex_from_behind": "all_fours", "fellatio": "kneeling",
                    "paizuri": "standing", "handjob": "sitting",
                    "cunnilingus": "lying", "tribadism": "lying", "69": "lying"}
            mapped = None if pose_pin else next(([AMAP[a]] for a in actions if a in AMAP), None)
            if mapped:
                states = mapped
                inferred.append("pose_from_action")
            elif not states:
                states = ["lying"]
                inferred.append("pose")
        angles = angles[:1]              # 性场景只留一个机位，避免 from_below+from_side 抢构图
        if "standing_sex" in actions:
            # 站立位：清掉一切"躺/趴/坐"姿态，避免 lying + standing_sex 打架画出骑乘
            states = ["standing"] + [s for s in states if s == "against_wall"]
            actions = [a for a in actions if a not in {"bent_over", "all_fours"}]
        else:
            states = [s for s in states if s not in {"standing", "bent_over"}]
    contacts = [x for x in (pose.get("contact") or []) if isinstance(x, str)][:3]
    fluids = _dedup([x for x in (pose.get("fluids") or []) if isinstance(x, str)][:3]
                    + list(c["fluid_ext"]))[:3]
    # 性行为必然 hetero；内射补 cum
    MALE_TAGS = {"1boy", "2boys", "multiple_boys", "male", "male_focus", "faceless_male",
                 "male_on_top", "male_penetrating"}
    yuri = list(c["yuri"])
    # 两个角色名 + 没有男性线索 → 判定百合（不用等用户说"百合"）
    if len(chars) >= 2 and not any(k in (text or "").lower()
                                   for k in ("男", "1boy", "boy", "futa", "扶他", "伪娘")):
        yuri = _dedup(yuri + ["yuri"])
    if yuri:
        # 女女：不加任何男性器官
        count = "2girls"
        actions = [a for a in actions if a not in MALE_TAGS | {"penis", "disembodied_penis", "hetero"}]
        actions += [t for t in yuri if t not in actions]
        inferred.append("yuri")
    elif sex_act or (set(actions) & {"paizuri", "handjob", "footjob", "thigh_sex", "legjob",
                                     "pussyjob", "breast_press", "penis"}):
        # 单人自慰不该凭空多一个男人：没有对方线索时按 solo 处理
        _SOLO_ACT = {"masturbation"}
        _solo = bool(set(actions) & _SOLO_ACT) and not any(
            k in (text or "") for k in ("一起", "互相", "对方", "帮", "他", "男", "两根", "插入"))
        if _solo:
            actions = [a for a in actions if a not in {"hetero", "1boy", "faceless_male", "penis",
                                                       "disembodied_penis", "pov"} | MALE_TAGS]
            if "solo" not in actions:
                actions.append("solo")
            inferred.append("solo")
        else:
            # 异性：用户已授权"一名不露脸男性入镜"，这样才看得出在性交
            actions = [a for a in actions if a not in MALE_TAGS - {"faceless_male", "1boy"}]
            actions.append("hetero")
            if MALE_VISIBLE:
                actions += ["1boy", "faceless_male"]
                if framing in ("upper_body", "cowboy_shot", "lower_body") and "pov" not in actions:
                    actions.append("pov")
            else:
                actions.append("disembodied_penis")
            if "penis" not in actions:
                actions.append("penis")
            inferred.append("male_visible" if MALE_VISIBLE else "male_hidden")
    # 素股/腿交只留 thigh_sex，不重复出 legjob/pussyjob
    if "thigh_sex" in actions:
        actions = [x for x in actions if x not in {"legjob", "pussyjob"}]
    elif "legjob" in actions:
        actions = [x for x in actions if x != "pussyjob"]
    if "cum_in_pussy" in (actions + fluids):
        fluids.append("cum")

    # 4.6) 生理反应层：出汗 / 发抖 / 喘息 / 体液 / 高潮（全部词库核实存在）
    physio = []
    if sex_ctx:
        physio += PHYSIO_BASE
        if any(k in (text or "") for k in CUE_INTENSE):
            physio += PHYSIO_INTENSE
        if any(k in (text or "") for k in CUE_CLIMAX):
            physio += PHYSIO_CLIMAX
        if {"sex", "sex_from_behind", "missionary", "girl_on_top",
            "standing_sex", "deep_penetration"} & set(actions):
            physio += ["pussy_juice", "vaginal"]
        if any(k in (text or "") for k in CUE_AHEGAO):
            physio += ["ahegao", "saliva_trail"]
        physio = _dedup([p for p in physio if p in idx])
    # 4.7) 伴生联想：动作必然带出的露骨标签（不掺场景物件）
    assoc = []
    if sex_ctx:
        for a in actions + list(fluids):
            assoc += COMPANIONS.get(a, [])
        if yuri:
            assoc += COMPANIONS["tribadism"]
        if climax_hint:
            assoc += ["fucked_silly", "mind_break", "excessive_cum", "messy_hair"]
        elif strong_hint:
            assoc += ["messy_hair", "very_sweaty"]
        _nude_asked = any(k in (text or "") for k in ("裸", "全裸", "脱", "一丝不挂", "光着"))
        _penetrating_now = bool(set(actions) & {"sex", "sex_from_behind", "missionary",
                                                "girl_on_top", "standing_sex", "deep_penetration"})
        _cloth_keep = bool(c.get("cloth_keep"))
        _clothed_act = _cloth_keep or bool(set(actions) & {"thigh_sex", "legjob", "pussyjob"})
        if _cloth_keep:
            assoc += ["clothed_sex", "cum_on_clothes"] if not clothing_mentioned(text) else ["clothed_sex"]
        elif _nude_asked or _penetrating_now or not _clothed_act:
            assoc += ["nude", "pussy"]
        else:
            assoc += ["clothed_sex"]
        if any(t in assoc for t in ("cum", "cum_overflow", "excessive_cum")):
            assoc += ["cum_on_body"]
        if "standing_sex" in actions:
            assoc = [t for t in assoc if t not in {"all_fours", "on_stomach", "lying", "ass"}]
        assoc = _dedup([t for t in assoc if t in idx])
    # 躺着/仰躺/侧卧时，口交伴生的 kneeling 与事实姿态冲突，剔除
    if {"lying", "on_back", "on_side"} & set(states):
        assoc = [t for t in assoc if t != "kneeling"]
        actions = [a for a in actions if a != "kneeling"]

    # 5) 表情 / 手 / 服装 / 氛围
    # 服装只认原话：点名了黑丝袜就只写黑丝袜；没点名就按角色原本衣服（不写任何服装标签）
    cloth_text = [t for t in c["cloth"] if t in idx]
    face_explicit = list(face_pin)[:4]
    hands_explicit = [h for h in (plan.get("hands") or []) if isinstance(h, str)][:2]
    cloth_in = []
    for x in (plan.get("clothing") or []):
        if isinstance(x, str):
            cloth_in.append(x)
        elif isinstance(x, dict):
            item = str(x.get("item") or "").strip().lower()
            if not item:
                continue
            color = str(x.get("color") or "").strip().lower()
            state = str(x.get("state") or "").strip().lower()
            if color and not color.endswith("_"):
                cloth_in.append("%s_%s" % (color, item))
                cloth_in.append(item)
            else:
                cloth_in.append(item)
            if state:
                cloth_in.append("%s_%s" % (state, item))
    if cloth_text:
        clothing = _dedup(cloth_text)[:4]
        # 原话只有袜子时，只留袜子；不补上衣/裙子
    else:
        clothing = []
        if cloth_in:
            inferred.append("cloth_dropped")
    if not c["nsfw"]:                      # 原话没有成人意图 → 不信模型给的裸体
        clothing = [x for x in clothing if x not in {"nude", "topless", "underwear", "panties", "bra"}]
    mood = [m for m in (plan.get("mood") or []) if isinstance(m, str)][:1]
    # 看向观者：只有原话点名「看镜头/看观者/对视」才加；性场景一律不加（会把人掰到正面，后入变骑乘）
    want_viewer = any(k in (text or "") for k in ("看镜头", "看观者", "看这边", "看过来", "对视",
                                                  "看着我", "直视", "eye_contact"))
    face = list(face_explicit)
    # 体液 / 汗水证据：崩坏表情只在「强烈 + 有体液汗水」时出现
    fluid_evidence = bool({"cum", "cum_in_pussy", "cum_overflow", "cum_on_body", "cum_on_breasts",
                           "facial", "pussy_juice", "pussy_juice_trail", "female_ejaculation",
                           "saliva", "saliva_trail", "drooling", "sweat", "very_sweaty"} &
                          set(fluids) | {t for t in [str(x) for x in (setting.get("props") or [])]})
    sweat_cue = any(k in (text or "") for k in ("汗", "汗水", "湿透", "白浆", "精液", "爱液", "潮吹", "内射", "射满", "灌满"))
    if not face:
        text_mood = next((v for k, v in CUE_MOOD if k in (text or "")), "")
        picked = text_mood or (mood[0] if mood else "")
        light_cue = any(k in (text or "") for k in CUE_FACE_LIGHT)
        if sex_ctx:
            if climax_hint:
                face = list(FACE_SEX_CLIMAX)
                inferred.append("face_climax")
            elif strong_hint:
                face = list(FACE_SEX_STRONG)
                inferred.append("face_strong")
            elif light_cue:
                face = list(FACE_LIGHT)
                inferred.append("face_light")
            # 其余情况：一个表情词都不写，交给底模
        elif light_cue:
            face = list(FACE_LIGHT)
            inferred.append("face_light")
        elif picked in MOOD_FACE:
            face = list(MOOD_FACE[picked])
            inferred.append("face")
    if sex_ctx and not face_pin:
        face = [f for f in face if f not in {"looking_at_viewer", "looking_away", "closed_eyes"}]
    # 机位唯一：后入只留 from_behind，站立位只留 from_side，其余按 ANGLE_MAP
    if sex_ctx:
        _want = ""
        if "sex_from_behind" in actions or "all_fours" in (list(states) + list(actions)):
            _want = "from_behind"
        elif "standing_sex" in actions:
            _want = "from_side"
        else:
            _want = next((a for k, a in ANGLE_MAP if k in actions), "")
        if _want:
            actions = [a for a in actions if a not in ANGLES or a == _want]
            states = [t for t in states if t not in ANGLES or t == _want]
            if _want not in actions:
                actions = [_want] + list(actions)
    hands = [h for h in hands_explicit if h in idx]

    # 6) 场景 / 道具 / 光线：空就联想
    PLACE_CUE = [("浴室", "bathroom"), ("澡堂", "bathroom"), ("淋浴", "bathroom"),
                 ("温泉", "onsen"), ("办公室", "office"), ("厨房", "kitchen"),
                 ("教室", "classroom"), ("图书馆", "library"), ("仓库", "warehouse"),
                 ("走廊", "hallway"), ("天台", "rooftop"), ("阳台", "balcony"),
                 ("车里", "car"), ("车上", "car"), ("泳池", "pool"), ("沙发", "sofa"),
                 ("卧室", "bedroom"), ("床上", "bedroom"), ("神社", "shrine"),
                 ("海边", "beach"), ("沙滩", "beach")]
    place = next((v for k, v in PLACE_CUE if k in (text or "")), "")
    place_cued = bool(place)             # 原话点名的地点，配额裁剪时必须保住
    if not place:
        place = str(setting.get("place") or "").strip().lower()
    if place not in PLACE_PROPS:
        place = "indoors"
        inferred.append("place")
    props = [p for p in (setting.get("props") or []) if isinstance(p, str)][:3]
    if not props:
        if NO_AUTOFILL:
            # 必要陈设可以补：只取该地点真正承托画面的 1–2 件（床/浴缸/台面），
            # 不塞整套餐具、窗帘、地灯这类多余违和道具
            _need = [p for p in PLACE_PROPS[place]["props"] if p != place][:2]
            props = _need
            if _need:
                inferred.append("props_need")
        else:
            props = PLACE_PROPS[place]["props"][:3]
            inferred.append("props")
    if sex_ctx:
        props = []                       # 性场景不塞背景物件，只留地点与一个光源
    light = [l for l in (plan.get("light") or []) if isinstance(l, str)][:2]
    if not light:
        tm = str(setting.get("time") or "").strip().lower()
        if NO_AUTOFILL:
            light = []                   # 原话没说光就不写光，页面组合抽词会补
        else:
            light = list(TIME_LIGHT.get(tm) or PLACE_PROPS[place]["light"])
            inferred.append("light")
    if sex_ctx:
        light = light[:1]                # 性场景只留一个光源

    skin_visible = bool({"nude", "topless", "completely_nude", "shirt_lift", "bra_lift"} & set(clothing))

    # 6.5) 密度补足：用户嫌提示词太少，按场景确定性补背景/光/身体细节
    ENRICH = {
        "outdoors": [["scenery"], ["sky", "cloud"], ["grass"], ["depth_of_field"], ["wind"]],
        "beach": [["sky", "cloud"], ["ocean", "wave"], ["sand"], ["depth_of_field"]],
        "bamboo_forest": [["scenery", "bamboo"], ["dappled_sunlight"], ["depth_of_field"]],
        "forest": [["scenery", "tree"], ["dappled_sunlight"], ["depth_of_field"]],
        "indoors": [["blurry_background"], ["depth_of_field"]],
        "bedroom": [["blurry_background"], ["lamp"], ["nightstand"], ["bed_sheet"], ["depth_of_field"]],
        "shrine": [["scenery"], ["stone_lantern"], ["torii"], ["gravel"], ["depth_of_field"]],
        "courtyard": [["scenery"], ["gravel"], ["depth_of_field"]],
        "bathroom": [["blurry_background"], ["steam"], ["depth_of_field"]],
        "onsen": [["steam"], ["water"], ["depth_of_field"]],
        "office": [["blurry_background"], ["window_light"], ["depth_of_field"]],
        "kitchen": [["blurry_background"], ["depth_of_field"]],
        "car": [["blurry_background"], ["depth_of_field"]],
        "library": [["blurry_background"], ["depth_of_field"]],
        "warehouse": [["blurry_background"], ["dim_lighting"], ["depth_of_field"]],
        "hallway": [["blurry_background"], ["depth_of_field"]],
        "pool": [["water"], ["sunlight"], ["depth_of_field"]],
        "rooftop": [["sky", "cloud"], ["city"], ["depth_of_field"]],
        "balcony": [["sky"], ["depth_of_field"]],
        "sofa": [["blurry_background"], ["depth_of_field"]],
    }
    pool = ENRICH.get(place, [["blurry_background"], ["depth_of_field"]])
    if sex_ctx:
        # 性场景只补虚化，不塞树/石头灯/云，否则构图被背景词稀释成"只是站着"
        pool = [["depth_of_field"], ["blurry_background"]]
    if "wind" in light:
        pool = pool + [["floating_hair"]]
    if skin_visible:
        pool = pool + [["collarbone"]]

    # 7) 组装
    ordered = []
    for ch in (chars or ([char] if char else [])):
        if ch not in ordered:
            ordered.append(ch)
    if copyright_:
        ordered.append(copyright_)
    ordered.append(count)
    BAD_TRAITS = {"faceless", "multiple_views", "bad_anatomy", "text", "watermark",
                  "multiple_expressions", "multiple_views", "english_text"}
    traits = _dedup([t for t in (subj.get("traits") or [])
                     if isinstance(t, str) and t not in BAD_TRAITS])[:6]
    # traits 只收词库里的通用外观标签；模型偶尔会把角色/作品名塞进来（例如 blank_(ff9)）
    traits = [t for t in traits if t in idx and _kind(idx, t) == "general"]
    if char:   # 已知角色：外貌由角色名决定，模型猜的发型/发色/瞳色/胸围一律丢（芙兰朵露是短发，别给她补 long_hair）
        traits = []
    elif not traits and not NO_AUTOFILL:
        traits = ["long_hair"]
        inferred.append("traits")
    ordered += traits[:3]
    # 人数标签自愈：异性/多人场景不该出现 multiple_girls/2girls（小模型常把负面词写进正向）
    _tset_now = set(ordered)
    if "yuri" not in _tset_now and "tribadism" not in _tset_now:
        ordered = [t for t in ordered if t not in ("multiple_girls", "2girls")]
    ordered += states + actions + physio   # 动作/体位/生理反应紧跟角色，权重不被背景词抢走
    ordered += assoc
    ordered += contacts + fluids
    ordered += face
    ordered += [t for t in facts if _kind(idx, t) == "general"][:6]
    ordered += hands
    ordered += clothing
    ordered += angles
    ordered += clothing[:0]
    ordered += props
    if place and place not in props:
        ordered.append(place)
    ANGLE_FOR = [("69", ["from_side"]), ("cunnilingus", ["from_side"]), ("tribadism", ["from_side"]),
                 ("double_penetration", ["from_side"]), ("group_sex", ["from_side"]),
                 ("threesome", ["from_side"]), ("spitroast", ["from_side"]),
                 ("suspended_congress", ["from_side"]), ("standing_sex", ["from_side"]),
                 ("sex_from_behind", ["from_behind"]), ("mating_press", ["from_above"]),
                 ("missionary", ["from_above"]), ("paizuri", ["from_above"]),
                 ("fellatio", ["from_above"])]
    # 行为 → 推荐机位（社区共识：69/双插/抱起/贴墙一律侧视，传教士/种付用俯视正面）
    angles = next((a for k, a in ANGLE_FOR if k in actions or k in assoc), [])
    if sex_ctx and not angles:
        angles = ["from_side"]
    ordered += light
    if framing == "full_body":
        ordered.append("eyelashes")
        inferred.append("face_detail")
    if want_viewer and not sex_ctx:
        # 原话点名看镜头/对视：非性场景直接落标签，不受取景限制
        ordered += ["looking_at_viewer", "eye_contact"]
        inferred.append("viewer")
    if ({"69", "fellatio", "cunnilingus", "irrumatio", "deepthroat"} & set(actions)) and framing == "full_body":
        framing = "cowboy_shot"
        inferred.append("framing_close")
    ordered.append(framing)

    # 8) 去污染
    dirty = {w.strip() for w in NEG_DEFAULT.split(",")}
    banned = dirty | set(QUALITY) | {"score_9", "score_8_up", "source_anime",
                                     "multiple_expressions", "english_text"}
    clean = []
    for t in ordered:
        t = str(t or "").strip().strip(",").lower()
        t = re.sub(r"^\(+|\)+$", "", t)
        t = t.split(":")[0].strip()
        if not t or CJK.search(t) or t in banned:
            continue
        if t.endswith((".safetensors", ".ckpt", ".pt", ".png", ".jpg", ".gguf")):
            continue
        if not re.fullmatch(r"[a-z0-9_\-() .]{1,60}", t):
            continue
        if t == "close_up":
            t = "close-up"
        clean.append(t)
    clean = _dedup(clean)
    if c.get("cloth_keep"):
        clean = [t for t in clean if t not in {"nude", "completely_nude", "topless", "bottomless",
                                               "pussy", "undressing", "clothes_removed", "skirt_lift",
                                               "shirt_lift", "bra_lift", "panties_removed"}]
    if "thigh_sex" in clean:
        clean = [t for t in clean if t not in {"legjob", "pussyjob"}]
    elif "legjob" in clean:
        clean = [t for t in clean if t != "pussyjob"]

    # 8.4) 扩写不补全：男性一律不出镜（下游 preflight 用 invisible_man 补）；
    #      原话没有性/裸意图就不许凭空加交合与裸露
    MALE_W = {"1boy", "2boys", "3boys", "faceless_male", "hetero", "male", "male_focus", "male_on_top"}
    clean = [t for t in clean if t not in MALE_W]
    _sex_text = any(k in (text or "") for k in (
        "做爱", "操", "插", "后入", "前入", "骑乘", "骑在", "口交", "舔", "含", "吸", "射",
        "内射", "中出", "裸", "脱", "露胸", "露乳", "露臀", "自慰", "磨镜", "腿交", "乳交",
        "足交", "性交", "上她", "干她", "插进"))
    SEXN = {"sex", "sex_from_behind", "missionary", "girl_on_top", "standing_sex",
            "doggystyle", "anal", "vaginal", "penis", "deep_penetration", "nude",
            "completely_nude", "topless", "bottomless", "pussy", "spread_legs",
            "pussy_juice", "cum", "uncensored", "fellatio", "cunnilingus", "paizuri",
            "handjob", "tribadism", "dry_humping", "grinding", "after_sex"}
    if not _sex_text:
        clean = [t for t in clean if t not in SEXN]

    # 8.5) 密度补足：普通场景补到 40；性场景补到 30（补多了主题会被冲淡）
    target = 34 if sex_ctx else 40
    if len(clean) < target:
        # 只补 3 个最贴场景的词（必要陈设/景深），不再把 ENRICH 五组全塞进来
        _add = [t for grp in (pool or []) for t in grp]
        for t in _add[:3]:
            if t in clean or not idx.get(t):
                continue
            clean.append(t)
        if not _add:
            inferred.append("thin")

    # 9) 矛盾清理：单取景 ≤2 机位、站/躺互斥、nude 不吃下装、性行为时去掉插兜
    final, seen_f, n_ang = [], False, 0
    pose_locked = None
    hair_locked = None
    for t in clean:
        if t in FRAMINGS:
            if seen_f:
                continue
            seen_f = True
        if t in ANGLES:
            if n_ang >= 1:
                continue
            n_ang += 1
        if t in {"standing", "lying", "on_side", "on_stomach", "sitting", "kneeling"}:
            if pose_locked and t in {"standing", "lying", "on_side", "on_stomach"} and t != pose_locked:
                continue
            pose_locked = pose_locked or t
        # 9.0) 冗余收敛：straddling / girl_on_top 已经表达了坐姿与骑乘，不再叠 sitting/lying/kneeling
        if ("straddling" in clean or "girl_on_top" in clean) and t in {"sitting", "lying", "kneeling"}:
            continue
        # 后入/趴跪已表达腿部姿势，spread_legs 会把它掰成正面张开腿
        if ("all_fours" in clean or "sex_from_behind" in clean) and t == "spread_legs":
            continue
        # 场景冗余：有 on_bed / bedroom 就不再单写床
        if ("on_bed" in clean or "bedroom" in clean) and t == "bed":
            continue
        if "nude" in clean and t in {"panties", "bra", "underwear", "shirt", "skirt", "dress"}:
            continue
        if t in HAIR_COLORS:
            if hair_locked:
                continue
            hair_locked = t
        if sex_ctx and t in {"looking_at_viewer", "eye_contact"} and not want_viewer:
            continue
        if sex_ctx and t == "smile" and not face_pin and any(f in FACE_SEX_STRONG + FACE_SEX_CLIMAX for f in face):
            continue
        if actions and t == "hands_in_pockets":
            continue
        final.append(t)

    # 9.35) 性场景常驻体液：汗水与爱液是性行为的默认状态，不靠联想也不靠用户说
    if sex_ctx:
        _const = ["sweat", "pussy_juice"]
        if any(a in actions for a in ("cum_in_pussy", "cum_overflow", "creampie")) or "cum" in fluids:
            _const.append("cum")
        for _t in _const:
            if idx.get(_t) and _t not in final:
                _i = final.index(framing) if framing in final else min(3, len(final))
                final.insert(_i, _t)

    # 9.4) 机位唯一（最终裁决）：后入/趴姿 → from_behind；站立位 → from_side；其余按 ANGLE_MAP
    if sex_ctx and ("sex_from_behind" in actions or "all_fours" in actions):
        # 底模后入本身很稳：同义标签堆叠反而让它画得不自然，这里做减法
        final = [t for t in final if t not in ("sex", "doggystyle", "arched_back")]
    if sex_ctx:
        _pref = ""
        if "standing_sex" in actions:
            _pref = "from_side"
        elif "sex_from_behind" in actions or "all_fours" in actions:
            _pref = "from_behind"
            # 后入三种机位：下体低角 → from_below+pov；侧视/前视 → from_side；默认背后
            if any(k in (text or "") for k in ("下体视角", "低角度", "从下", "仰拍", "下面看", "下方视角")):
                _pref = "from_below"
                if "pov" not in final:
                    final.append("pov")
            elif any(k in (text or "") for k in ("侧视", "侧面", "侧身", "正面看", "前视", "侧机位")):
                _pref = "from_side"
        else:
            _pref = next((a for k, a in ANGLE_MAP if k in actions), "")
        if _pref:
            final = [t for t in final if t not in ANGLES or t == _pref]
            if _pref not in final:
                _i = final.index(framing) if framing in final else min(4, len(final))
                final.insert(_i, _pref)

    # 9.5) 标签配额：性场景压到 24 个，动作/姿态/机位/取景必须保留，砍的是背景与装饰
    if sex_ctx:
        keep_always = (set(QUALITY) | set(chars) | {count} | set(states) | set(actions)
                       | set(angles) | {framing} | ({place} if place_cued else set())
                       | {"1boy", "2boys", "multiple_boys", "1girl", "2girls", "multiple_girls", "hetero", "yuri"})
        budget = 24
        if len(final) > budget:
            ranked = [t for t in final if t in keep_always]
            rest = [t for t in final if t not in keep_always]
            final = _dedup(ranked + rest)[:budget] if len(_dedup(ranked)) <= budget else _dedup(ranked)[:budget]
            # 保住尾部构图标签：framing/angles 若被截掉就补回
            for must in list(angles) + [framing]:
                if must and must not in final:
                    final.append(must)

    # 9.6) 配额补回会用旧 angles 覆盖裁决，这里再裁一次
    if sex_ctx and _pref:
        final = [t for t in final if t not in ANGLES or t == _pref]
        if _pref not in final:
            _i = final.index(framing) if framing in final else min(4, len(final))
            final.insert(_i, _pref)

    # 10) 词库校验：未知词剔除
    chk = kitobj.check(", ".join(final))
    tags = [("close-up" if t == "close_up" else t)
            for t in chk.get("tags", []) if not (idx.get(t) or {}).get("rating")]
    # 10.1) 口语固定搭配补全 + 归一（用户原话里"后穴/项圈"这类词不能只靠词库硬解）
    _t = text or ""
    _want = set()
    if any(w in _t for w in ("肛", "后穴", "菊花")):
        _want |= {"anal", "anus"}
        if any(w in _t for w in ("射", "内射", "注入")):
            _want |= {"cum_in_ass", "cumdrip"}
    if "项圈" in _t:
        _want |= {"collar"}
    if any(w in _t for w in ("牵", "绳子拉", "拴")):
        _want |= {"leash"}
    tags = ["heart-shaped_pupils" if t == "heart_shaped_pupils" else t for t in tags]
    if _want & {"1boy", "penis", "hetero"}:
        pass
    for _w in ("anal", "anus", "cum_in_ass", "cumdrip", "collar", "leash"):
        if _w in _want and _w not in tags:
            tags.append(_w)
    _ts = set(tags)
    if any(w in _t for w in ("相拥", "抱着睡", "余韵")) and not any(w in _t for w in ("女", "百合", "双女")):
        tags = [t for t in tags if t not in ("2girls", "multiple_girls")]
        for _w in ("1boy", "faceless_male", "hug", "afterglow"):
            if _w not in tags:
                tags.append(_w)
    if (_ts & {"1boy", "penis", "hetero"}) and "2girls" in _ts and not any(w in _t for w in ("女", "百合", "双女")):
        tags = [t for t in tags if t not in ("2girls", "multiple_girls")]

    # 体液规则（与场景直出同源）：没写射/中出/颜射/潮吹这类高潮词，就不该出乳白精液
    _FLUID_CUM = {"cum", "cum_in_pussy", "cum_in_ass", "cum_on_body", "cum_on_breasts",
                  "cum_on_hair", "cum_on_face", "cum_on_tongue", "cum_on_stomach",
                  "cumdrip", "cum_overflow", "excessive_cum", "bukkake", "facial",
                  "cum_on_penis", "cum_on_ass", "cum_in_mouth"}
    _FLUID_TEXT = ("中出", "内射", "射精", "射了", "射在", "颜射", "乳射", "肛内")
    if not any(k in text for k in _FLUID_TEXT):
        tags = [t for t in tags if str(t).strip().lower() not in _FLUID_CUM]
    # 最终幻觉清理：只保留原话有依据的机位/视线/腿部/敞开衣物
    _t = text or ""
    if sex_ctx and not any(k in _t for k in ("看镜头", "看观者", "对视", "看着我", "直视", "看这边")):
        ordered = [x for x in ordered if x not in ("looking_at_viewer", "eye_contact")]
    if not any(k in _t for k in ("抬腿", "举起腿", "腿抬高", "双腿上抬", "压胸", "抱腿")):
        ordered = [x for x in ordered if x not in ("legs_up", "leg_lift")]
    if not any(k in _t for k in ("敞开", "解开", "掀衣", "拉开", "敞胸", "露胸")):
        ordered = [x for x in ordered if x not in ("open_clothes", "shirt_lift", "bra_lift")]
    if not ({"yuri", "tribadism"} & set(ordered)):
        ordered = [x for x in ordered if x not in ("multiple_girls", "2girls")]
    tags = _dedup(ordered)
    # 10.8) 复核 8.4 与 9.0 —— ordered→tags 重建会丢掉前面的过滤，这里补一遍
    tags = [t for t in tags if str(t).replace(" ", "_").lower() not in MALE_W]
    if not _sex_text:
        tags = [t for t in tags if str(t).replace(" ", "_").lower() not in SEXN]
    _ts0 = {str(t).replace(" ", "_").lower() for t in tags}
    if _ts0 & {"all_fours", "sex_from_behind", "doggystyle"}:
        tags = [t for t in tags if str(t).lower() not in ("spread_legs", "legs_up", "legs_apart")]
    if "nude" in _ts0:
        tags = [t for t in tags if str(t).lower() not in ("panties", "bra", "underwear", "shirt", "skirt", "dress")]
    if "penis" in _ts0 and not (_ts0 & {"1boy", "2boys", "faceless_male", "futanari"}):
        # 画面里没有男性主体时，露出的阴茎换成"only 阴茎"，避免底模画出半透明插入者
        tags = ["disembodied_penis" if str(t).lower() == "penis" else t for t in tags]
    # 扶她硬规则（v3 实测）：`sex` 在 danbooru 几乎必然带 1boy，扶她改用 penis+vaginal，
    # 否则画面会多出一个男人。此规则同时写在 assistant.py 场景分支与 run_scene_batch.py。
    _low_t = {str(t).replace(" ", "_").lower() for t in tags}
    if "futanari" in _low_t and "sex" in _low_t:
        tags = [t for t in tags if str(t).replace(" ", "_").lower() != "sex"]
        if "penis" not in _low_t:
            tags.append("penis")
        if "vaginal" not in _low_t and "anal" not in _low_t:
            tags.append("vaginal")

    # 双人硬规则（v3 实测）：leg_lift / legs_up / legs_apart 会把插入方的腿也抬起来
    if set(tags) & {"futanari", "2girls", "multiple_girls", "yuri", "tribadism"}:
        tags = [t for t in tags if t not in ("leg_lift", "legs_up", "legs_apart", "one_leg_up")]


    pos = ", ".join(QUALITY + tags)
    # 打码防治（v3 实测）：性器/内射词会带出黑色马赛克
    _CENS = {"cum_in_pussy", "cumdrip", "cum_on_pussy", "spread_pussy", "pussy",
             "cum_in_ass", "after_vaginal", "after_anal", "female_ejaculation",
             "cum_overflow", "excessive_cum", "creampie", "sperm", "spilling"}
    _lowtags = {t.lower() for t in tags}
    if ((_lowtags & _CENS) or ("close-up" in _lowtags and any("cum" in t for t in _lowtags))) and "uncensored" not in _lowtags:
        tags.append("uncensored")
        pos = ", ".join(QUALITY + tags)

    inferred_tags = [t for t in tags if t not in facts and _kind(idx, t) not in ("character", "copyright")]
    fact_tags = [t for t in tags if t in facts]

    negative = NEG_DEFAULT
    if sex_act and not yuri:
        if MALE_VISIBLE:
            # 只压"肌肉男/男性特写"，不再压 faceless_male，否则男方被整个抹掉
            negative += ", male_focus, muscular_male, male_torso, abs"
        else:
            negative += ", 1boy, male, male_focus, faceless_male, muscular_male, male_torso"
    if c.get("cloth_keep"):
        negative += ", nude, completely_nude, topless, bottomless, nipples, pussy"
    if sex_act:
        # 分镜/多视图是"画成漫画格"的主因，负面直接压掉
        negative += ", multiple views, comic, split screen, 2koma"
    if framing == "full_body":
        negative += ", head_out_of_frame, feet_out_of_frame"
    _szh = str(plan.get("scene_zh") or "").strip()
    if _szh and not sex_ctx:
        # 非性场景的模型自述仍会编衣服（"早苗穿着工作制服"）：原话没提服装就整段丢掉
        _CLOTH_W = ("制服", "衬衫", "裙子", "连衣裙", "外套", "短裙", "校服", "和服", "巫女服",
                    "丝袜", "长袜", "短袜", "内裤", "胸罩", "睡衣", "卫衣", "牛仔裤", "马甲",
                    "领带", "围巾", "斗篷", "靴", "帽", "泳装", "浴巾")
        if not clothing_mentioned(text or "") and not c["cloth"]:
            if any(w in _szh for w in _CLOTH_W):
                _szh = ""
                inferred.append("scene_zh_dropped")
    return {
        "positive": pos,
        "negative": negative,
        "positive_zh": zh_gloss(pos),
        # 性场景的模型自述常与最终标签对不上（骑乘被写成骑马、躺床被写成站立），直接不显示，以 positive_zh 为准
        "scene_zh": "" if sex_ctx else _szh,
        "facts": fact_tags,
        "inferred": _dedup(inferred_tags),
        "inferred_slots": _dedup(inferred),
        "why": "你原话落地 %d 个标签；其余 %d 个是按场景联想补的，不要就点掉。" % (
            len(fact_tags), len(inferred_tags)),
        "params": {"steps": 30, "cfg": 5.5, "sampler": "euler_ancestral", "scheduler": "normal",
                   "width": 832, "height": 1216, "hires": True, "hires_scale": 1.5,
                   "hires_steps": 14, "hires_denoise": 0.45},
        "count": len(tags),
        "place": place,
        "mode": "plan",
    }
