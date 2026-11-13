# -*- coding: utf-8 -*-
"""查 豆包(Doubao) / 元宝(Yuanbao) / 其他国内大模型 在 Civitai 的 Anima LoRA。"""
import json, os, time, urllib.parse, urllib.request

TOKEN = ""
tp = os.path.expanduser(r"~\.dsh\civitai-token.txt")
if os.path.exists(tp):
    TOKEN = open(tp, encoding="utf-8").read().strip()

QUERIES = [
    "doubao", "豆包", "doubao (character)", "字节豆包",
    "yuanbao", "元宝", "tencent yuanbao", "腾讯元宝",
    "hunyuan", "混元", "ernie", "文心一言", "ernie bot",
    "baichuan", "百川", "minimax", "海螺", "spark", "讯飞星火",
    "tiangong", "天工", "kimi", "glm", "zhipu", "qwen", "通义千问",
    "gpt", "claude", "gemini", "grok", "deepseek",
]

OUT = r"D:\ComfyUI\logs\anima_cn_models_scan.json"


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            if TOKEN:
                req.add_header("Authorization", "Bearer " + TOKEN)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == tries - 1:
                return {"_err": str(e)}
            time.sleep(1.5 + i)


def anima_versions(m):
    out = []
    for v in m.get("modelVersions", []):
        if v.get("baseModel") != "Anima":
            continue
        files = [f for f in v.get("files", []) if f.get("type") == "Model" and f.get("sizeKB", 0) > 10000]
        if files:
            out.append({
                "version": v.get("name"), "vid": v.get("id"),
                "sizeMB": round(files[0]["sizeKB"] / 1024, 1),
                "file": files[0].get("name"),
                "trig": (v.get("trainedWords") or [])[:3],
                "dl": v.get("stats", {}).get("downloadCount") or 0,
            })
    return out


rows, seen = [], set()
for q in QUERIES:
    url = "https://civitai.com/api/v1/models?limit=30&nsfw=true&query=" + urllib.parse.quote(q)
    d = get(url)
    items = d.get("items", [])
    hits = 0
    for m in items:
        av = anima_versions(m)
        if not av:
            continue
        if m["id"] in seen:
            continue
        seen.add(m["id"])
        hits += 1
        rows.append({"query": q, "id": m["id"], "name": m.get("name"),
                     "type": m.get("type"), "vers": av})
    print("%-22s models=%-3d anima_hits=%d" % (q, len(items), hits))
    time.sleep(1.5)

json.dump(rows, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nTOTAL Anima models:", len(rows), "->", OUT)

want = ["doubao", "豆包", "yuanbao", "元宝"]
print("\n=== 豆包/元宝 专项 ===")
found = False
for r in rows:
    nm = (r["name"] or "").lower()
    if any(w in nm for w in want) or any(any(w in (t or "").lower() for w in want) for v in r["vers"] for t in v["trig"]):
        found = True
        print(" ", r["id"], r["name"], "|", r["vers"])
if not found:
    print("  无 Anima 版本命中")
