# Anima 生图知识 3.1

> 配套 `workbench-维护手册.md`。所有数字都是本机实测（RTX 40 系 + 32GB 内存，ComfyUI 便携版）。
> 3.1 起 WAI v17 已下线，本文只写 Anima，WAI 的对照列已删。

---

## 1. 底模（3.1：只剩 Anima）

| 项 | Anima 12（`miaomiaoHarem_anima12`） |
|---|---|
| 文本编码器 | **Qwen3 0.6B**（不是 CLIP） |
| 权重语法 | **无效**（`(word:1.2)` 不生效） |
| 标签写法 | danbooru tag 与自然语言混排都行 |
| 画师 | 必须 `@画师名` 前缀 |
| 步数 / CFG | 10 / 1.0 |
| 采样 / 调度 | `er_sde` / `beta` |
| 默认分辨率 | 1024×1536 |
| 单张耗时 | 9–18s |
| 擅长 | 二次元、日式画风、表情 |
| 短板 | 手部易崩、道具穿帮 |

**分工**：全部走 Anima。WAI v17 已于 3.1 移除。

---

## 2. 参数口径

| 项 | 值 | 说明 |
|---|---|---|
| 步数 | 10 | turbo LoRA **1.0**（实测值，与 §10 速查卡一致），再多是浪费 |
| CFG | **1.0**（默认） | 2B DiT + turbo，cfg>1 容易过饱和 |
| 采样器 / 调度 | `er_sde` / `beta` | 10730 那组参数在本机最稳 |
| 分辨率 | 832×1216（竖图）/ 1024×1536 | 见 §3 |

**cfg=1 的已知缺陷**：负向完全不参与（同 seed 换负向内容，像素差异 0.0000%）。
要负向生效只有两条路：

1. **把 CFG 提到 2.0 以上** —— 实测有效但会改变画风（对比度上升），不适合所有场景。
2. **装 `ComfyUI-Anima-NAG`**（`AnimaNormalizedAttentionGuidance`）—— 在 attention 层
   把负向当"推离方向"接回，cfg 仍是 1。温和档 `scale 1.0 / tau 1.2 / alpha 0.5 / end 0.4`
   可用；官方默认（scale 2.0 / tau 2.5 / end 0.5）在 Anima base 上会把主体压没。
   代价约 **+4s/张（+38%）**。`assistant.py` 已支持（`/api/gen` 传 `nag`），页面暂无入口。


## 3. 分辨率

| 尺寸 | 耗时 | 对比 | 饱和 | 备注 |
|---|---|---|---|---|
| 832×1216 | 18.1s | 65.9 | 37.7 | 快，适合批量 |
| 1024×1536 | 16.1s | 66.8 | 43.0 | **默认** |
| 1152×1728 | 20.1s | 60.7 | 35.5 | 细节更好，略慢 |
| 1536×2304 | 36.2s | **51.0** | 58.5 | 长边>1792 微对比掉 24%，耗时翻倍 |

规则：长边别超 1792；要更大就出图后放大，不要直接抽。

---

## 4. 采样器与调度器

- `er_sde` + `beta`：Anima 官方组合，画面干净、线条稳。
- `euler` / `euler_ancestral`：更"硬"，对比略高，人物质感偏锐。
- `dpmpp_2m`：稳但慢，适合需要细腻渐变。
- 调度 `normal` 在 Anima 上会让高光过曝，除非刻意要"亮"。

---

## 5. 内存与稳定

- 15.8GB 内存下 `VAEDecode` 会随机 `Fatal Python error: Aborted`（解码阶段）。
- 解决：全链路换 `VAEDecodeTiled`（tile 512 / overlap 64 / temporal 64/8），代价是慢 1–2s，换来 100% 稳定。
- 显存不足时启动加 `--lowvram`；再不够就把扩写模型钉在 CPU（`num_gpu 0`）。

---

## 6. 手部加固

`FaceDetailer` 二段修手（只重画手部，不动其它区域）：

```
UltralyticsDetectorProvider(bbox/hand_yolov8s.pt)
→ FaceDetailer(steps 8, cfg 1.0, er_sde+beta, denoise 0.45,
               guide_size 384, max_size 768, bbox_threshold 0.35,
               dilation 12, crop_factor 2.5, feather 8)
```

- 检测不到手 → 直通（不会糊整张图）。
- 实测单张 8.1s，PIL diff 只落在手部区域。
- 什么时候用：手指交叠、抓握、贴近脸的手、被遮挡一半的手。

---

## 7. 负面与打码

- 默认负面就是代码里的 `DEF_NEG`（`tools/gen_workbench.py` 行 371-378），**50 个词条 / 7 组**，不是短表：
  1. 质量 / 人体（5）：`bad quality, worst quality, worst detail, bad anatomy, bad hands`
  2. 手指 / 肢体（6）：`extra hands, fused fingers, extra fingers, missing fingers, malformed limbs, extra limbs`
  3. 肌肉男（5）：`muscular_male, muscular, abs, bare_pectorals, back_muscles`
  4. 男体（6）：`male face, male body, visible male, male torso, male head, male eyes`
  5. 多头 / 配饰 / 衣物（8）：`multiple heads, two heads, hat on male, extra hat, duplicate accessory, duplicate, extra clothing, out of place clothing`
  6. 文字水印（5）：`text, speech bubble, japanese text, watermark, signature`
  7. 打码（15，`CENSOR_HARD` 带权重）：`(mosaic censoring:1.45), (bar censor:1.4), (censored:1.35), (pixelated:1.3), mosaic, square mosaic, blur censor, light censor, steam censor, hair censor, heart censor, convenient censoring, transparent censoring, out-of-frame censoring, censored genitals`
- **不要**在负面里写裸 `censored`：太模糊，反而容易勾出马赛克。
- 正面命中打码触发词（`cum_in_pussy / cumdrip / pussy / pussy_ejaculation / penis / sperm / spilling` 等）→ 自动补 `uncensored`，并把负面里的 censor 词全部剔掉（实测最稳）。
- 触手/机械类**不要**写 `penis / 1boy`，否则硬塞一个男人进来。

---

## 8. 方言（两套别混）

| 项 | Anima 方言（3.1 唯一） |
|---|---|
| 分隔 | 空格、无下划线 |
| 权重 | 无效，必须去掉 |
| 画师 | `@kanpa (campagne 9)` |
| 负面 | 50 词长表（`DEF_NEG`，见 §7） |
| 长度 | 上限 45 短语 |

页面固定用 Anima 方言（`/api/expand` 的 `dialect=anima`）。danbooru 方言（逗号 + 下划线、可用权重）只给旧脚本留兼容。

---

## 9. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 画出来像欧美 3D | CFG 太高 | 降到 1.0，或开 NAG 温和档 |
| 角色不像 | 权重语法 / 缺角色 tag | Anima 去掉权重，写全 `角色tag + 发色 + 瞳色 + 服装` |
| 两个人变一个人 | 只写了 `futanari` 或 `2girls` | 每个角色都写外貌；扶她补 `futa_with_female` |
| 多出一条腿 | `leg_lift` 等双侧词 | 双人场景剔双侧词，改 `from_side` 构图 |
| 出现 JK 裙 | `school_uniform`/`pleated_skirt` 先验 | 不写；要裙子用 `long_skirt`/`pencil_skirt` |
| 墙上洞里多一根 | 空间类 tag 先验 | 明确写 `glory_hole` + `penis` 数量描述 |
| 表情没出来 | 脸占画幅太小 | 加 `upper_body`，或换 `close-up` |
| 手崩 | 手指交叠 | 修手；或改姿势让手不重叠 |

---

## 10. 参数速查卡

```
Anima：10 步 / CFG 1.0（负向需 NAG）/ er_sde / beta / 1024×1536 / VAEDecodeTiled 512-64
       LoRA：turbo 1.0 + kinokohime 0.6 + konya 0.3
       CLIP：qwen_3_06b_base (stable_diffusion)   VAE：qwen_image_vae
修手 ：8 步 / CFG 1.0 / denoise 0.45 / guide 384 / max 768
```
