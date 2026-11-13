# -*- coding: utf-8 -*-
"""抓 Civitai 全量 Anima LoRA 排行（cursor 分页），存 anima_all_rank.json。"""
import json, os, time, urllib.parse, urllib.request

OUT = r"D:\ComfyUI\logs\anima_all_rank.json"
tk = open(os.path.expanduser("~/.dsh/civitai-token.txt"), encoding="utf-8").read().strip()


def get(u, tries=4):
    for a in range(tries):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Authorization": "Bearer " + tk})
            return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
        except Exception as e:
            print("retry", a, e)
            time.sleep(3)
    return None


def tags_of(m):
    out = []
    for t in (m.get("tags") or []):
        if isinstance(t, str):
            out.append(t)
        elif isinstance(t, dict):
            out.append(t.get("name", ""))
    return out[:8]


def main():
    rows = {}
    u = "https://civitai.com/api/v1/models?baseModels=Anima&types=LORA&limit=100"
    pages = 0
    while u and pages < 20:
        d = get(u)
        if not d:
            break
        its = d.get("items", [])
        if not its:
            break
        for m in its:
            vid = str(m["id"])
            if vid in rows:
                continue
            vs = [v for v in m.get("modelVersions", []) if v.get("baseModel") == "Anima"]
            if not vs:
                continue
            v = max(vs, key=lambda x: x.get("publishedAt", ""))
            fs = [f for f in v.get("files", []) if f.get("type") == "Model" and f.get("sizeKB", 0) > 10000]
            if not fs:
                continue
            rows[vid] = {
                "id": m["id"], "name": m.get("name", ""), "ver": v.get("name", ""),
                "mb": round(fs[0].get("sizeKB", 0) / 1024, 1),
                "dl": (m.get("stats") or {}).get("downloadCount", 0),
                "trig": (v.get("trainedWords") or [])[:4],
                "tags": tags_of(m),
            }
        pages += 1
        nxt = (d.get("metadata") or {}).get("nextCursor")
        print("page%-2d +%-3d total=%d" % (pages, len(its), len(rows)), flush=True)
        u = ("https://civitai.com/api/v1/models?baseModels=Anima&types=LORA&limit=100&cursor="
             + urllib.parse.quote(nxt)) if nxt else None
        time.sleep(1.2)
    json.dump(list(rows.values()), open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("SAVED", len(rows), "->", OUT)


if __name__ == "__main__":
    main()
