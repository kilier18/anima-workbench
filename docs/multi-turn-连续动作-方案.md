# multi-turn 连续动作 —— 设计方案（交接）

> 状态：**轻量版已落地（2026-11-15）** —— 五阶段/衣物链/锁定/节拍/姿势互斥/参考图/回放全部在 `tools/gen_workbench.py`；42 块设计稿**未进代码**，实际 14 块（含侧入 / 3P / 触手 / 机械），见 §10 与 `提示词与场景-v3.md` §12。
> 目标读者：下一个接手工作台的人
> 相关文档：`提示词与场景-v3.md`（池结构）、`workbench-维护手册.md`（工作台架构/不变式）

---

## 1. 要解决什么

现在点"批量 10 张"，得到的是 **10 个互不相干的片段**：

- 每张独立抽池、抽场景、抽地点、抽机位、抽光照
- 第 1 张在便利店，第 2 张在卧室，中间没有因果
- 第 1 张穿外套，第 2 张光着，没交代什么时候脱的

**multi-turn 要的是：一批图 = 一场戏的 N 个镜头。**

同一个角色、同一个地点，动作按顺序推进，服装状态跟着递减，第 N 张知道第 N-1 张脱了什么。

---

## 2. 为什么现在做不到

不是缺数据，是缺三个维度：

| 缺什么 | 现状 | 后果 |
|---|---|---|
| **阶段（phase）** | 37 个池是平级的抽屉，没有"这是第几步"的概念 | 抽到"事后"条目也可能排在第 1 张 |
| **继承（state）** | `preflight()` 每次从零开始，不读上一张的结果 | 服装状态每张独立，接不上 |
| **锁定（lock）** | 地点/机位/光照每张重抽 | 场景乱跳，不成戏 |

`after` 池那 46 条"事后"条目现在只能靠运气出现，出现了也跟前面哪张都对不上。

---

## 8. 当前实现（2026-11-14 收口，以这一节为准）

第 7 节记录的是"轻量版 + 效果强化"的第一轮落地。跑过 50 张真实批量、并经过几轮挑错之后，
调度逻辑换成了**区块制差分**，衣物从"脱衣动作"改回"衣着状态形容词"。下面这一张表才是现在的实际行为，
第 7 节里冲突的条目（例如"服装锁自动挑衣服""段内锁机位"）已经作废。

### 8.1 排片：块 → 场 → 张

- 一批图先按 **块（block）** 分份额，一个块 = 一种动作（前戏 / 口交 / 乳交 / 手交 / 足交 / 正面位 / 后入 / 骑乘 / 站立抱起 / 触手 / 机械 / 事后）。
  `BLOCK_DEFS[].w` 是权重，`blockPlanOf(n)` 按最大余数分配，凑不满就从最大块削、跳过事后块。
- 一个块内部再切 **场（scene）**：每 25 张左右换一场，换场时重抽地点、光照、天气与场记，并清掉脱衣状态与上一张的机位/景别记忆。
- 一场内部按阶段（setup → foreplay → play → sex → after）走，一块的 phase/garb 由块定义固定。
- 张数少时按 `BLOCK_DEFS` 顺序取前 N 个块；张数多时同块重复出现即"再来一轮差分"。

### 8.2 差分：只换表情/景别/细节，机位与体位锁死

用户口径（2026-11-14）：「写差分的时候至少机位和体位应该统一，哪怕跑出来不是和提示词一样的体位，至少也能跑出来差分效果」，
以及「同一个姿势差分 3~4 张图之后再换相机位置」。

- **体位锁死**：`BLOCK_POSE[block]` 给出这一块允许的姿势词（口交跪、乳交仰躺、手交/足交坐、正面位 on_back+missionary、
  后入 sex_from_behind+all_fours、骑乘 cowgirl_position、站立 standing_sex+carrying、事后 sitting）。条目自带的其它姿势词全部剔掉、
  缺锚点就补上 —— 这样同块 N 张画的是同一个体位。
- **机位按 2 张一段**：`S.blockAngKey = 块 + floor(beat/2)`，同一段 2 张共用一个机位，下一段换（必不与上一段重复）。
  即"同一个姿势连拍 2 张 → 换机位"，机位不穿插。
- **景别按节拍**：`PHASE_PLAN[].beat`（段内第几张给哪个景别），撞上一张就顺延；口交块 `noClose`，整块不给特写（特写+口交是崩脸重灾区）。
- **动作条目块内轮换**：`pickBlockActs(block, scene, count)` 用 `baseSeed` 洗牌后取 count 条互不相同的条目，
  第 i 张用第 i 条 —— 同块不再是同一条动作重复 N 次（这是"口交同质化严重"的修法）。

### 8.3 衣物 = 状态形容词

- garb 状态机：full / open / partial / none；partial 用 `partially_clothed` 状态词（不是 `undressing` 动作词），open 用 `open_clothes`，none 用 `completely_nude`。
- preflight 在剧情模式**先剔所有脱衣动作词**（undressing / clothes_lift / skirt_lift / clothes_pull / bra_lift / panty_pull …），
  fix 文案「剧情·脱衣动作改状态」；理由：脱衣动作词进了画面就是"双手在脱衣"，跟手交/乳交同框立刻多出一只手。
- 状态词互斥：open/partial 剔 `clothed`；none 剔 `clothed / partially_clothed / open_clothes` 与泳装类。
- **不再自动挑衣服**：剧情模式只认"角色卡自带的 + 你手选的"；要换衣服在服饰面板手选后再开批量。

### 8.4 人与地点

- 男体按段：sex/after 用 `1boy, faceless_male, hetero`（透明男在 anima 上会被画成"没有人"，正戏必须看得见身体）；
  玩法段（口/乳/手/足）用 `invisible_man`，并剔掉 `faceless_male/1boy/hetero`（`hetero` 会把男体拉进来）。
- 剧情模式全段禁 `pov`（第一视角会裁掉身体、还要多一双手）；pov 只在单图抽卡里保留。
- 地点：`S.storyLock` 整批（整场）锁定 place/light/weather；`PLACE_GRP` 19 组 + 家具跟随（`FURN`），锁了室内不会冒出便利店/小巷；
  锁定的地点组之外的词在返回前统一剔除。

### 8.5 进程词（时间轴）

`imminent_penetration`（还没进去）/ `guided_penetration`（扶着引导，只给插入体位块的第一张）/ `deep_penetration` / `afterglow`，
已插入（sex/vaginal/sex_from_behind/creampie）就剔掉"即将插入"。这三个词替代"每个动作写前中后三拍"。

### 8.6 词面卫生

- 撇号词统一去撇号（`hand_on_another's_waist` → `hand_on_anothers_waist`），否则 CLIP 把它切成碎片、动作丢一半。
- 归一化统一：`K()` / `low()` / `sockKey()` 都把连字符折成下划线比较，避免 `face-to-face` 删不掉 `face_to_face`。
- 采样固定 10 步 / cfg 1.0（用户定的画风档）；注意 cfg=1 时**负向提示词基本不参与**，所以所有修正都落在正向词面，不靠负向兜。

### 8.7 现在的测试与跑批

```
node _style_test/run_all.js          # 12 组全绿（生成/抽取/语法 + 9 个断言集）
node _style_test/dry_story.js 12     # 只算词不出图，逐张看最终 prompt
node _style_test/run_story_ref.js <baseSeed> <n> [ref] <char> [outfit|-] [family]
python tools/review_sheet.py --only <baseSeed>_<n>   # 拼审阅板
```

### 已知边界
- 角色漂移只在**两个以上不同角色卡（LoRA）同框**时出现；单人原作 tag（`hakurei_reimu` 那套）十张脸是稳的，所以参考图单人默认关，省 10s/张。
- 多角色段（yuri/triple）目前只锁"两个女孩"的池，不锁"两张不同的脸"——真要一张图里两个不同角色卡，得靠参考图 + 分段：先各出一张单人定妆，再拿那两张做双参考。
- 完整版序列池（phase→beat 子序列）仍未做，等轻量版跑够批再看。


## 9. 提示词来源改为「用户场景库」（2026-11-15）

### 9.1 为什么换
atoms 池是动作碎片（handjob, penis, fingers），拼出来的句子缺主谓，2B 模型只能猜；用户库 wb_scenes.json 的 963 条是**整场戏**，每条都带 stage 0..5、cat、group，并且是跑过验证的。

### 9.2 现在的取词路径
`
块（14 个） --预设优先--> 场景库一条（同块 N 张共用，这就是差分）
             \--兜底--> atoms 池（库里没对应动作时）
`
- BLOCK_STAGE：块 → 库里 stage（foreplay 1 / 口交·乳·手·足 2 / 四个体位 2 / 事后 5）。
- BLOCK_SIG：块 → 允许的动作动词；cat 命中块中文名也算（库里 手交/后入 这类分类直接对上）。
- presetPool(b, scene) 过滤：tier r18 剔 sfw/near；单人剔 2girls/yuri/futanari/mmf…；插入类必须有 penetrated 词（sex/vaginal/sex_from_behind/… 任一）；handjob 块只认 handjob；oral 只认 fellatio/licking_penis。
- pickBlockPreset(b, scene)：批内 id 去重，种子 = storyBaseSeed + scene*7919 + 块名长度*131。
- 预设自带的地点/光照/裸露/机位词由 stripSceneTags() 一律剥掉 —— 地点光照只听本场锁定、裸露只听衣物链、壁纸式机位不进来。

### 9.3 三条兜底门禁（都写在 preflight，真机问题驱动）
- ⑤l 正戏：有体位词却没有 sex/vaginal → 补齐（后入画成素股的根因）。
- ⑤m 前戏：一个前戏动词都没有 → 补 groping（预设动作词被脱衣改状态剥空时）。
- ⑤n 手/足/乳：画面里没有 penis/tentacles → 补 penis（否则手在空气里搓）。

### 9.4 小众族现在真的会被抽到

nicheSlot()：前戏/后入/骑乘/事后里每 3 场留 1 个位置给 催眠/触手 分类整条预设（该块整体改成那场戏，不假装是后入的差分）。互动类块（口交/乳交/手交/足交/正面位）不吃小众族 —— 那些必须有人在。

### 9.5 核对表工具（本轮交付）
`
node _style_test\check_map.js 50
`
输出每条最终提示词实际在演什么与排片意图的比对表；✓ 正常、✗ 缺 X、△ 串到 X。当前 50 张：**50/50 ✓**（含 7 条小众族）。


## 10. 不同数量的排片表（50 / 100 / 190）

排片由 `blockPlanOf(n)` 算：先按 14 个块的权重分配（6/6/9/9/8/13/13/9/9/9/6/6/4/6，前戏在 n<100 时减半），再用最大余数补齐；然后"整块装场" —— 一场 = 一个地点里连续几块戏，每场目标 25 张，**场界永远落在块边界上**（切在块中间 = 同一动作中途换房间）。

| 块 | 权重 | 190 张实测 | 备注 |
|---|---:|---:|---|
| 前戏 foreplay | 6 | 10 | n<100 时折半到 3 |
| 口交 oral | 6 | 10 | |
| 乳交 paizuri | 9 | 15 | |
| 手交 handjob | 9 | 15 | |
| 足交 footjob | 8 | 14 | |
| 正面位 missionary | 13 | 22 | |
| 后入 doggy | 13 | 22 | |
| 骑乘 ride | 9 | 15 | |
| 站立抱起 stand | 9 | 15 | |
| 侧入 side | 9 | 15 | 2026-11-15 新增 |
| 3P threesome | 6 | 10 | 机位钉死 from_side |
| 触手 tentacle | 6 | 10 | |
| 机械 machine | 4 | 7 | |
| 事后 after | 6 | 10 | |
| **合计** | | **190** | |

分区为 `solo/machine/tentacle/yuri/voyeur` 时 3P 块权重归 0（这几个分区整条链路在剔男体词）。

**每块最后一张带结算词**（`FINALE_W`，见 §12.1），然后接下一块 —— 一批图读起来是一段段做完，不是最后统一收尾。

- 50 张 → **2 场**（25 / 25 张）
- 100 张 → **5 场**（21 / 17 / 14 / 23 / 25 张）
- 190 张 → **10 场**（24 / 17 / 17 / 16 / 25 / 25 / 17 / 17 / 20 / 12 张）

每个块内部：一条场景库预设（动作词整条不动）+ N 张差分（机位每 2 张换一次、景别按块节拍、表情档随段位递增）。所以你拿到的是"12 个动作块 × 每块 1–25 张同动作不同机位"，不是 190 张互不相干的图。

## 11. 参考图锚点（社区结论 + 现在的做法）

### 11.1 社区怎么说
- 逐张接力（拿上一张当参考）会**累积误差**：学术上叫 exposure bias / drifting，指"视觉质量随时间逐步劣化"，缓解手段是固定记忆锚点而不是回灌上一帧（[Frame Context Packing, arXiv 2504.12626](https://arxiv.org/html/2504.12626v3)）。
- 实操侧的观察和你的体感一致：前 2–3 张稳，**到第 5–6 张开始变**（[r/StableDiffusion](https://www.reddit.com/r/StableDiffusion/comments/1rjuyn9/why_do_ai_images_stay_consistent_for_23/)）；一条 52 帧的系列里，角色在 38 帧上漂了，作者复盘的第一条就是"我拿一张场景图当锚点，等于把场景也焊进角色"（[Little Might](https://www.littlemight.com/how-to-stop-your-ai-images-from-drifting-across-a-series/)）。
- 主流做法是**锚点延展**：一张基准图当锚，其它张都从它长出来，而不是链式互相参考（[星流九宫格玩法](https://news.qq.com/rain/a/20260122A05PAK00)）。
- 参考图权重与分工：角色参考 0.7–0.9、构图参考 0.5–0.7，参考图要干净背景，否则背景元素会被当角色特征（[双参考图实战](https://blog.csdn.net/weixin_29090677/article/details/165667897)）。

### 11.2 现在的实现
- 默认**关**：单人角色 tag（原作 LoRA 已经锁长相）不需要参考图，链式参考只会把上一张的崩坏传下去。
- 打开后有两个锚点模式：
  - `锚本块第一张`（默认）：每个块的第一张**不挂**参考图，块内差分全部锚这一张；换块就断链。所以一条链最长 = 一块的张数，误差不会跨动作累积。
  - `锚上一张（链式）`：旧行为，只在你想强接续同一场景的连续动作时手动选。
- 多角色卡（≥2 个不同 LoRA 同框）时才自动建议打开 —— 那是真的会串脸的场景。

## 12. 核心逻辑第二轮修订（2026-11-15，50 张实拍反馈驱动）

这一节是"透过现象看本质"的那一刀：用户 m03775 逐条指出 50 张里的错误，逐条追下去基本都不是提示词写法问题，是调度层的四条逻辑没立住。

### 12.1 差分 = 子动作 × 机位槽（不再靠堆词）

- 每个互动块带一张 `sub` 子动作表（`BLOCK_DEFS[].sub`），同一个块内逐张换一条：
  - 口交：`licking_penis + tongue_out` / `fellatio` / `licking_penis + saliva` / `fellatio + looking_up`
  - 乳交：`breasts` / `breast_press` / `nipples`
  - 手交：`penis` / `testicles` / `precum`
  - 足交：`soles` / `toes` / `two-footed_footjob`
  - 站立抱起：`carrying + legs_around_waist` / `suspended` / `carrying + sex`
- composeShot 在"体位锁"之后先剔掉该块所有变体词、再压入本张那一条 —— 否则"舔 + 含"同框互相打架，模型自己挑一个，看起来就是没差分。
- 机位槽 `Math.floor(beat / 2)`：同姿势连拍 2 张共用一个机位再换，比每张换稳、比一个块不换有看点。
- 口交块 `noClose`：不给特写（用户口径：特写小窗最容易崩）。

### 12.2 体位锁优先于互斥表

`⑥c 姿势互斥` 原来按"命中数×权重"投票，会把块里已经锁好的 `kneeling`（口交）投成 `straddling`（骑乘）。现在剧情模式下：块内 `S.curBlockPose` 有值时，互斥表只做"剔掉不在锁里的姿势词"，不做投票。

### 12.3 男体三档（用户拍板）

| 段 | 档 | 词 |
|---|---|---|
| 前戏 / 玩法（口·乳·手·足） | `penis` 仅阴茎 | `disembodied_penis` + `solo_focus`，剔 `faceless_male / invisible_man / 1boy / 2boys / hetero` |
| 正戏 / 事后 | `faceless` 无脸男 | `1boy + faceless_male + hetero`，剔 `invisible_man / disembodied_penis` |
| 触手 / 机械（不论段） | 无人形 | 剔 `1boy / 2boys / faceless_male / hetero / invisible_man / disembodied_penis` |

`S.maleAuto` 由 batchRun / runner / dry_story 按阶段写入，`maleMode()` 优先读它；单图抽卡路径不写，行为不变。

### 12.4 结算词与事后痕迹

- 玩法段（口/乳/手/足）与正戏前几拍不许出现 `cumdrip / cum_in_pussy / creampie / cum_overflow / after_sex / afterglow` 等（列表本轮补齐 `cumdrip` 一族）。
- 正戏只在**本块最后一张**放 `cum_in_pussy`（`forceBeat < curBlockCount-1` 时剔）。
- 事后段：`cum_in_pussy / creampie / sex / vaginal / 体位词` 全部换成 `cum_overflow + after_sex`，并且不给 `from_behind`。

### 12.5 地点与机位的两条补丁

- `sceneWordSets()` 的 `S.__PT` 补了 19 个地点词（`public_toilet / elevator / curtains / headboard / locker_room / shower_room / kitchen / living_room / bedroom / classroom / office / alley / street / convenience_store / park / forest / shrine / rooftop / indoors`）—— 预设自带的地点词若不在集合里，会把本场锁定的"森林"顶掉。
- `from_behind` 时剔 `looking_at_viewer / looking_back / looking_over_shoulder`：后脑勺长脸就是这么来的。
- 贫乳（`S.bust === 'flat'`）时整块 `paizuri` 改排 `handjob`：乳交语义自带大胸先验，提示词压不住。

### 12.6 小众族（触手 / 催眠 / 机械）

`nicheSlot` 只允许在"能独立成戏"的块里插：`foreplay / doggy / ride / after`，周期 `scene % 3 === 2`。互动类块（口·乳·手·足）和正面位永不接小众族 —— 否则触手会跟"扶着插进去"打架。50 张里现在稳定出现 2 个整块（约 11 张）。

### 12.7 验证

- 干跑看词：`node _style_test\dry_story.js 50`（每张打印块/第几张/阶段/衣物/景别/预设/最终词/fixes）。
- 反读动作：`node _style_test\check_map.js 50` → 按动词签名判"这条提示词实际在演什么"，输出 `D:\ComfyUI\docs\核对表-50张.md`。
- 金标：`node _style_test\golden_check.js`（本轮改行为，`--update` 已重建：structure50 `d408ecc4981f1889`、structure190 `7201d24d18c1db9e`、prompts50 `1564e4a58a2dea6e`、prompts12 `030fc81d50a0f359`）。
- 全量：`node _style_test\run_all.js` 12 组全绿。

---
