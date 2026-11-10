# Anima 生图知识 3.1

> 配套 `手册-v3.md`。所有数字都是本机实测（RTX 40 系 + 32GB 内存，ComfyUI 便携版）。
> 3.1 起 WAI v17 已下线，本文只写 Anima；WAI 的历史对照留在下表以便看懂旧记录。

---

## 1. 底模（3.1：只剩 Anima）

| 项 | Anima 12（`miaomiaoHarem_anima12`） | WAI v17（`waiIllustriousSDXL_v170`） |
|---|---|---|
| 文本编码器 | **Qwen3 0.6B**（不是 CLIP） | CLIP（SDXL） |
| 权重语法 | **无效**（`(word:1.2)` 不生效） | 有效 |
| 标签写法 | danbooru tag 与自然语言混排都行 | 纯 danbooru tag |
| 画师 | 必须 `@画师名` 前缀 | 普通 tag |
| 步数 / CFG | 10 / 1.0 | 26 / 7.0 |
| 采样 / 调度 | `er_sde` / `beta` | `euler_ancestral` / `normal` |
| 默认分辨率 | 1024×1536 | 832×1216 |
| 单张耗时 | 9–18s | 18–30s |
| 擅长 | 二次元、日式画风、表情 | 结构稳定、手部略好 |
| 短板 | 手部易崩、道具穿帮 | 画风偏欧美、慢 |

**分工**：全部走 Anima。WAI v17 已于 3.1 移除，旧记录里看到 WAI 参数只当历史对照。

---

## 2. 为什么 10 步比 20/30 步好

同一提示词、同一 seed、只改步数与 CFG（832×1216）：

| 组合 | 耗时 | 饱和 | 亮度 | 对比 | 边缘密度 | 平涂度 |
|---|---|---|---|---|---|---|
| 10 步 CFG1 | **12.1s** | 51.9 | 157.8 | 63.9 | 11.1 | 15.59 |
| 20 步 CFG1 | 16.1s | 57.2 | 144.9 | 64.3 | 11.8 | 15.91 |
| 30 步 CFG1 | 20.5s | 59.9 | 141.8 | 64.3 | 10.6 | 15.52 |
| 10 步 CFG4 | 16.1s | **122.4** | 138.8 | 80.0 | 15.4 | 16.44 |
| 20 步 CFG4 | 28.6s | 85.4 | 143.1 | 79.9 | **20.0** | **19.40** |
| 30 步 CFG4 | 42.3s | 86.1 | 145.8 | 79.6 | 19.0 | 18.72 |

结论：

1. **CFG 才是画风漂移主因**：10 步时 CFG 1→4，饱和度 +136%、对比 +25%，直接变"欧美 CG 塑料感"。
2. turbo 是**步数蒸馏 LoRA**，10 步是它的设计工况；CFG>1 时继续加步数只会让细节碎片化（边缘密度 15.4→20.0、平涂度 16.4→19.4）。
3. 想要"更像角色"：`CFG 1.0`，别加步数。
4. 20/30 步在 CFG1 下也合格，只是慢（12.1s vs 20.5s），性价比不如 10 步。

---

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

- 默认负面：`bad quality, worst quality, worst detail, bad anatomy, bad hands, muscular_male, muscular, abs, bare_pectorals, back_muscles, bar censor, mosaic censoring, convenient censoring, pixelated, mosaic, blur censor, censored genitals`
- **不要**在负面里写裸 `censored`：太模糊，反而容易勾出马赛克。
- 正面命中打码触发词（`cum_in_pussy / cumdrip / pussy / pussy_ejaculation / penis / sperm / spilling` 等）→ 自动补 `uncensored`，并把负面里的 censor 词全部剔掉（实测最稳）。
- 触手/机械类**不要**写 `penis / 1boy`，否则硬塞一个男人进来。

---

## 8. 方言（两套别混）

| 项 | danbooru 方言（WAI，已下线） | Anima 方言（3.1 唯一） |
|---|---|---|
| 分隔 | 逗号 + 下划线 | 空格、无下划线 |
| 权重 | 可用 | 无效，必须去掉 |
| 画师 | 普通 tag | `@kanpa (campagne 9)` |
| 负面 | 长表 | 14 词短表 |
| 长度 | 30–60 词 | 上限 45 短语 |

页面固定用 Anima 方言（`/api/expand` 的 `dialect=anima`）。danbooru 方言只给旧脚本留兼容。

---

## 9. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 画出来像欧美 3D | CFG 太高 | 回到 CFG 1.0 |
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
Anima：10 步 / CFG 1.0 / er_sde / beta / 1024×1536 / VAEDecodeTiled 512-64
       LoRA：turbo 1.0 + kinokohime 0.6 + konya 0.3
       CLIP：qwen_3_06b_base (stable_diffusion)   VAE：qwen_image_vae
修手 ：8 步 / CFG 1.0 / denoise 0.45 / guide 384 / max 768
```
