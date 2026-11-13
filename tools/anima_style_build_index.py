# -*- coding: utf-8 -*-
"""合并 Anima 画师库，检索目标画师，导出可直接喂给工作台的候选表。"""
import json, os, csv, re

ROOT = r"D:\ComfyUI\custom_nodes\comfyui-anima-style-nodes"
LORA = r"D:\ComfyUI\models\loras\Anima"
OUT = r"D:\ComfyUI\logs"
os.makedirs(OUT, exist_ok=True)

print("=== 插件根目录文件")
for n in sorted(os.listdir(ROOT)):
    p = os.path.join(ROOT, n)
    print("  %-34s %s" % (n, "dir" if os.path.isdir(p) else "%.1fKB" % (os.path.getsize(p) / 1024)))

with open(os.path.join(ROOT, "data", "artists.json"), encoding="utf-8") as f:
    base = json.load(f)
with open(os.path.join(ROOT, "data", "animadex_index.json"), encoding="utf-8") as f:
    amx = json.load(f)

rows = {}
for e in base:
    t = e["tag"]
    rows[t] = {"tag": t, "name": t, "works": e.get("works", 0), "score": e.get("uniqueness_score", 0),
               "kind": "artist", "source": "styles", "img": "", "has_image": False, "url": ""}
for e in amx:
    t = e.get("tag") or ""
    k = (t, e.get("source_kind", "artist"))
    if t in rows and e.get("source_kind", "artist") == "artist":
        rows[t]["img"] = e.get("img_url") or e.get("thumb_url") or ""
        rows[t]["thumb"] = e.get("thumb_url") or ""
        rows[t]["has_image"] = bool(e.get("has_image"))
        rows[t]["url"] = e.get("url") or ""
        rows[t]["amx_score"] = e.get("score", 0)
    elif t:
        rows["%s::%s" % (t, k[1])] = {"tag": t, "name": e.get("name", t), "works": e.get("works", 0),
                                      "score": e.get("uniqueness_score", 0), "kind": k[1], "source": "animadex",
                                      "img": e.get("img_url") or "", "thumb": e.get("thumb_url") or "",
                                      "has_image": bool(e.get("has_image")), "url": e.get("url") or ""}

print("\n=== 合并后条目: %d" % len(rows))
kinds = {}
for r in rows.values():
    kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
print("kind:", kinds)
have_img = sum(1 for r in rows.values() if r["has_image"])
print("has_image:", have_img)

csv_path = os.path.join(OUT, "anima_style_index.csv")
cols = ["tag", "name", "kind", "works", "score", "amx_score", "has_image", "img", "thumb", "url"]
with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in sorted(rows.values(), key=lambda x: -x.get("works", 0)):
        w.writerow(r)
print("CSV ->", csv_path, "%.1fMB" % (os.path.getsize(csv_path) / 1048576))

# 目标画师检索
targets = ["kanpa", "campagne", "hisahiko", "as109", "ebifurya", "belko", "sincos", "hammer",
           "tony taka", "kantoku", "iwao", "yoneyama", "d-art", "afrobull", "incase", "wlop",
           "ogipote", "nixeu", "sakimichan", "modare", "carnelian", "harada", "houtengeki",
           "ciloranko", "rurudo", "toosaka"]
print("\n=== 目标画师命中")
hit = []
for t in targets:
    ms = [(k, v) for k, v in rows.items() if t in k.lower()]
    ms.sort(key=lambda kv: -kv[1]["works"])
    print("%-12s hits=%d %s" % (t, len(ms), "; ".join("%s(w=%d,img=%s)" % (m[1]["tag"], m[1]["works"], m[1]["has_image"]) for m in ms[:3])))
    hit += [m[1] for m in ms[:3]]

# 清透向候选：高 works + 高 uniqueness（避免泛化），并给出预览图链接
print("\n=== 画师总数分布")
ART = [r for r in rows.values() if r["kind"] == "artist"]
ART.sort(key=lambda r: -r["works"])
print("artist count:", len(ART), " with img:", sum(1 for r in ART if r["has_image"]))
print("works>=1000:", sum(1 for r in ART if r["works"] >= 1000))

json.dump({"total": len(rows), "artists": len(ART), "with_image": have_img},
          open(os.path.join(OUT, "anima_style_index_meta.json"), "w", encoding="utf-8"))
