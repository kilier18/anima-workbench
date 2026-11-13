# -*- coding: utf-8 -*-
"""创建 GitHub Release 并上传发行 zip。"""
import json, os, urllib.request, urllib.error

OWNER, REPO, TAG = "kilier18", "anima-workbench", "v4.0"
ZIP = r"D:\ComfyUI\dist\anima-workbench-v4.0.zip"
TOKEN = open(os.path.expanduser(r"~\.dsh\github-token.txt"), encoding="utf-8").read().strip()
API = "https://api.github.com"

BODY = """# Anima Workbench v4.0

本地插画工作台：提示词编排 + 批量出图 + 画风库，跑在 ComfyUI 之上。所有素材与结果都留在本机。

## 本版新增

- **画风库**：114 个画风 LoRA 一键切换，点卡即挂，自带触发词与强度；缩略图统一固定角色，画风可直接横比
- **AI 拟人（大模型娘）**：18 条角色双预设（正常版 / Q 版）
- 画风由 `webui/data/anima_styles.json` 数据驱动，加包不改代码
- 修手图与主图共用同一画风包；画风卡强度按索引生效

## 安装

下载 `anima-workbench-v4.0.zip`，解压到 ComfyUI 根目录，双击 `install.cmd`（7 步向导）。

已有 ComfyUI + Anima 环境的话：改 `_setup\\start_engine.cmd` 与 `start_assistant.cmd` 里的 ROOT 路径，依次启动引擎与工坊，浏览器开 `http://127.0.0.1:8190`。

## 依赖

- ComfyUI（含 ComfyUI-Manager、Impact-Pack、GGUF、IPAdapter_plus）
- Anima 底模：UNet + Qwen3-0.6B 文本编码器 + Qwen-Image VAE
- Python 3.12+

## 关于画风 LoRA

LoRA 权重不随包分发。放进 `models/loras/` 后，在 `webui/data/anima_styles.json` 追加一条记录即可出现在画风栏。
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
    with urllib.request.urlopen(r, timeout=180) as resp:
        raw = resp.read()
        return resp.status, (json.loads(raw.decode("utf-8")) if raw[:1] in (b"{", b"[") else raw)

try:
    st, rel = req("GET", "%s/repos/%s/%s/releases/tags/%s" % (API, OWNER, REPO, TAG))
    print("release exists", rel.get("html_url"))
except urllib.error.HTTPError as e:
    if e.code != 404:
        raise
    st, rel = req("POST", "%s/repos/%s/%s/releases" % (API, OWNER, REPO), {
        "tag_name": TAG,
        "name": "Anima Workbench v4.0",
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
