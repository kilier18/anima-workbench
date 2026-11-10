# 部署手册 · 从零到出图

面向一台**全新的 Windows 电脑**。按顺序做完，工坊能跑起来并出图。
全程约 40–60 分钟，其中模型下载占大头（约 8 GB）。

> 所有路径示例以 `D:\ComfyUI` 为准。装在别处就把下文所有 `D:\ComfyUI` 换成你的实际路径。

---

## 0. 两条路，先选一条

| | 自动安装（推荐） | 手动安装 |
|---|---|---|
| 适合 | 想要最快跑起来 | 想自己控制每一步、或已有 ComfyUI |
| 命令 | 双击 `install.cmd` | 跟本文第 1–7 节手工做 |
| 时间 | 全自动，模型仍需下载 | 40–60 分钟 |

### 自动安装

把整个仓库下载到本地（`git clone https://github.com/kilier18/anima-workbench.git D:\ComfyUI`），然后双击仓库根目录的 **`install.cmd`**，或者在命令行里：

```bat
install.cmd            :: 全部 7 步
install.cmd 1          :: 只跑第 1 步（环境自检）
install.cmd 6 D:\AI    :: 只跑第 6 步，并装到 D:\AI
```

它会依次完成：

1. **环境自检** — 系统版本、目标盘剩余空间、git、显卡与显存、内存
2. **装 ComfyUI** — 没有就自动查 GitHub 最新 release 下载 portable 包；已有就跳过
3. **建模型目录** — 12 个模型子目录 + `extra_model_paths.yaml`（已存在不覆盖）
4. **下载模型** — 文本编码器、VAE、底模三个必需文件直连 HuggingFace
5. **装自定义节点** — Manager / Impact-Pack / Impact-Subpack 必需，GGUF / IPAdapter 可选
6. **装工作台** — 拉本仓库，并把脚本里的路径改成本机 `-Dir`
7. **冒烟验证** — 编译检查 + 数据体检 + 仓库一致性

装完按第 8 节启动即可。任何一步失败都停在原地打印原因，修好后用 `install.cmd N` 单独重跑那一步。

### 手动安装

继续往下看第 1 节。

---

## 0.1 先确认硬件

| 项目 | 最低 | 舒服 |
|---|---|---|
| GPU | NVIDIA，6 GB 显存 | 8 GB 以上 |
| 内存 | 16 GB | 32 GB |
| 磁盘 | 30 GB 空闲（模型约 8 GB + 输出） | SSD，60 GB |
| 系统 | Windows 10 21H2 / 11 x64 | 同左 |

6 GB 显存（例如 RTX 4050 Laptop）可以跑，但必须开 `--lowvram`；出 832×1216 一张约 30–45 秒。
AMD / Intel 显卡理论上 ComfyUI 也能跑，但本手册只覆盖 NVIDIA 路径。

---

## 1. 装 ComfyUI（portable 版）

1. 打开 <https://github.com/comfyanonymous/ComfyUI/releases>，下载最新的 `ComfyUI_windows_portable_nvidia.7z`。
2. 解压到 `D:\ComfyUI\ComfyUI_windows_portable`。
   解压后应该看到：

   ```
   D:\ComfyUI\ComfyUI_windows_portable\
   ├─ ComfyUI\              ← 主体
   ├─ python_embeded\       ← 自带 Python，不用另装
   └─ run_nvidia_gpu.bat
   ```

3. 先双击 `run_nvidia_gpu.bat` 跑一次，确认浏览器能打开 `http://127.0.0.1:8188`，看到默认工作流界面。**这一步不通，后面都不用做。**

> 用的是 portable 包自带的 Python：`D:\ComfyUI\ComfyUI_windows_portable\python_embeded\python.exe`。
> 本文档所有 `python` 命令都指这个解释器。

---

## 2. 建统一模型目录

portable 包每次重装都会覆盖内部 `models`，所以把模型放外面、用配置文件指过去。

```bat
mkdir D:\ComfyUI\models\diffusion_models\Anima
mkdir D:\ComfyUI\models\text_encoders
mkdir D:\ComfyUI\models\vae
mkdir D:\ComfyUI\models\loras\Anima
mkdir D:\ComfyUI\models\checkpoints
```

在本仓库根目录已有一份 `extra_model_paths.yaml`，如果你把仓库放在 `D:\ComfyUI`（推荐），**不用改**。
装在别处就把里面的 `base_path: D:/ComfyUI/models` 改成你的实际路径。

---

## 3. 下载模型

### 3.1 主模型（必需，约 4.2 GB）

| 文件 | 放到 | 说明 |
|---|---|---|
| `miaomiaoHarem_anima12.safetensors` | `models\diffusion_models\Anima\` | 本项目调好的融合版（2.09B 参数，BF16） |
| `anima-base-v1.0.safetensors`（备选） | 同上 | 官方原版，效果略不同，二选一即可 |

获取途径：

- 官方底模：<https://huggingface.co/circlestone-labs/Anima> → `anima-base-v1.0.safetensors`
- 融合版：HuggingFace 搜索 `miaomiaoHarem`（社区发布，作者与版本可能变动）
- 国内下载慢的话，用 `hf-mirror.com` 替换域名即可

**换模型只需改一处**：`webui/assistant.py` 里的

```python
ANIMA_UNET = r"Anima\miaomiaoHarem_anima12.safetensors"
```

改成你的文件名。

### 3.2 文本编码器与 VAE（必需）

| 文件 | 放到 | 来源 |
|---|---|---|
| `qwen_3_06b_base.safetensors` | `models\text_encoders\` | <https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI> 的 `split_files/text_encoders/` |
| `qwen_image_vae.safetensors` | `models\vae\` | 同一仓库 `split_files/vae/` |

> Anima 是 Cosmos-Predict2 架构，**不是 SDXL**，文本编码器必须用 Qwen3-0.6B，拿 SDXL 的 CLIP 会直接报维度错。

### 3.3 LoRA（建议装，可关）

| 文件 | 放到 | 作用 |
|---|---|---|
| `anima-turbo-lora-v0.2.safetensors` | `models\loras\Anima\` | 加速；官方 Anima 仓库里带 |
| `kinokohime_v2.safetensors` | 同上 | 画风 |
| `konyaKarasue_Anima1_lora_V42.safetensors` | 同上 | 画风 |

三个 LoRA 的权重写在 `webui/assistant.py`：

```python
ANIMA_LORAS = [
    (r"Anima\anima-turbo-lora-v0.2.safetensors", 1.0),
    (r"Anima\kinokohime_v2.safetensors", 0.6),
    (r"Anima\konyaKarasue_Anima1_lora_V42.safetensors", 0.3),
]
```

缺哪个就删哪一行，或把权重写成 `0`。**两个画风 LoRA 会稀释画师 tag**（实测约 22%），
想要画师词更准就把后两个权重降到 0.2 以下。

---

## 4. 装自定义节点

```bat
cd D:\ComfyUI\ComfyUI_windows_portable\ComfyUI\custom_nodes

git clone https://github.com/ltdrdata/ComfyUI-Manager
git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack
git clone https://github.com/ltdrdata/ComfyUI-Impact-Subpack
git clone https://github.com/city96/ComfyUI-GGUF
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus
```

| 节点包 | 必需？ | 缺了会怎样 |
|---|---|---|
| ComfyUI-Manager | 建议 | 装别的节点要靠它 |
| ComfyUI-Impact-Pack | **必需** | 工坊的「修手」用 FaceDetailer，缺了出图报节点缺失 |
| ComfyUI-Impact-Subpack | **必需** | FaceDetailer 的检测模型依赖 |
| ComfyUI-GGUF | 可选 | 只有用 GGUF 量化模型才需要 |
| ComfyUI_IPAdapter_plus | 可选 | 参考图风格迁移 |

`Comfyui-Anima-Wardrobe-V5`（角色/场景资源包）**可选**：装了角色缩略图更全，没装工坊会自动回落到自带数据。

装完重启一次 ComfyUI，看启动日志有没有 import 报错。

> Impact Pack 首次启动会下载检测模型（`bbox/face_yolov8m.pt` 等），需要能访问 GitHub。

---

## 5. 部署本仓库

```bat
git clone <本仓库地址> D:\ComfyUI
```

> 目录里已经有 `ComfyUI_windows_portable` 时，`git clone` 会报"目录非空"。
> 两种办法：先把仓库 clone 到 `D:\ComfyUI_new` 再挪过去，或者 `git init` 后 `git remote add origin <地址> && git fetch && git checkout -f main`。

克隆完检查这几个文件在不在：

```
D:\ComfyUI\webui\assistant.py
D:\ComfyUI\webui\workbench.html
D:\ComfyUI\webui\data\wb_atoms.json
D:\ComfyUI\_setup\start_engine.cmd
D:\ComfyUI\_setup\start_assistant.cmd
```

### 5.1 改三个脚本里的路径

如果仓库不在 `D:\ComfyUI`，这三个文件里的 `ROOT` 都要改：

- `_setup\start_engine.cmd` → `set "ROOT=D:\ComfyUI"`
- `_setup\start_assistant.cmd` → `set "PY=..."` 与 `cd /d "..."`
- `ComfyUI控制台.ps1`（可选，图形界面用）→ `$ROOT = 'D:\ComfyUI'`

**注意：`.cmd` 文件必须保持 CRLF 换行。** 用 VS Code 保存时右下角选 `CRLF`，
用 Git 时确保 `core.autocrlf` 不会把它转成 LF——LF 的批处理会报
`'ComfyUI"' 不是内部或外部命令` 这类莫名错误。

### 5.2 出图目录

默认出图到 `D:\ComfyUI\output`。想换盘：启动工坊后点右上角 **⚙ 目录** 改，会在
`webui\data\wb_config.json` 落盘，控制台和启动脚本都读这一份。

---

## 6. 启动

**方式 A：图形控制台（推荐）**

右键 `ComfyUI控制台.ps1` → 用 PowerShell 运行。窗口里有启动引擎 / 停止 / 打开工坊 / 📁 出图。

**方式 B：两个命令行窗口**

```bat
:: 窗口 1
D:\ComfyUI\_setup\start_engine.cmd

:: 窗口 2
D:\ComfyUI\_setup\start_assistant.cmd
```

等 ComfyUI 日志出现 `To see the GUI go to: http://127.0.0.1:8188` 后，
浏览器打开 <http://127.0.0.1:8190>。

---

## 7. 验证部署

### 7.1 数据体检

```bat
cd D:\ComfyUI
python tools\health_check.py
```

期望最后一行是 `失败 0 / 28`，并打印类似：

```
{"zh": 6472, "tags": 1965, "chars": 2390, "scenes": "963", "presets": "46(26+20)", "thumbs": 910}
```

### 7.2 出图冒烟测试

浏览器打开工坊 → 选一个角色 → 点「🎨 生成」。
30–60 秒后图应该出现在右侧网格，同时落盘到出图目录。

命令行验证（不依赖前端）：

```bat
curl -s http://127.0.0.1:8188/system_stats
```

返回 JSON 就说明 ComfyUI 活着。

### 7.3 检查审查链路

页面右上角「① 提示词」标题旁应该有个绿底徽标 `审查 ✓`。
如果显示 `审查 修N`，说明自动改了 N 处冲突（正常，点开能看到改了什么）。

---

## 8. 故障排查

| 症状 | 原因 | 处理 |
|---|---|---|
| 页面全白 | 后端没起 / 数据加载失败 | 浏览器 F12 看 Console；`webui\assistant.err.log` 有堆栈 |
| `数据加载失败 TypeError` | `webui\data` 缺文件 | 检查 `wb_atoms.json` 等 8 个文件是否齐全 |
| 出图报 `node type not found: FaceDetailer` | 缺 Impact-Pack | 按第 4 节装 |
| 出图报 `CLIP input is invalid` | 文本编码器不对 | 必须 Qwen3-0.6B，不是 SDXL CLIP |
| 显存溢出 `CUDA out of memory` | 分辨率太高 | 启动加 `--lowvram`；降宽高到 832×1216 以下 |
| 图落到 `D:\ComfyUI\output` 而不是自定义目录 | `wb_config.json` 没被读到 | 重启 ComfyUI；目录必须已存在且可写 |
| 控制台「📁 出图」打开旧目录 | 同上的缓存问题 | 已修为每次点击重读配置，若仍旧请更新仓库 |
| 批处理报 `'ComfyUI"' 不是内部或外部命令` | `.cmd` 被存成 LF | 转成 CRLF 保存 |
| 角色缩略图全是首字母 | 缺 `presets/thumbs` | 可选，用 `tools/gen_char_thumbs_local.py` 重新生成 |

日志位置：

- ComfyUI：`_setup\comfy.log`、`_setup\comfy.err.log`
- 工坊后端：`webui\assistant.log`、`webui\assistant.err.log`

---

## 9. 下一步

- 改动作库 → 见 `README.md` 的「核心概念：动作池」
- 改场景/角色 → 直接编辑 `webui/data/*.json`，刷新页面即生效
- 看变更历史 → `docs/历史与回退-v3.md`（只追加，新条目在最上方）
- 看使用手册 → `docs/手册-v3.md`
