# 变更记录 · Changelog

按时间倒序。只记录**功能与技术决策**，不含具体内容词条。
完整开发流水（含逐条排查过程）保留在本地 `docs/历史与回退-v3.md`，不进仓库。

---

### 场景池：玩法拆分与扩库（2026-11-14 下午）

池数 **27 → 37**，条目 **1308 → 1529**。生成链从"直接改 json"改为三层脚本固化
（`build_atoms.py` → `atoms_extra.py` → `atoms_extra2.py`），重跑构建不再冲掉手改。

**新增场景类型（下拉第 8 项）**
- `exhibition` 露出·偷窥：`exhibition_daily` 15 / `exhibition_flirt` 20 / `exhibition_sex` 20 / `voyeur_flirt` 15

**新增玩法池（细分动作，替代过去只能抽 `duo_male` 一刀切）**
- `foreplay_flirt` 20（隔衣）/ `foreplay_sex` 20 / `oral_sex` 20 / `paizuri_sex` 20 / `handjob_sex` 20 / `footjob_sex` 40
- 全部 `g:1, m:1` —— `m:0` 会把 `penis`/`fellatio` 当男位词删掉，画面变成对空气做动作

**池引用去重**
- `duo_sfw` 从 56 条删到 15 条（只留男女特有），其余 41 条标 `shared:true` 留在 `duo_daily`，
  由 `POOL_INHERIT` + `poolItems()` 单份引用，不再双写维护

**扩库**
- `after` 13 → 46：温存 + 事后结算（`creampie` / `cumdrip` / `trembling` / `partially_clothed`）
- 丝袜载体 40 条按 target 分发，`footjob_sex` 22/40 带袜子（此前全库 `pantyhose` 仅 3 条）

**修复**
- **`EXPLICIT_SOFT` 误伤日常穿着**：丝袜 9 个、露肩 4 个、汗/湿 2 个共 15 个词被当擦边，
  健全档会静默删掉角色身上的丝袜和露肩。已移出该表。
- **复杂构图黑名单**：新增 `NO_POSE`（69 / 悬空 / 倒立 / 折身位 / 多人交错 / 抱起离地），
  `preflight` ①b 段命中即剔。用户明确"这类构图出图效果很差"。
- **袜子被连带删衣**：`pantyhose` 触发 `open_clothes` → `FULLGARB` 删裙子。`USTATE`/`CLOTHED_KEEP` 补袜子类。
- **`duoOK` 误剔玩法池**：锁「双人·男女」时"男"是无脸男不是第二张卡，带 `penis` 的池曾被 100% 剔除。
- **`rollLibrary` 顺序**：`sceneKind/scenePool` 赋值晚于 `setTags`，随机一套读到上一张的池。
- **`duo_flirt` 死池复活**：65 条双女文本此前没有任何出口。

**权重与配比**
- 新增模块级 `POOL_W`（`oral 4 / foreplay 4 / paizuri 3 / handjob 2 / footjob 2 / after 3`），
  取代 `EX_LOW` 硬编码；主池权重 `5 × 辅池数` 动态化。
- 真配比：duo/r18 → `duo_male 79.2% + 玩法 19.4%`；yuri/suggestive → `yuri_flirt 56% / duo_flirt 44%`。

**测试**
- `_style_test/test_preflight.js` 20/20、`test_plan.js` 11/11，用本机 node 直接调内部函数。

### 角色 LoRA 与画风 LoRA 叠加（2026-11-14 下午）

此前角色卡只有 `trigger` 文本、没有 `lora` 字段 —— 点角色只是把 tag 写进提示词，
角色 LoRA 从未被加载。已给 18 张 AI 拟人卡补 `lora` / `lora_w`。

- `anima_loras()` 改三层：基座（turbo 0.7）→ 角色包 → 画风包
- `gen_graph` / `anima_handfix` / `gen_submit` 全部接受 `char_id`
- **多人一律卸角色 LoRA**：`_anima_multi()` 命中 `2girls` 等即清空 `char_id`。
  实测四组对照（不挂 / 双挂 0.5+0.5 / 只挂 A / 只挂 B）全部串味 —— 单包特征覆盖整张图，
  而东方角色没有 LoRA 所以双人从来不串。
- **角色词条分层**：拆 `trig_core`（身份）+ `trig_outfit`（整件衣物），性场景自动只留身份。
  实测 grok-tan 健全 → 带 `black red short dress`；性场景 → 只剩 `gold crown, blue eyes, blonde twintails`。

### 文档整理（2026-11-14 晚）

`docs/` 从 11 份精简到 6 份。归档到 `docs/_archive/`（不进仓库）：
`历史与回退-v3.md`（278KB 旧流水）、`手册-v3.md`（v3 工作台手册）、`画师tag-实测清单.md`、
`Anima画风-保留名单.md`、`Anima-32包编号清单.md`、`Anima画风LoRA-搬运清单.md`。

保留：`提示词与场景-v3.md`（主文档）、`Anima画风LoRA-交接手册.md`、`Anima画风LoRA-测评台帐.md`、
`Anima知识-v3.md`、`multi-turn-连续动作-方案.md`（新增）、本文件。

---

## 2026-11-14

### 画风库（v4.0）
新增 `webui/data/anima_styles.json`：114 个画风 LoRA 的索引，页面「画风」一栏按卡渲染。
基座从写死三条 LoRA 改为 `ANIMA_BASE_LORAS`（turbo 0.7）+ 选中画风包叠加；
`gen_graph` / `gen_submit` / `anima_handfix` 全部接受 `style_id`。

新增接口 `GET /api/styles`、`POST /api/style/select`、`GET /style_thumbs/<file>`。
114 张缩略图统一固定角色半身，保证画风可比。

**决策**：画风由 JSON 数据驱动，加包不改代码；点卡把触发词写进正向框，再点取消。

### AI 拟人（大模型娘）角色组
角色库新增 18 条双预设（正常版 / Q 版），作品名「AI 拟人（大模型娘）」：
鲸鱼娘、白龙娘、Gemini 娘、Claude 娘、Grok 娘、Kimi、GLM。

### 修复
- 修手图未透传 `style_id`，主图与修手图可能挂不同画风包。
- 触发词去重按整串比较，前端只写部分词时会重复前置；改为按首个 token 判断。
- `/api/wb/chars` 未排序就 `[:limit]`，新角色永远显示不出；改为按 `pop` 降序。
- 画风卡 `strength` 未从索引读出，全部按 1.0 跑，Q 版 0.75/0.85 失效。

## 2026-11-10

### 18:20 · 出图目录三处入口对齐
控制台的「📁 出图」按钮与「启动引擎」原来各自硬编码 `D:\ComfyUI\output`，页面里改了目录不生效。
现在四个入口统一读 `webui/data/wb_config.json`：页面 ⚙ 目录 / 工坊内重启 / 控制台启动 / 控制台出图按钮。
新增 `_setup/get_outdir.py` 作为单一取值点。

**教训**：`.cmd` 必须 CRLF；`for /f` 里嵌引号路径会静默失败，改用 `set /p`；批处理保持纯 ASCII。

### 17:55 · 出图目录可配置
新增 `GET/POST /api/config` 与 `POST /api/comfy/restart`。
换目录必须重启 ComfyUI（`--output-directory` 是启动参数）。
`/img/` 改为双目录兜底，切目录后历史图不 404。

### 17:40 · 2.9B 扩容版试验（已撤销）
试过把 28-block 底模合进 40-block 的社区扩容版。能跑，但：
提升不稳定（细节密集场景 +16%，低信息场景反而略降）、对比度整体降 5 点、
int8 权重无法存盘（只能工作流内现合，慢 1.4×）。已全部删除，释放 2.93 GB。

**教训**：验证扩容版必须先做低信息场景（夜景/剪影）对照，只测细节密集场景会高估收益。

### 15:30 · 画风量化调法
建立了亮度 / 对比度 / 饱和度 / 线条密度的量化指标，用于客观比较不同参数组合。

### 15:10 · 画师 tag 失效真因（重要）
三个原因叠加：
1. 后端 `to_anima_text()` 的正则把 `artist_(tag)` 的括号当权重语法剥掉，画师词根本没进编码器；
2. 前端点击画师写入 `\(` 转义，但 Anima 的方言是 `@artist (tag)`（下划线转空格、加 `@`）；
3. 两个画风 LoRA 把画师影响稀释约 22%（同 seed 对照 RMSE 78 vs 100）。

修完后 AB 对照 RMSE 从 <3（无效）升到 72–96（有效）。

### 14:20 · 缩略图与双人场景过滤
缩略图 URL 白名单补全 `( ) : ! + '` 等字符集，快照 912 张全部可达。
双人场景在抽取阶段就排除含男性词条的池，不再依赖事后审查。

### 13:45 · 缩略图「跑完但页面看不到」
两道独立闸门：插件路由白名单拒绝含括号的 slug；`wb_chars.json` 的 `th` 标记没人回刷。
修复后 291 张补完。

### 02:00 · 动作池第七类：催眠 / 主池去重修复
新增三档催眠池。顺带修了一个隐蔽 bug：`composeShot` 的去重把主池条目挡光，
导致 40 张批量里 50% 落到辅池。

---

## 2026-11-09

### 23:59 · 词库 v4：六类 × 三档
动作库重构成 24 个池（单人/双女/机械/调教/触手/三人/催眠 × 三档 + 5 个辅助池），
共 1087 条，组合数 9252 万。每条带「核心动作词」，避免被表情与光线词稀释。

### 22:55 · 首屏白屏修复 + 首模块统一
`loadData()` 里一个探针访问了已不存在的字段，抛错被 `boot()` 的 catch 吞掉后直接 return，
后续渲染全部跳过 → 切一次标签才恢复。

**教训**：启动路径上的探针必须不可抛；`catch` 里不能静默 `return`。

### 22:12 · 表情分型 / 抑制水印 / 主体三档
表情按档位分变体并做每批上限；负面词加权抑制；主体处理提供「无脸 / 隐形 / 仅器官」三档。

### 21:45 · 链路级审查清零
把「抽词 → 归一 → 提交 → 审查」当成一条链做端到端断言，六档抽样指标全部归零。

### 20:52 · 池化重构：11 池 + 池级性别审查
动作从「三张大表 + 事后过滤」改成「按档位×人数分池 + 池声明性别构成」。

### 19:40 · 原子库 74 → 150 + 出图前审查
首次引入 `preflight()`：提交前统一收束人数、性别、视角冲突。

### 19:25 · 修「整页 JS 不执行」
一段诊断代码把换行写成了字面换行，字符串未闭合，整个 `<script>` 解析失败。

**教训**：任何写进 JS 字符串的换行都用 `String.fromCharCode(10)`，别依赖编辑器不转义。

---

## 更早

见本地 `docs/历史与回退-v3.md`（2026-11-07 起的完整记录）。
