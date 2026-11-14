# multi-turn 连续动作 —— 设计方案（交接）

> 状态：**构想，未实现**
> 目标读者：下一个接手工作台的人
> 相关文档：`提示词与场景-v3.md`（池结构）、`Anima画风LoRA-交接手册.md`（工作台架构）

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

## 3. 轻量版设计（推荐先做这个）

**不写新数据，只加一层编排。** 约一天工作量。

### 3.1 五个阶段

```js
const PHASE_PLAN = [
  { id:'setup',    zh:'准备',  pools:['duo_sfw','duo_daily'],                  garb:'full'    },
  { id:'foreplay', zh:'前戏',  pools:['foreplay_flirt','foreplay_sex'],        garb:'open'    },
  { id:'play',     zh:'玩法',  pools:['oral_sex','paizuri_sex','handjob_sex','footjob_sex'], garb:'partial' },
  { id:'sex',      zh:'正戏',  pools:['duo_male'],                             garb:'none'    },
  { id:'after',    zh:'事后',  pools:['after'],                               garb:'partial' },
];
```

- 每段固定从 `pools` 里抽，**不再走 `poolPlan()` 的随机决策**
- 段内可以抽多条（比如 10 张 = 准备 2 + 前戏 2 + 玩法 3 + 正戏 2 + 事后 1）
- `garb` 决定这一段的衣物状态，插入对应 `USTATE` 词

### 3.2 状态机（衣物递减）

```js
const GARB_CHAIN = {
  full:    [],                          // 全套
  open:    ['open_clothes'],            // 敞开
  partial: ['undressing','skirt_lift'], // 半脱
  none:    ['completely_nude'],         // 全裸
  // 事后回 partial
};
```

关键点：**`garb` 是强制项，不是建议**。第 3 张不论抽到什么条目，都要带 `undressing`，否则模型会自己把衣服穿回去。

### 3.3 锁定项

一批图里这三样**只在第 1 张抽一次，之后全部复用**：

- `S.chars`（角色，含角色 LoRA 选择）
- `place` / `light`（地点、光照）
- `angle`（机位，可以按阶段做小幅变化：前戏中景、正戏特写、事后远景）

改动位置：`batchRun()` 里现在每轮都调 `applyScene()`，story 模式要改成"第 1 轮抽完存进 `S.storyLock`，后续轮只做动作替换"。

### 3.4 seed 策略

```
baseSeed = 用户给的 seed（或随机）
第 i 张 seed = baseSeed + i * 1000
```

同 base 派生能保持底色/画风接近，又给每张留变化空间。不要用同一个 seed，否则动作变了构图也跟着僵。

### 3.5 实现清单

| 文件 | 函数 | 改什么 |
|---|---|---|
| `tools/gen_workbench.py` | 新增 `PHASE_PLAN` / `GARB_CHAIN` 常量 | 放 `POOL_W` 旁边，测试要读 |
| 同上 | `poolPlan(tier, nChar, scene)` | 加第 4 参数 `phase`，命中就返回 `{main:[...], extra:[]}` 短路 |
| 同上 | `composeShot()` | 读 `S.storyPhase`，从 `PHASE_PLAN[phase].pools` 取 |
| 同上 | `batchRun()` | 加 `S.storyMode` 分支：第 1 轮锁定角色/地点/机位，后续轮跳过 `applyScene()` |
| 同上 | `preflight()` | 加 `forceGarb` 参数，段位要求的衣物词强制插入 |
| `webui/workbench.html` | 批量区 | 加开关「连续剧情（story mode）」+ 段长配置 |
| `_style_test/test_plan.js` | — | 加断言：story 模式下 10 张的段位分布符合配置 |

### 3.6 验收标准

跑一批 10 张，人工看三点：

1. **地点不跳**——10 张全在同一个空间
2. **衣服只减不增**——除非是事后"披回外套"那类条目
3. **动作有先后**——不会出现第 2 张已经在正戏、第 5 张又回到前戏

---

## 4. 完整版构想（暂不做）

### 4.1 序列池

新建 `wb_sequences.json`，每条是一个有序动作链：

```json
{
  "id": "wall_pin_chain",
  "zh": "抵在墙上→转过来→按回去→抱起→放下",
  "phaseSpan": ["foreplay", "sex"],
  "steps": [
    {"zh": "把她抵在玄关墙上",   "tags": ["against_wall","standing","looking_at_viewer"], "garb": "full",    "angle": "medium"},
    {"zh": "转过来面对他",       "tags": ["face_to_face","standing","eye_contact"],      "garb": "open",    "angle": "medium"},
    {"zh": "重新按回墙上",       "tags": ["against_wall","one_leg_up","moaning"],       "garb": "partial", "angle": "close"},
    {"zh": "抱起来",             "tags": ["carrying","standing","arms_around_neck"],   "garb": "partial", "angle": "wide"},
    {"zh": "放到沙发上",         "tags": ["lying","on_back","spread_legs"],            "garb": "none",    "angle": "wide"}
  ]
}
```

抽一条链就等于买下整场戏，比轻量版的"按段抽"连贯得多。

**注意**：`carrying` / `suspended` 这类在 `NO_POSE` 黑名单里（用户明确说过复杂构图出图差），所以完整版的链要避开悬空动作，或只允许"抱起后立刻放下"这种有支撑面的写法。

### 4.2 状态机升级

轻量版是"段位决定衣物"，完整版要"步进累积"：第 4 步脱了什么，第 5 步要知道。实现上给每张图存一个 `worn: Set`，每步做增删。

### 4.3 最大风险：角色漂移

实测：同一角色连跑 10 张，**第 6–8 张开始脸会变**（LoRA 权重 + seed 变化的叠加漂移）。

三个兜底手段，按成本排：

1. **固定 seed 派生 + 同 prompt 前缀**（免费，能压到第 6 张）
2. **Ref Adapter 拿第 1 张做参考**（插件已在 `ComfyUI_windows_portable/ComfyUI/custom_nodes/ComfyUI-Anima-Ref-Adapter`，节点 `AnimaRefAdapter`，turbo 下 `cfg1 / 10 步 / ref_guidance 1`，每张多约 10 秒）
3. **IPAdapter**（`custom_nodes/IPAdapter_plus` 已装，但对 Anima 的兼容性没验过）

推荐第 2 条：Ref Adapter 官方文档明写"identity transfers much better than style"，正好是保人不保画风的需求。

---

## 5. 建议的执行顺序

1. 先做轻量版的 **3.1 + 3.2 + 3.3**（阶段 + 衣物链 + 锁定），不做 UI，用命令行参数跑一批看效果
2. 效果认可再加 UI 开关（3.5 最后两行）
3. 再决定要不要上完整版序列池
4. 如果漂移明显，接 Ref Adapter

**不要一上来就写序列池**——轻量版跑一批就知道"戏感"够不够，不够再加数据。

---

## 6. 参考：现有可复用的东西

| 需要的东西 | 已有实现 | 位置 |
|---|---|---|
| 池抽选 | `composeShot()` / `poolItems()` | `tools/gen_workbench.py` |
| 池权重 | `POOL_W` | 同上，模块级常量 |
| 衣物状态词表 | `USTATE` / `CLOTHED_KEEP` / `FULLGARB` / `GARB_KEEP` | 同上 |
| 复杂构图黑名单 | `NO_POSE` | 同上 |
| 男体补全 | `preflight()` 的 `m===2` 分支 + `PF_MALE` | 同上 |
| 批量入口 | `batchRun()` | 同上 |
| 测试脚手架 | `test_plan.js`（`vm.runInContext` 直接调内部函数） | `D:\ComfyUI\_style_test\` |
