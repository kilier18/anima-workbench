# -*- coding: utf-8 -*-
"""扫描 AI 拟人角色相关的 Anima LoRA：正常比例 / chibi 迷你形态 / Claude 娘。"""
import json, os, time, urllib.request

TOKEN = open(os.path.expanduser("~/.dsh/civitai-token.txt"), encoding="utf-8").read().strip()
UA = {"User-Agent": "Mozilla/5.0", "Authorization": "Bearer " + TOKEN}
QUERIES = ["白龙娘", "chatgpt", "gpt girl", "claude", "claude girl", "deepseek", "鲸鱼娘",
           "chibi anima", "gijinka", "ai assistant girl", "anthropomorphic ai", "openai"]
OUT = r"D:\ComfyUI\logs\anima_musume_scan.json"


def api(u):
    for a in range(4):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode())
        except Exception as e:
            print("  retry", type(e).__name__, e)
            time.sleep(1.5 + a)
    return None


def main():
    seen, rows = set(), []
    for q in QUERIES:
        u = ("https://civitai.com/api/v1/models?limit=40&types=LORA&nsfw=true&query="
             + urllib.request.quote(q))
        d = api(u)
        if not d:
            print("FAIL", q)
            continue
        for m in d.get("items", []):
            mid = m["id"]
            if mid in seen:
                continue
            seen.add(mid)
            for v in m.get("modelVersions", [])[:3]:
                fs = [f for f in v.get("files", []) if f.get("type") == "Model" and f.get("sizeKB", 0) > 2000]
                if not fs:
                    continue
                rows.append({
                    "q": q, "id": mid, "name": m.get("name"), "ver": v.get("name"),
                    "base": v.get("baseModel"), "mb": round(fs[0]["sizeKB"] / 1024, 1),
                    "dl": m.get("stats", {}).get("downloadCount"), "likes": m.get("stats", {}).get("thumbsUpCount"),
                    "words": v.get("trainedWords") or [], "fid": fs[0].get("id"), "vid": v.get("id"),
                })
                break
        print("%-22s +%d (total %d)" % (q, len(d.get("items", [])), len(rows)), flush=True)
        time.sleep(1.2)

    ans = [r for r in rows if r["base"] == "Anima"]
    print("\n=== Anima 版本 %d 条 ===" % len(ans))
    for r in sorted(ans, key=lambda r: -(r["likes"] or 0)):
        print("  %-9s %-46s %-6s %6.1fMB dl=%-6s ♥%-5s %s" % (
            r["id"], (r["name"] or "")[:46], r["ver"][:6] if r["ver"] else "", r["mb"],
            r["dl"], r["likes"], (r["words"][0][:40] if r["words"] else "")))
    json.dump(rows, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n->", OUT, len(rows))


if __name__ == "__main__":
    main()
