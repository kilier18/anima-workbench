# Anima Workbench · 本地插画工作台

一套跑在自己电脑上的 **提示词编排 + 批量出图** 工作台。后端是一个轻量 Python 服务，前端是一张单页 HTML，出图交给本机的 ComfyUI。

不是在线服务，不上传任何数据，所有素材、模型、生成结果都留在本机。

---

## 它解决什么问题

直接手写提示词画图，有三个反复出现的麻烦：

1. **词穷** —— 每次都要重新拼动作、场景、光线、构图。
2. **不一致** —— 一次出十张，人物数量、性别、构图互相打架。
3. **不可复现** —— 上次那张好看的配方没存下来。

这个工坊把这三件事拆开处理：

| 模块 | 作用 |
|---|---|
| **动作块** | 1529 条动作条目归进 **14 个块**（前戏 / 口交 / 乳交 / 手交 / 足交 / 正面位 / 后入 / 骑乘 / 站立抱起 / 侧入 / 3P / 触手 / 机械 / 事后），每块带 3–5 条子动作与机位差分 |
| **复合层** | 催眠 / 调教不占块位，是可叠加的修饰层（催眠口交、调教后入），约 12% 的行随机挂上 |
| **场景库** | 960+ 条现成场景，一键套用（地点 / 光线 / 天气 / 构图 / 情绪全套） |
| **角色库** | 2400+ 角色条目，带作品分类、搜索、缩略图；含「AI 拟人（大模型娘）」18 条双预设 |
| **画风库** | 114 个画风 LoRA（画师包 / 东方画师 / AI 拟人），点卡即挂，自带触发词、强度与缩略图 |
| **出图前审查** | 提交前跑一遍一致性检查，自动修人物数量、性别配置、视角与机位冲突、衣物状态、表情堆叠 |
| **批量出图** | 一次排 N 张（50 / 100 / 190 都有排片表），逐张过审、逐张记录，出问题能定位到是哪一条 |
| **出图目录** | 页面里直接改落盘位置，出图自动按 `序号_块_衣物_机位_原名` 命名 |

## 技术栈

```
浏览器  ──HTTP──▶  assistant.py (FastAPI/标准库, :8190)
                        │
                        ├─ 静态页 workbench.html（单文件，无构建步骤）
                        ├─ 数据 webui/data/*.json（纯 JSON，可直接改）
                        └─ 转发 ──▶ ComfyUI (:8188)
                                      │
                                      ├─ Anima 2B UNet（动漫向扩散模型）
                                      ├─ Qwen3-0.6B 文本编码器
                                      ├─ Qwen-Image VAE
                                      └─ 画风 LoRA 库（turbo 1.0 + 画风包选挂）
```

- 后端只依赖 Python 标准库 + 可选 Pillow，不装框架也能跑。
- 前端零依赖、零构建：`webui/workbench.html` 就是全部，改完刷新即可。
- 数据全在 `webui/data/`，改 JSON 就改行为，不用碰代码。

## 目录结构

```
ComfyUI/
├─ ComfyUI控制台.ps1          # 图形控制台：启动/停止引擎、打开工坊、打开出图目录
├─ extra_model_paths.yaml     # 模型路径重定向（部署时按自己路径改）
├─ _setup/
│   ├─ start_engine.cmd       # 拉起 ComfyUI
│   ├─ start_assistant.cmd    # 拉起工坊后端
│   ├─ start_ollama.cmd       # 可选：本地 LLM（扩写用）
│   └─ get_outdir.py          # 读配置，输出当前出图目录
├─ webui/
│   ├─ assistant.py           # 后端（路由 / 任务队列 / ComfyUI 转发）
│   ├─ planner.py             # 自然语言 → 提示词结构化（可选，需本地 LLM）
│   ├─ workbench.html         # 前端单页
│   ├─ tag_zh.json            # 标签中文对照
│   └─ data/                  # 全部数据
│       ├─ wb_atoms.json      # 动作池（核心）
│       ├─ wb_scenes.json     # 场景库
│       ├─ wb_chars.json      # 角色库
│       ├─ wb_tags.json       # 标签分类库
│       ├─ wb_presets.json    # 预设
│       ├─ wb_pools.json      # 池元数据
│       ├─ wb_outfits.json    # 服饰
│       ├─ wb_zh.json         # 中文词表
│       └─ anima_styles.json  # 画风库索引（lora / 触发词 / 强度 / 分组）
├─ webui/static/style_thumbs/ # 画风卡缩略图（固定角色半身）
├─ tools/
│   ├─ build_atoms.py         # 生成 wb_atoms.json
│   ├─ gen_workbench.py       # 生成 workbench.html
│   ├─ health_check.py        # 数据体检
│   ├─ comfy_proxy.py         # 轻量代理（可选）
│   └─ atoms_*.py             # 各池原始词条（改动作库改这里）
├─ _style_test/                # 回归测试与抽卡审计（node 脚本，零依赖）
│   ├─ run_all.js              # 12 组回归
│   ├─ audit_multi.js          # 44 轮抽卡审计（4 seed × 11 配置）
│   ├─ dry_story.js            # 只抽卡不出图，打印每张最终提示词
│   └─ run_story_ref.js        # 命令行跑真图并复制到指定目录
└─ docs/                       # 四份手册 + 变更记录
```

## 快速开始

**从零部署请直接看 [DEPLOY.md](DEPLOY.md)**，那里写了 ComfyUI、模型、节点的完整安装顺序和校验命令。

最快的方式是双击仓库根目录的 `install.cmd`（7 步向导，可 `install.cmd 3` 单独重跑某一步），
它会自检环境、装好 ComfyUI、建模型目录、下模型、装节点、装工作台并做冒烟验证。

装完后随时可以校验本地文件和仓库是否一致：

```bat
python tools\verify_repo.py            :: 逐文件 sha256 比对
python tools\verify_repo.py --remote   :: 再比一次 HEAD vs origin/main
python tools\verify_repo.py --quiet    :: 只打结论
```

已经装好 ComfyUI + Anima 的话，最短路径是：

```bat
:: 1. 克隆到 D:\ComfyUI
git clone <repo> D:\ComfyUI

:: 2. 改 _setup\start_engine.cmd 和 start_assistant.cmd 里的 ROOT 路径

:: 3. 启动引擎
_setup\start_engine.cmd

:: 4. 另开一个窗口启动工坊
_setup\start_assistant.cmd

:: 5. 浏览器打开
start http://127.0.0.1:8190
```

也可以直接双击 `ComfyUI控制台.ps1` 用图形界面起。

## 核心概念：动作块

`wb_atoms.json` 里 1529 条动作条目，按「内容分级 × 人物关系」切成 37 个池；批量出图时**不直接抽池**，而是先排「块」。

**14 个块**（一张图属于哪个块，由排片阶段决定）：

| 块 | 段 | 张数占比（190 张） |
|---|---|---|
| 前戏 / 事后 | 准备 / 收尾 | 10 / 10 |
| 口交 / 乳交 / 手交 / 足交 | 玩法 | 10 / 15 / 15 / 14 |
| 正面位 / 后入 / 骑乘 / 站立抱起 / 侧入 / 3P | 正戏 | 22 / 22 / 15 / 15 / 15 / 10 |
| 触手 / 机械 | 正戏（非人形） | 10 / 7 |

块内再做三件事产生差分，避免"同一动作连拍"：

1. **子动作**：每块 3–5 条（口交有舔 / 含 / 边乳交边舔），块内不放回抽
2. **机位**：一张一换，块内不重复；无机位可选的块按 `ANG_OK2` 白名单挑
3. **景别**：每 3 张换一次（全身 / 七分身 / 上半身）

每块最后一张自动落**结算词**（口交 `cum_in_mouth`、正面位 `creampie`…），过程行禁止结算词 —— 这样一批图读起来像"一场戏"，而不是十条互不相干的片段。

**复合层**（催眠 / 调教）不占块位，随机叠在约 12% 的行上，各自带要剔的男体词与物理冲突姿势（"绑住手腕还抱起"会被拒）。

改动作库的流程：

```bat
:: 改 tools/atoms_solo.py / atoms_duo.py / atoms_ext.py
python tools/build_atoms.py        :: 重新生成 wb_atoms.json
python tools/health_check.py       :: 体检：缺词、无核心、同义重复
python tools/gen_workbench.py      :: 重新生成 workbench.html
node _style_test/run_all.js        :: 12 组回归（语法 / 分段 / 审查 / 仿真）
```

## 画风库

`webui/data/anima_styles.json` 是画风 LoRA 的索引表，页面「画风」一栏就是它的渲染结果。一张卡 = 一个 LoRA 包：

| 字段 | 含义 |
|---|---|
| `lora` | 相对 `models/loras/` 的路径，必须带目录前缀（如 `Anima\packs\pako.safetensors`） |
| `trig` | 触发词，点卡时自动写进正向框；多词触发词用逗号分隔 |
| `strength` | LoRA 强度，缺省 1.0 |
| `group` | 分组：画师包 / 东方画师 / 桶外-知名画师 / AI 拟人（大模型娘） |

基座固定 `turbo 1.0`，选中画风包时叠加；再点同一张卡即取消，只留 turbo。

加一个新画风：LoRA 放进 `models/loras/`，`anima_styles.json` 追加一条（`id` 唯一、`on_disk: true`），刷新页面即可。缩略图可选，放 `webui/static/style_thumbs/<id>.jpg`。

## 内容分级

工坊内置三档分级开关，数据层就有对应的池隔离，不是靠提示词里加一句"不要"来控制：

| 档位 | 说明 |
|---|---|
| SFW | 日常、生活感，无性暗示 |
| Suggestive | 暧昧、挑逗，不含性行为 |
| Explicit | 成人向 |

**任何公开场合的使用、分发、截图，请自行确认符合所在地法律与平台规则。** 模型与 LoRA 各有自己的许可证，商用前请逐个确认。

## 数据来源与致谢

- 标签、角色、画师词条来自 [Danbooru](https://danbooru.donmai.us/) 公开标签体系
- 底模：[Anima](https://huggingface.co/circlestone-labs/Anima)（Cosmos-Predict2 架构，动漫向）
- 推理：[ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- 自定义节点：ComfyUI-Manager、Impact-Pack、Impact-Subpack、GGUF、IPAdapter_plus、
  [Anima-NAG](https://github.com/hybskgks28275/ComfyUI-Anima-NAG)（cfg=1 下让负向词真正生效）、
  ComfyUI-Anima-Ref-Adapter（角色一致性参考图）

## 许可

代码部分 MIT。`webui/data/` 下的标签与角色数据遵循其原始来源的条款，请勿将其当作自有资产再分发。
