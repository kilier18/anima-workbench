# -*- coding: utf-8 -*-
"""创建 GitHub Release v5.0 并上传发行 zip。"""
import json, os, urllib.request, urllib.error

OWNER, REPO, TAG = "kilier18", "anima-workbench", "v5.0"
ZIP = r"D:\ComfyUI\dist\anima-workbench-v5.0.zip"
TOKEN = open(os.path.expanduser(r"~\.dsh\github-token.txt"), encoding="utf-8").read().strip()
API = "https://api.github.com"

BODY = """# Anima Workbench v5.0

本地插画工作台：提示词编排 + 批量出图 + 画风库，跑在 ComfyUI 之上。所有素材与结果都留在本机。

**这一版把「批量出图」从"抽一堆互不相干的图"改成了"排一场戏"**：一批图 = 若干动作块，每块几个机位/动作/表情差分，块末带射精收尾，然后换下一个动作。

## 本版新增

### 块制排片（14 块）
前戏 / 口交 / 乳交 / 手交 / 足交 / 正面位 / 后入 / 骑乘 / 站立抱起 / 侧入 / 3P / 触手 / 机械 / 事后。
每块有 3–5 个子动作变体、一组合法机位、一个收尾词。50 / 100 / 190 张各有实测配额表。

### 复合层（可叠在任意块上）
**催眠**（hypnosis + mind_control + ringed_eyes / empty_eyes）与**调教**（bound_wrists + shibari + blindfold / leash）。
不是独立块，是层 —— 可以"催眠口交""捆住手腕的后入"。每层带 `tone` / `look` / `deny` / `banPose` 四类词，三道闸防串味。

### 男体三档
- 玩法段（口/乳/手/足）：`penis, solo_focus` —— 画面只有一根，占的画面最小
- 正戏 / 事后：`1boy, hetero`
- 触手 / 机械：整块无人形

`invisible_man` 全项目下线（2B 底模会理解成多一条腿或鬼影）。

### 机位
`profile`（侧面轮廓）下线 —— 语义是侧脸肖像，在实际画面里变成"别过脸"。
新增 `foreshortening`（透视压缩）与 `internal_cumshot`（插入内视小窗）。
机位真空行从 14% 降到 0；3P 固定侧面（三人改视角会叠成一团）。

### 出图落盘
每张图自动另存到「⚙ 目录」设的路径，文件名 `034_骑乘_hypno_插入内视_anima_pg_00034_.png`。

### 负向真的生效了
接 [Anima-NAG](https://github.com/hybskgks28275/ComfyUI-Anima-NAG)：cfg=1 下负向本来完全不参与（实测像素差 0.0000%），装上后 99.5%。
页面「负面生效」默认勾选，每张 +4 秒。

### 角色卡
- ai_gijinka 18 张卡 77 个词条补中文
- 修三处漏点：`trig_outfit` 这一列从来没被读过 / 前端无条件拼服装触发词 / `FULLGARB` 缺鞋类
- R18 只脱衣物、保留头饰帽子等配饰

## 安装

下载 `anima-workbench-v5.0.zip`，解压到 ComfyUI 根目录，双击 `install.cmd`（7 步向导）。

**换了安装盘也不用改代码**：`assistant.py` 和三个启动脚本全部从自身位置推导路径。
已有环境的话，依次启动引擎与工坊，浏览器开 `http://127.0.0.1:8190`。

## 依赖

**必需节点**：`ComfyUI-Anima-NAG` / `ComfyUI-Impact-Pack` / `ComfyUI-Impact-Subpack` / `Comfyui-Anima-Wardrobe-V5`
**可选节点**：`ComfyUI-Anima-Ref-Adapter`（参考图锁角色）/ `comfyui-anima-style-nodes` / `ComfyUI-GGUF` / `ComfyUI_IPAdapter_plus` / `ComfyUI-Manager`

**模型**：Anima UNet + Qwen3-0.6B 文本编码器 + Qwen-Image VAE + `anima-turbo-lora-v0.2`（放 `models/loras/Anima/`）+ `anima_ref_adapter_v2_r64`（放便携版 `models/loras/`）

Python 3.13（便携版自带）。工作台自身零第三方硬依赖。

## 已知边界

- 角色 LoRA 里烘死的服装拿不掉（`grok-tan` 只给触发词仍穿黑红短裙）
- `deepseek-tan-chibi` 的 `ds_whalemaid` 是合成 token，拆不开
- 单人角色下 3P 块不排（会被"单人剔多人"清空）
- `from_side` 占机位 48%：这是"块名准确"的代价（后入 25 张里 19 张必须背后机位）

详细部署见仓库里的 `DEPLOY.md`。
"""


def req(method, url, data=None, ctype="application/json", accept="application/vnd.github+json"):
    body = None
    if data is not None:
        body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Authorization", "Bearer " + TOKEN)
    r.add_header("Accept", accept)
    r.add_header("Content-Type", ctype)
    r.add_header("User-Agent", "anima-workbench-release")
    with urllib.request.urlopen(r, timeout=300) as resp:
        raw = resp.read()
        return resp.status, (json.loads(raw.decode("utf-8")) if raw[:1] in (b"{", b"[") else raw)


try:
    st, rel = req("GET", "%s/repos/%s/%s/releases/tags/%s" % (API, OWNER, REPO, TAG))
    print("release exists", rel.get("html_url"))
    req("PATCH", "%s/repos/%s/%s/releases/%d" % (API, OWNER, REPO, rel["id"]), {"body": BODY, "name": "Anima Workbench v5.0"})
    print("body updated")
except urllib.error.HTTPError as e:
    if e.code != 404:
        raise
    st, rel = req("POST", "%s/repos/%s/%s/releases" % (API, OWNER, REPO), {
        "tag_name": TAG,
        "name": "Anima Workbench v5.0",
        "body": BODY,
        "draft": False,
        "prerelease": False,
    })
    print("release created", rel.get("html_url"))

rid = rel["id"]
existing = {a["name"]: a for a in rel.get("assets", [])}
name = os.path.basename(ZIP)
if name in existing:
    print("asset exists, deleting", existing[name]["id"])
    req("DELETE", "%s/repos/%s/%s/releases/assets/%d" % (API, OWNER, REPO, existing[name]["id"]))

with open(ZIP, "rb") as f:
    blob = f.read()
print("uploading", name, "%.1fMB" % (len(blob) / 1048576))
st, asset = req("POST",
    "https://uploads.github.com/repos/%s/%s/releases/%d/assets?name=%s" % (OWNER, REPO, rid, name),
    blob, ctype="application/octet-stream")
print("uploaded", st, asset.get("browser_download_url"), asset.get("size"))
print("RELEASE", rel.get("html_url"))
