# -*- coding: utf-8 -*-
"""下载 animadex 画师预览缩略图 + 量化画风指标（亮度/对比/饱和），用于可计算的画风筛选。
用法:
  python anima_style_previews.py --tags "kanpa (campagne 9),hisahiko,..."
  python anima_style_previews.py --all --limit 2000 --workers 8
"""
import argparse, csv, io, json, os, sys, time
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from PIL import Image
except ImportError:
    Image = None

IDX = r"D:\ComfyUI\logs\anima_style_index.csv"
OUT = r"D:\ComfyUI\logs\anima_previews"
META = r"D:\ComfyUI\logs\anima_style_metrics.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
os.makedirs(OUT, exist_ok=True)


def safe(name):
    return "".join(c if c.isalnum() or c in "-_() " else "_" for c in name).strip()[:120]


def load_index():
    with open(IDX, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def metrics(path):
    """亮度 / 对比度(标准差) / 饱和度 —— 与文档 anima_pg_00203_ 判据同尺度(0-255)"""
    if Image is None:
        return None
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return None
    im.thumbnail((256, 256))
    px = list(im.getdata())
    n = len(px)
    lum = [(0.299 * r + 0.587 * g + 0.114 * b) for r, g, b in px]
    mean = sum(lum) / n
    var = sum((v - mean) ** 2 for v in lum) / n
    # HSV 饱和度均值
    import colorsys
    s = 0.0
    for r, g, b in px[::max(1, n // 4000)]:
        s += colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)[1]
    m = len(px[::max(1, n // 4000)])
    return {"lum": round(mean, 1), "contrast": round(var ** 0.5, 1), "sat": round(s / m * 255, 1)}


def fetch(row, force=False):
    tag = row["tag"]
    url = row.get("thumb") or row.get("img")
    if not url:
        return {"tag": tag, "status": "no-url"}
    dest = os.path.join(OUT, safe(tag) + ".webp")
    rec = {"tag": tag, "works": int(row.get("works") or 0), "score": float(row.get("score") or 0),
           "url": url, "file": dest}
    if os.path.exists(dest) and os.path.getsize(dest) > 1000 and not force:
        rec["status"] = "cached"
        rec.update(metrics(dest) or {})
        return rec
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if len(data) < 800:
            return {**rec, "status": "too-small"}
        with open(dest, "wb") as f:
            f.write(data)
        rec["status"] = "ok"
        rec["bytes"] = len(data)
        rec.update(metrics(dest) or {})
        return rec
    except Exception as e:
        return {**rec, "status": "err:%s" % e}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-works", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    rows = load_index()
    rows = [r for r in rows if r["kind"] == "artist" and (r.get("thumb") or r.get("img"))]
    if a.tags:
        want = [t.strip().lower() for t in a.tags.split(",") if t.strip()]
        rows = [r for r in rows if any(w in r["tag"].lower() for w in want)]
    if a.min_works:
        rows = [r for r in rows if int(r.get("works") or 0) >= a.min_works]
    rows.sort(key=lambda r: -int(r.get("works") or 0))
    if a.limit:
        rows = rows[:a.limit]
    print("targets:", len(rows))

    results = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(fetch, r, a.force): r for r in rows}
        for i, fu in enumerate(as_completed(futs), 1):
            rec = fu.result()
            results.append(rec)
            if i % 50 == 0 or i == len(rows):
                ok = sum(1 for x in results if x.get("status") in ("ok", "cached"))
                print("  %d/%d ok=%d %.0fs" % (i, len(rows), ok, time.time() - t0))
    results.sort(key=lambda x: -x.get("works", 0))

    old = []
    if os.path.exists(META):
        try:
            old = json.load(open(META, encoding="utf-8"))
        except Exception:
            old = []
    by_tag = {x["tag"]: x for x in (old if isinstance(old, list) else [])}
    for r in results:
        by_tag[r["tag"]] = r
    json.dump(list(by_tag.values()), open(META, "w", encoding="utf-8"), ensure_ascii=False)
    print("META ->", META, "records=%d" % len(by_tag))


if __name__ == "__main__":
    main()
