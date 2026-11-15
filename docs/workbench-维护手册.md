# 工坊维护手册（workbench）

> 2026-11-14 建立。这份是给"以后的自己"看的：改哪儿、怎么验证、哪些东西不能碰。
> 方案本体在 `docs/multi-turn-连续动作-方案.md`，这里只讲工程。

## 0. 底模参数（速查）

> 底模参数速查统一见 `Anima知识-v3.md` §10（10 步 / CFG 1.0 / er_sde + beta / 1024×1536 / VAEDecodeTiled 512-64；turbo LoRA 1.0；Qwen3 0.6B 文本编码器、权重语法无效、画师要 @）。

**已知缺陷（2026-11-15）**：`cfg=1` 时负向完全不参与，负向里写的质量词/文字词/肌肉男全是白写。
原文档里"10 步 CFG1 最优"的实测表已按 YG 要求删除——那组数据不成立，且不适用于所有场景。
cfg 取值待实验（1.0 / 2.5 / 4.0 同 seed 对照）后再定，**改之前不要在代码里硬编码新值**。

---

## 1. 唯一的源文件与生成链

| 环节 | 路径 | 备注 |
|---|---|---|
| 源 | `D:\ComfyUI\tools\gen_workbench.py` | Python 里 `r"""..."""` 包住整页 HTML+CSS+JS，**改代码只改这里** |
| 产物 | `D:\ComfyUI\webui\workbench.html` | 生成物，别手改；改完刷新页面即生效 |
| 服务 | `D:\ComfyUI\webui\assistant.py` → `http://127.0.0.1:8190` | 静态直读 workbench.html，前端改动不用重启 |
| 抽取 | `_style_test\extract_wb.py` | 把产物里的 `<script>` 抽成 `_wb_check.js` 供 node 测试；**必须 UTF-8**（老版本用 PowerShell 抽，按 GBK 读成乱码，中文正则全失效） |

一条命令跑完「生成 → 抽取 → 语法 → 全部回归」：

```
node D:\ComfyUI\_style_test\run_all.js
```

手工分步：

```
& D:\ComfyUI\ComfyUI_windows_portable\python_embeded\python.exe D:\ComfyUI\tools\gen_workbench.py
& D:\ComfyUI\ComfyUI_windows_portable\python_embeded\python.exe D:\ComfyUI\_style_test\extract_wb.py
node --check D:\ComfyUI\_style_test\_wb_check.js
```

## 2. 测试清单（改完必跑）

| 脚本 | 覆盖 |
|---|---|
| `test_story.js` | 五阶段分配、衣物链单调、地点/光照锁定、seed 派生、单张模式不受影响 |
| `test_beat.js` | 景别节拍、姿势互斥、玩法阶梯（足→手→乳→口，按种子洗牌）、严格/松散档、玩法段去结算词 |
| `test_preflight.js` | 审查层：人数/性别/衣物/时间词/崩脸 |
| `test_plan.js` | 各档位池配比不塌（after 结算向 ≥5 等） |
| `check_face.js` | 贴头动作+全身+侧视 → 换背面/七分身；表情堆叠上限；丝袜三态 |
| `test_batch_sim.js` | **端到端仿真**：在 vm 里喂假 fetch 真跑 `batchRun()`，验证不抛异常、按钮复位、seed +1000、地点恒定、回放槽写入、池子空掉也不崩 |
| `test_core.js` | 状态机与归一化：`addTag` 的 `noUser`、`recount`/`pickChar`/`pickOutfit`/`applyField` 不污染 `userTags`、归属表清理、清空服饰快照、`zhOf` 缺表、连字符↔下划线互认、袜类去重、生成器 `node --check` 门禁 |

`test_batch_sim.js` 是这次故障之后加的：它用 `wb_outfits.json` 的**真实形状**（`{items:[...], _meta}`）喂进去，正是这个形状差异让批量按钮锁死。

## 3. 不变式（改代码时不许破）

1. `S.lib.outfits` 是**对象**（`{items:[], _meta}`），不是数组。任何读它的地方都要 `Array.isArray(x)?x:(x.items||[])`。
2. 一批图：**地点、光照、天气、角色、那身衣服整批恒定**；只有机位可按阶段变。
3. 衣物链只减不增：`full → open → partial → none`（事后段可回 `partial`），且状态词不锁具体哪一身，`S.storyOutfit` 负责"哪一身"。
4. 结算词（`cum_* / creampie`）不许出现在玩法段；`pussy_juice` 这类过程词可以在。
5. 批处理任何一张出错都不许让 `btnBatch` 停在 disabled：`batchRun` 主体是 `try/catch/finally`，收尾统一复位 `S.batch`、`btnBatch`、`btnPause`、`btnGen`。
6. 页面侧一切"用户改了参数就立刻生效"的下拉（丝袜/参考图/自由度）都要在 `batchRun` 开头重读一次 DOM，不能只依赖 `onchange`。
7. **`userTags` 只装"人写进去的词"**：程序补的结构词（`1girl/solo/2girls`、画风字段、校验补词）一律 `addTag(x, {noUser:true})`。否则清空正文后这些词会被"重建库"逻辑拼回去——这是"点了清空还剩 1girl"的根因。
8. **删除必须走 `delTag`**：`delTag` 同时清 `tags`/`userTags`/`sceneTags`/`owner` 四处。手写 `S.tags = S.tags.filter(...)` 会留下归属残留，下一批又拼回来。
9. **词表比较一律归一化**：`K()`（`[\s-]+ → _`）是唯一口径。表里写 `face-to-face`、正文写 `face_to_face` 必须互认，`has()`/`cut()` 两侧都要 `low()`（preflight 的 `cut` 已改成 `new Set(ks.map(low))`）。
10. `catch{}` 不许空着：最小也要 `logline("xxx","ERR "+e)`。丝袜段与 `pfDryRun` 曾经整段静默失效，测试全绿但功能没跑。

## 3.5 生成门禁（2026-11-14 加）

`gen_workbench.py` 的 `main()` 现在先 `check_js(HTML)`：把内联 `<script>` 抽出来跑 `node --check`，**语法错就 `SystemExit`，不写 `workbench.html`**。JS 全在 `r"""..."""` 里，写错一个引号就是整页空白，靠人眼看是看不出来的（所以改完 JS 先跑一次生成，门禁不过就不写盘，页面不会坏）。

> 坑：在 `r"""` 内部写注释时**不能出现三个连续双引号**（`r"""` 会提前结束字符串，`SyntaxError: invalid character`），要写"HTML 内联 script"。

## 3.6 服务端判定顺序（assistant.py）

`gen_poll` 的判定顺序必须是「先 error → 再 success/outputs → 再查 `/queue` 判丢」。老版本先判 success 会把"有 outputs 的失败任务"报成 done，且只看 `/history` 不查 `/queue`，ComfyUI 一重启前端就永远转圈。现在丢了返回 `{"state":"lost"}`，前端轮询认这个状态并提示"任务在 ComfyUI 里丢了"。


## 4. 已知故障与根因（别再踩）

| 现象 | 根因 | 修法 |
|---|---|---|
| 点「🎬 批量出图」没反应（按钮灰着） | `storyOutfitPick()` 对 `S.lib.outfits` 直接 `.map`，而它是 `{items:[]}` 对象 → 抛 `lib.map is not a function`，在进循环前就死了，`btnBatch.disabled` 永远停在 true | 形状兼容 + `try/finally` 复位 + 载入时复位 |
| 第 7 张人头扭曲 | 贴头动作（whispering+hug_from_behind）+ `full_body` + `from_side`，两个头只占几十像素，再叠 4 个极端表情 | `HEAD_NEAR` 规则换 `from_behind`/`cowboy_shot`；表情上限 2–3；全身图不塞气泡 |
| 衣物"穿回去" | `HALF_W` 里含 `open_clothes`，判定"已经半脱"就不补脱衣 | `HALF_STRICT` 独立判定集 + 先 `cut(['open_clothes'])` |
| 第 2 张就演完正戏 | 条目不属任何池时 `POOL_RULE` 算不出类型，`noActPool=false` → 强插 sex | `noActPool` 追加「前段（full/open）不插正戏」 |
| 精液出现在刚脱完衣服那张 | 足交条目自带 `cum_on_feet` | `preflight` ⑤e：玩法段剔结算词 |
| 地点精神分裂（"咖啡馆的床上"） | 只过滤候选条目，动作自带的地点词漏网；`on_desk` 这种带介词的前缀匹配不到组 | `placeGroupOf` 去介词前缀 + 组装完 tags 再剔异组地点词 |

## 5. 数据文件

| 文件 | 内容 | 注意 |
|---|---|---|
| `webui\data\wb_atoms.json` | actions(37 池 / 1529 条)、places 38、lights 16、weather 8、shots 4、angles 7、intensity 5、phys | 只做加法，别改已有条目的 `zh`（`usedActs` 去重按 `zh`） |
| `webui\data\wb_outfits.json` | `{items:[...140], _meta}` 服饰道具 | 备份在 `.bak-1114`；加条目要同步 `_meta.n` |

## 6. 目录卫生

`_style_test` 只留：9 个测试脚本（`test_story` / `test_beat` / `test_preflight` / `test_plan` / `check_face` / `check_male` / `test_batch_sim` / `test_core` / `test_rules`）+ `run_all.js`（串成 12 步）+ 4 个工具（`extract_wb.py` / `dry_story.js` / `run_story_ref.js` / `review_sheet.py`）+ 最近的跑批 json/log + 对照图。一次性的 `_patch_*.py`、`_peek*.py`、拼图中间产物用完即删——2026-11-14 清过一轮（285 项 / 约 900MB）。

## 11. 已知边界：角色 LoRA 会把衣服「烘死」

同一组提示词（`... completely_nude, nude, sex, [场景], cowboy_shot`）换角色卡结果完全不同 —— `hakurei_reimu` 这张卡把衣服烘进了 LoRA，纯提示词拿不掉（正向加 `nude / topless / bottomless`、负向加 `dress / skirt / apron / uniform` 都无效）。
`completely_nude` 在这类卡上实际渲染成「衣不蔽体 / 敞开露出」，不是全裸。
要真全裸只有换角色卡（或换 nude 变体 LoRA / 第二段 LoRA 覆盖）—— 换角色卡才能解决。

## 12. 分区路由 / 无男分区 / 包触发词（2026-11-14 晚）

### 12.1 剧情模式必须尊重「分区」下拉
以前 `poolPlan()` 一进 `if(phase)` 就 return 阶段池，`qScene`（分区）在连续剧情里完全失效 —— 选「触手」还是从 duo_/foreplay_ 抽。

现在：
- `sceneType()` 先读 `#qScene`，读不到（无 DOM 的测试/干跑）回落 `S.sceneType`。
- `familyPoolsOf(phase, tier, fam)` 做「族 → 阶段 → 池」映射：
  | 阶段 | duo | 其它族（solo/machine/tentacle/yuri/triple/bdsm/hypno/exhibition） |
  |---|---|---|
  | setup | duo_daily | `<fam>_daily` |
  | foreplay | duo_flirt | `<fam>_flirt` |
  | play / sex | duo_male | `<fam>_sex` |
  | after | after | 人形族回落 `after`；tentacle/machine/solo/exhibition/voyeur 仍用 `<fam>_sex` |
- 候选链 `<fam>_want → <fam>_<tier> → <fam>_sex → <fam>_flirt → <fam>_daily`，命中即用。
- `ACT_GROUPS` 主行为组：池名以 `tentacle` 开头强制 group 4、`machine` 强制 group 5，否则触手词会被 `fingering/handjob` 抢走主行为组、当成冲突剔掉（"触手图没触手"的真因之一）。

### 12.2 无男分区不许长出男人
`faceless_male / hetero` 有三条来源都会往单人/触手/机械/女女画面里塞人：
1. `normTags` 的 R18 注入（`ACT_R18` 整串带 `sex,1boy,faceless_male,hetero`）；
2. `needMale()`（词面有性动作就补男）；
3. `preflight` 的池规则 m:1 / m:2 /「手写兜底」/ after 段的 `passive` 中文正则。

现在统一用 `femPool`（池名或分区属于 solo/machine/tentacle/yuri/voyeur）一刀切：
- `noActPool` 含 `femPool` → 不注入 ACT_R18；
- `if(!femPool) a = needMale(a);`；
- `preflight` 里 `famFem ? false : (...)` 让 `needBody` 恒 false，m:1 分支改为 `cut(PF_MALE)+cut(MALE_BODY)` ——
  **只剔"人形"，不动动作**（`MALE_POS` 里 `sex`/`vaginal`/`double_penetration` 是行为不是男体，
  一起删会让触手/机械分区整块变成裸体空镜，190 张抽卡 #154–#159 实测）；
- ⑦「手写兜底」加 `!/^(solo|machine|tentacle|yuri|voyeur)$/.test(o.family)`。
- 三处 `preflight` 调用都要带 `family: String(S.sceneType||'')`（页面 + 探针 + 干跑脚本）。

### 12.3 换包必须先清旧触发词
`pickStyle()` 只 `addTag(新 trig)`、从不删旧 trig；而旧 trig 早已被 addTag 写进 `S.tags` 与 `S.userTags`，于是「跑完大肥鱼 LoRA 再跑原版角色 tag」也带着 `deepseek_whale_girl_zipzippipe`。

现在 `stripStaleTriggers()` 把「当前没选的 style/charLora」的 trig 全部摘掉（tags + userTags + owner），在 `pickStyle` 与 `batchRun` 开头各调一次（双保险）。

### 12.4 负向默认表加了文字类
A/B 实测：触手图会自己长出日文拟声词气泡，而正文里没有 `speech_bubble`。`DEF_NEG` 追加 `text, speech bubble, japanese text, watermark, signature`。

### 12.5 景别标签以「最终词」为准
`preflight` 的物理冲突规则会把特写顶回全身，日志若还写 compose 时的意图就会「日志说特写、图是全身」。日志与回放改用 `shotZhFromTags(S.tags)`。

## 13. 区块制排片与"衣服是状态不是动作"（2026-11-14）

### 13.1 为什么放弃"连续性硬接动作"
用户判断（原话）："其实感觉还是连续性强行接上下的动作导致的，你这个脱衣服他本来应该是衣着的状态形容词而不是一个脱衣服的动作。""真的要让他完全做到像视频那样的连续性是不可能的，图片的优势就是只要大概接近，完全可以用人脑补出来。"

结论写成规矩：
- **衣着只给状态词**：`open_clothes` / `partially_clothed` / `completely_nude` / `clothed_sex`。
- **脱衣动作词在剧情模式一律剔除**：`undressing` / `clothes_lift` / `skirt_lift` / `clothes_pull` / `skirt_pull` / `shirt_lift` / `dress_lift` / `bra_lift` / `panty_pull` / `clothes_in_mouth` / `adjusting_clothes` / `getting_dressed` / `dressing` / `putting_on_clothes` / `taking_off_clothes`。
  原因：这些词进了画面就是"双手正在脱"，跟手交/乳交同框直接多出一只手；跟足交同框就是"一边脱一边足交"。
- 连续性只求"大致接近"，不再为每个块硬补动作动词。

实现位置：`gen_workbench.py` 的 `preflight` 里 `if(o.forceGarb){ ... if(o.forceStory){ cut([...脱衣动作词...]) } ... }`；partial 段只补 `partially_clothed`；⑤d 的 partial 分支只保证状态词存在（`GARB_CHAIN` 已删，别再去代码里找）。

### 13.2 区块制（BLOCK_DEFS）
一张一批不再按"阶段"均匀散抽，而是按**块**：一块 = 一个动作类型，块内连排 N 张做差分。

| 块 | 阶段 | 衣着 | 权重 | 池 | core（必须命中） | add（缺则补） |
|---|---|---|---|---|---|---|
| 前戏 foreplay | foreplay | open | 6（n<100 折半为 3） | foreplay_flirt / foreplay_sex | — | — |
| 口交 oral | play | partial | 6 | oral_sex | fellatio / licking_penis / blowjob / deepthroat / cum_in_mouth | — |
| 乳交 paizuri | play | partial | 9 | paizuri_sex | paizuri / breast_press / titjob | penis |
| 手交 handjob | play | partial | 9 | handjob_sex | handjob | penis |
| 足交 footjob | play | partial | 8 | footjob_sex | footjob / toes / soles | footjob + soles + penis |
| 正面位 missionary | sex | none | 13 | duo_male / foreplay_sex / solo_sex | missionary / mating_press / sex / vaginal | missionary + sex + vaginal |
| 后入 doggy | sex | none | 13 | duo_male / solo_sex / triple_sex | sex_from_behind / doggystyle / doggy_style / sex / vaginal | sex_from_behind + sex + vaginal + all_fours |
| 骑乘 ride | sex | none | 9 | yuri_sex / triple_sex / duo_male | cowgirl_position / reverse_cowgirl_position / girl_on_top / straddling | cowgirl_position + girl_on_top + sex + vaginal |
| 站立抱起 stand | sex | none | 9 | duo_male / exhibition_sex / solo_sex | standing_sex / carrying | standing_sex + sex + vaginal + carrying |
| 侧入 side | sex | none | 9 | duo_male | on_side / sex / vaginal / leg_lift / legs_together | sex + vaginal |
| 3P threesome | sex | none | 6 | triple_sex / group3p | threesome / group_sex / 3boys / double_penetration | threesome + sex |
| 触手 tentacle | sex | none | 6 | tentacle_sex | tentacle_sex / tentacles | tentacle_sex + tentacles |
| 机械 machine | sex | none | 4 | machine_sex | sex_machine / object_insertion / vibrator | sex_machine + object_insertion |
| 事后 after | after | partial | 6 | after | — | — |

`blockPlanOf(n)`：权重配额 + 最大余数分配；`span = Math.max(6, Math.ceil(n / Math.max(1, Math.ceil(n / 25))))`；即场数按 25 张一场向上取整，每场最少 6 张。整块装场：一块不许跨场，收尾不足 6 张的小场并进上一场。

### 13.3 五条硬规则（都是真机踩出来的）
1. **单角色剔除女女条目**：骑乘/后入池含 `yuri_sex`，单角色抽到就是"两个女生"。`pickBlockAct` 里按 `2girls/3girls/yuri/lesbian` 过滤。
2. **机位与姿势对位**（preflight）：正面位禁 `from_behind`；后入禁 `pov/from_below`；骑乘禁 `from_behind`；站立抱起禁 `from_above/from_below`；口交禁 `from_behind`。不合法就换成该组允许的机位。
3. **剧情模式最先禁 pov**（⓪ 步，必须在"第一视角去自体动作"之前）：否则 pov 会把 `cowgirl_position`/`straddling` 一起剔掉，骑乘块画面上只剩"背对我们趴着"。
4. **插入组内部不互斥**：`ACT_GROUPS[1]`（missionary/sex/vaginal/…）不再只留一个词——只留姿势词会让画面没有"在插入"。
5. **`guided_penetration` 只属于插入块的第一张**：足交/乳交挂这个词等于"手空出来扶"，跟动作抢手。

### 13.4 男体按段分
- 正戏/事后（sex/after）：`1boy, faceless_male, hetero`。
- 玩法/前戏（play/foreplay）：**仅阴茎档** `penis, disembodied_penis, solo_focus`，并剔掉 `faceless_male / invisible_man / 1boy / hetero`。
- 触手/机械：整块按"无人形"处理（`nonHuman` 判定），连 `penis` 一起剔。
- `invisible_man` **全项目不再使用**：2B 底模对这个词的理解是"多一条腿/鬼影"，用户实测反复穿帮。
- 剧情模式全段禁 `pov`。

### 13.5 验证命令
```
node D:\ComfyUI\_style_test\dry_story.js 12      # 只看词：每块的最终 prompt
node D:\ComfyUI\_style_test\run_all.js           # 12 组全绿
node D:\ComfyUI\_style_test\run_story_ref.js <baseSeed> <n>   # 真机
```

### 13.6 差分不变式（2026-11-14 定型，2026-11-15 修订）
1. 一个块 = 一种动作；块内 BLOCK_POSE 锁体位，条目自带的其它姿势词一律剔掉。
2. 机位按 **2 张一段**（`blockAngKey = 块 + floor(beat/2)`），段内共用一个机位，段间必不重复 —— 机位不许穿插。（2026-11-15 从 3 张改 2 张：3 张一段会让 5 张的块出现"2+3"断裂。）
3. 景别按 `PHASE_PLAN[].beat`；口交块 `noClose`（连阶段偏好里的 `close-up` 也要挡）。
4. 动作条目块内轮换（pickBlockActs），同一块里不再是同一条动作重复 N 次。
5. 衣物只用状态形容词；剧情模式剔所有脱衣动作词。
6. 玩法段用**仅阴茎档**（`penis, disembodied_penis, solo_focus`）且不写 `hetero`；正戏/事后用 `faceless_male`。
7. 剧情模式全段禁 pov。
8. 采样 10 步、cfg 待定；cfg=1 时负向不参与（已知缺陷），所以修正暂时只能落正向。


### 13.7 排片与参考图（2026-11-15 追加）

不变式：
11. **场界只能落在块边界**。`blockPlanOf` 用"整块装场"（`if(inScene > 0 && inScene + c > span)` 才开新场），收尾不足 6 张的小场并进上一场。切在块中间 = 同一个动作拍一半换房间。
12. **参考图默认块锚**（`S.refAnchor === 'block'`）：换块时 `S.storyRef = ''`，块的第一张不挂参考图、块内差分全锚它。逐张接力（`shot`）只在手动选择时使用 —— 链式会累积误差，第 5–6 张开始崩（社区实证见方案文档 §11）。
13. 排片表用 `node _style_test\plan_table.js` 复核（50/100/190 三种数量的块配额与场划分），改动配额或场逻辑后必须跑一次，看场是不是被劈开、有没有 3 张的碎场。

## 14. 重构纪律（2026-11-15 整理轮）

代码改了很多轮，之后再动 `tools\gen_workbench.py` 一律按下面这套走，否则"看着只改了个注释、提示词全变了"这种事一定会再发生。

### 14.1 三把锁

| 锁 | 命令 | 守住什么 |
|---|---|---|
| 生成门禁 | `python tools\gen_workbench.py` | 内联 JS 先过 `node --check`，语法错拒绝写 `webui\workbench.html` |
| 结构金标 | `node _style_test\golden_check.js` | `structure50/190`（排片+块+阶段+beat+场+该块首个预设）、`prompts50/12`（干跑提示词指纹） |
| 全量回归 | `node _style_test\run_all.js` | 12 组：生成/抽取/语法/剧情/节拍/审查/配比/崩脸/男体/批处理仿真/状态机/结构不变量 |

只有"确实要改行为"时才 `node _style_test\golden_check.js --update`，并在当天记录里写清为什么变。纯重构必须四项全 `SAME`。

### 14.2 改代码流程

1. 写一次性补丁 `D:\ComfyUI\_tmp_xxx.py`（`str.replace` + `assert s.count(old)==1`），别用 PowerShell here-string 改中文；
2. `python _tmp_xxx.py` → `python tools\gen_workbench.py` → `python _style_test\extract_wb.py`；
3. `node _style_test\golden_check.js`（四项 SAME）→ `node _style_test\run_all.js`（12 组 PASS）；
4. 补丁脚本用完丢进 `_style_test\old_patches\`，仓库根目录不留 `_tmp_*`。

### 14.3 已知的坑（都是这轮踩的）

- `check_js()` 里 `subprocess.run` 必须显式 `encoding='utf-8', errors='replace'`：Windows 默认 gbk 解 node 的输出，一旦 node 打印非 ASCII 就 `UnicodeDecodeError`，生成被误判成"JS 语法错误"。
- 注释里出现 `---- */` 会被 JS 当成注释结束，把后续整段注释变成代码（TOC 就这么挂过一次）。
- 删声明时别把上面的 `/* … */` 闭合行一起吃掉：`EXPLICIT_SOFT` 那次就是这样整段被注释掉，报 `tierGate is not defined`。
- 测试脚本注释一律 ASCII：`test_core.js` 是混合编码，追加中文必炸；新断言写进 `test_rules.js`。
- 脚本顶层不要写 `process.exit(0)`：会抢在 async IIFE 前把进程杀掉，只打印表头。

### 14.4 这轮删掉/修掉的

- 删死符号：`batchStop`、`PROP_WORDS`、`GARB_CHAIN`、`PROP_GRP`、`pickBlockAct`、`phSeen`、`shotPool`（连带 `dry_story.js`/`run_story_ref.js` 里的注入）。
- 修 preflight 缺花括号：⑤l/⑤n/⑤m/单角色剔多人 原本被嵌在 `nChar<2` 分支里，2 人剧情正戏永不补 `sex`/`vaginal`。
- ⑥ 重名三处 → ⑥a/⑥b/⑥c；`preflight` 顶部加执行顺序表（23 条，按代码真实顺序）。
- `SOCK_ZH` 补 4 个中文 key；过时数字注释校正（角色 2408、duo_male 50、solo_sex 60、wb_outfits 140）。
- 88 个一次性补丁脚本归档到 `_style_test\old_patches\`（91 项）。

### 14.5 重复表合并（2026-11-15 P1 已做）

- **归一化 14 个实现 → 1 个**：全部走模块级 `K`（小写 → 去撇号 → 空白/连字符/点折成下划线）。
  `keyOf` / `sockKey` / `pkB` / `PK` / `lowT` / `normS` / `pk` / preflight 的 `low` 现在都是 `K` 的别名。
  改动动机：`keyOf` 只折空格、`K` 折连字符，`half-closed_eyes` 会存成两个 key。
- **`CUM_W = CUM.concat([...])`**（原表 `facial` 重复两次）。
- **`UNDRESS = SOFT_HOT.slice(0, 21)`**（逐字核对过完全一致）；`HALF_W = HALF_STRICT.concat(['open_clothes'])`。
- **`MALE_POS` 拆成 `MALE_ACT` + `MALE_BODY`**，`MALE_POS` 保留为两者相并的兼容别名。
- 仍未并：`SEX_ACT` ⊂ `PF_SEXISH`（语义不同，保留两份）、`lvOf`/`lvOf2`（`STAGE_PLAN` 已删，排片只剩 `PHASE_PLAN` 一套）。

## 15. 差分与男体（2026-11-15 定稿，改这几处前先读）

### 15.1 差分与男体不变式

统一见 §13.6（这里原来那六条与 §13.6 / 方案文档 §12 三处重复，已删）。贫乳不排乳交见 `multi-turn-连续动作-方案.md` §12.5。

### 15.2 三处必须同步的地方（漏一处就出现"页面 / 干跑 / 真批"三套行为）

- `composeShot` 的块状态：`curBlockActs / curBlockPose / curBlockSub / curBlockNoClose / blockAng`
- `batchRun`（页面）：每张写 `S.sceneBeat / S.scenePhase / S.curBlockCount / S.maleAuto`
- `run_story_ref.js`（真批）+ `dry_story.js`（干跑）：同样三行，且 `preflight` 要拿到 `forceBeat`

### 15.3 `check_js` 与 node 的编码

`tools/gen_workbench.py` 的 `check_js()` 必须 `subprocess.run(..., encoding="utf-8", errors="replace")`，否则 Windows 默认 gbk 解码会让"语法正确"被判成"禁止写入"。

## 16. 机位实现细节（2026-11-15 P3）

> 差分的总规则见 §13.6；本节只留机位 / 景别的实现细节与零频词清单，不重复抄一遍不变式。

**不变式 1**：机位/景别的唯一权威是 `composeShot` 里选出来的 `ang` / `shot`。预设自带的位置全部在 `return` 前剔掉，别让 preset 决定机位。

**不变式 2**：`internal_cumshot` 只在插入类块（`missionary/doggy/ride/stand`）的 `beatIdx2 >= 1` 位置出现，每块最多一张，且强制配 `close-up`。

**不变式 3**：`sub` 带姿势时，应用前必须先剔 `SUB_POSE` 全表，再补本张那条。只剔 `flatSub` 不够 —— preset 的姿势词不在 `flatSub` 里。

**不变式 4**：机位去重先按"机位本身"（`usedAng`），用光了才退回"机位+景别"组合。反过来做的话，换个景别就能复用同一机位，5 张块整块一个视角。

**零频词清单**（加词前必须查 danbooru `post_count`，=0 的永远不加）：`from_front`、`three_quarter_view`、`rear_view`、`wide_angle`、`over_the_shoulder`、`legs_around_waist`、`sitting_on_edge`、`intercrural_sex`、`face_in_pussy`、`legs_on_shoulders`、`bending_over`（应为 `bent_over`）、`half-lidded_eyes`（应为 `half-closed_eyes`）、`after_orgasm`、`flushed`、`suspended`、`cum_on_face`。

- `suspension` 6160 是 BDSM 悬挂，可用；`suspended` 0 频不可用（块内 `sub` 也一律不写）。
- `from_front` post_count = 0，danbooru 根本没有这个 tag —— 不写机位词才等于正面。

## 17. 测跑一致性与过宽规则（2026-11-15 P3）

**坑 1（最贵的一个）**：`dry_story.js` / `run_story_ref.js` 与页面 `batchRun` 的换块分支不同源 —— 前者缺 `S.blockCamUsed = []`，导致机位去重表永久累积，50 张里前 9 张用完所有机位、后面全部退化；runner 还缺 `pickBlockPreset`，跑的是 atoms 拼词而不是场景预设，跟词审看到的不是同一套提示词。修完平均每块机位种类 1.7 → 4.3。

**坑 2**：`VFIX` 里 `when:['leg_lift','standing_sex'] → cut from_behind` 太宽，站立块每次都被换掉背后机位（已删，后入由 `ANG_OK2` 管）。

**坑 3**：剧情分支里 `cut(['pov',...])` 无条件执行，仅阴茎档也被剔掉第一视角（改成 `hasBody` 才剔）。

**坑 4**：`dutch_angle + full_body` 先在 `composeShot` 选机位时预筛，不要"选了再扔"。

**不变式 5**：三处换块分支（页面 / dry / runner）的字段必须一致，改一处必须三处一起改。字段清单见 `提示词与场景-v3.md` §13.10。

## 18 复合层（MOD_DEFS）

### 18.1 不变式

1. **一行只挂一个层。** `assignMods` 用 `taken` 保证不重复挑同一行；渲染侧还有三道剥离。
2. **层词必须在三层都剥一遍**：`composeShot` 入场（无层行）、`MOD` 块开头（剥别层）、
   `preflight` ⑦b/⑦c（收口）。只做一处一定漏 —— 池条目和预设都会把层词带回来。
3. **`hasMod` 是排片期标记，不能跨调用残留。** `blockPlanOf` 开头必须清。
4. **挂层的块不走场景预设。** 预设是整场打包的，会盖掉行的粒度。
5. **层分配必须确定性。** 用 `S.storyBaseSeed + n` 派生 LCG，不许用 `Math.random`。

### 18.2 改层词表前先查频次

阈值照旧：动作/装备词 <5 万标风险、<1 万换掉、=0 永远不用。
本轮三个词域实测几乎全是低到零频，详见《提示词与场景-v3》§14.3。
最容易踩的：`dildo_machine`/`fucking_machine`/`machine_sex` 全 0、
`hypnotized`/`trance` 全 0、`collar` 287k 但语义是时装项圈。

### 18.3 加新层的步骤

1. `MOD_DEFS` 加一条：`{id, rate, tone, look, deny, banPose, allow}`
2. `allow` 白名单要按冲突实测定，别照抄（`collar/leash` 在 handjob/paizuri 里必炸）
3. 抽卡验三项：未挂层污染 0、层串味 0、每块机位 ≥2 种
4. `golden_check.js --update` 重建，连跑两次必须 SAME

---

## 19. 块末收尾 / 固定机位 / 分区排片（2026-11-15 P25–P27）

### 19.1 块末收尾（`FINALE_W`）

每个动作块**最后一张**带结算词，然后接下一块 —— 不是整批结束才结算（用户口径：这样读起来才连贯）。

| 位置 | 要做什么 | 漏了会怎样 |
|---|---|---|
| `blockPlanOf` | 每块最后一行打 `finale:true` | 全批没有收尾图 |
| `preflight` ⑤e | `if(o.forcePhase === 'play' && !o.finale)` 才剔结算词 | 过程行也带 cum |
| `preflight` ⑤f | 有 `finale` 就补 `FINALE_W[block]` | 收尾图没词 |
| 三处调用 | 页面 / `dry_story.js` / `run_story_ref.js` 都传 `finale:` | 命令行跑批 0 收尾（实测踩过） |
| 输出行 | `dry_prompts.json` / `story_run_*.json` 里带 `finale` 字段 | 检查脚本读不到 |

**验收**：`node _style_test\audit_multi.js` 的「收尾缺失」项必须是 0。
检查清单里的结算词要包含 `cum`（不只 `cum_overflow`），否则会把「只补了 cum」误判成缺失。

### 19.2 块级固定机位（`fixedAng`）

只有 3P 在用（三人构图换视角必叠成一团，差分全交给表情）。三处同时钉，少一处就被上游改掉：

1. `composeShot`：覆盖必须放在 `ang` **全部算完之后**（放 `aRaw0` 之前会被 `pickOne` 冲掉）
2. `preflight` 末尾（`rep.kind = k` 之前）：`cut(ANGLES - fixedAng)` + `push(fixedAng)` —— 因为 ⑥a 视角冲突、
   `VFIX`、崩脸三条都会改机位（实测被"贴头动作改七分身/背面"改成 `from_above`）
3. `blockPlanOf`：分区为 `solo/machine/tentacle/yuri/voyeur` 时该块权重归 0

### 19.3 分区排片的两条硬规则

- **无人形分区不排 3P**：这几个分区的整条链路都在剔男体词，`3boys` 会被清掉 → 裸体空镜。
- **`arched_back` 不算姿势**：它是身体曲线不是支撑面。放 `POSE_GRP.bend`（权重 2）会打赢 `lie`（权重 1，含 `on_side`），
  侧入被画成"弯背自慰"（实测 #151）。
- **`side` 块池子只留 `duo_male`**：`solo_sex` 里大量 `dildo` 自慰条目，抽到就不是侧入。

### 19.4 多轮抽卡审计（新工具）

```bash
node _style_test/audit_multi.js          # 4 个 seed × 11 种配置，一次跑完
node _style_test/audit_dump.js <seed> <N> <family> empty|3p|all [duo]   # 单例深挖
```

`audit_multi.js` 检查 12 项：块末收尾、过程行带结算词、无机位、无景别、同张多景别、pov 与背后/内视同框、
3P 机位未锁死、场景锁定、衣物回退、玩法段出现人形男、正戏段无性行为词、块+机位重复率。
**总问题数必须是 0** 才算这一轮过。
