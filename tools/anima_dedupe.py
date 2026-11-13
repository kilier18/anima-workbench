# -*- coding: utf-8 -*-
"""画风库去重 + 东方简单归类。
规则：同一画师的多个版本只留最优（训练图数优先，其次文件体积）；touhou_artist=True 的统一归到「东方画师」组。
"""
import json, os, struct

STYLES = r"D:\ComfyUI\webui\data\anima_styles.json"
PACKS = r"D:\ComfyUI\models\loras\Anima"
REPORT = r"D:\ComfyUI\logs\dedupe_report.json"

# 同画师重复组（人工确认过的）
GROUPS = [
    ("米山舞", ["p5_29", "p5_30"]),
    ("柚子社", ["p5_19", "p5_20", "p5_23"]),
    ("毛玉牛乳", ["2624534", "2648265"]),
    ("Nunyu", ["2715280", "1685523"]),
    ("Onineko", ["2317290", "2655807"]),
    ("Takamichi", ["2842118", "1423180"]),
]

# 显示名冲突（不同文件但要区分）
RENAME = {
    "p5_24": "Cutified 变体 D",
    "p5_25": "Cutified 变体 F",
}


def header(path):
    try:
        with open(path, "rb") as f:
            n = struct.unpack("<Q", f.read(8))[0]
            if n <= 0 or n > 64 * 1024 * 1024:
                return {}
            return json.loads(f.read(n).decode("utf-8")).get("__metadata__", {}) or {}
    except Exception:
        return {}


def main():
    d = json.load(open(STYLES, encoding="utf-8"))
    by_id = {s["id"]: s for s in d["styles"]}
    cache = {}

    def info(sid):
        s = by_id[sid]
        lora = (s.get("lora") or "").replace("Anima\\", "").replace("Anima/", "")
        p = os.path.join(PACKS, lora.replace("packs\\", "packs\\").replace("packs/", "packs/"))
        if p not in cache:
            meta = header(p) if os.path.exists(p) else {}
            try:
                imgs = int(meta.get("ss_num_train_images") or 0)
            except Exception:
                imgs = 0
            cache[p] = {"imgs": imgs, "mb": os.path.getsize(p) / 1048576 if os.path.exists(p) else 0,
                        "exists": os.path.exists(p)}
        return cache[p]

    decisions = []
    for name, ids in GROUPS:
        rows = []
        for sid in ids:
            if sid not in by_id:
                continue
            i = info(sid)
            rows.append((sid, by_id[sid].get("zh"), i["imgs"], round(i["mb"], 1), i["exists"]))
        rows.sort(key=lambda r: (-r[2], -r[3]))
        keep = rows[0][0] if rows else None
        for r in rows:
            decisions.append({"group": name, "id": r[0], "zh": r[1], "imgs": r[2],
                              "mb": r[3], "exists": r[4], "verdict": "keep" if r[0] == keep else "drop"})

    dropped = 0
    for dv in decisions:
        s = by_id[dv["id"]]
        s["verdict"] = dv["verdict"]
        if dv["verdict"] == "drop":
            dropped += 1
            s["dup_of"] = dv["group"]

    for sid, nm in RENAME.items():
        if sid in by_id:
            by_id[sid]["zh"] = nm

    moved = 0
    for s in d["styles"]:
        if s.get("verdict") == "keep" and s.get("touhou_artist") and s.get("group") != "东方画师":
            s["group"] = "东方画师"
            moved += 1

    d["version"] = int(d.get("version") or 0) + 1
    json.dump(d, open(STYLES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    keep = [s for s in d["styles"] if s.get("verdict") == "keep"]
    import collections
    print("keep=%d  drop=%d  (本轮新 drop %d, 移动分组 %d)" % (
        len(keep), len(d["styles"]) - len(keep), dropped, moved))
    print(collections.Counter(s.get("group") for s in keep))
    print("\n=== 去重决策 ===")
    for dv in decisions:
        print("%-10s %-10s %-26s imgs=%-5s %5.1fMB  %s" % (
            dv["group"], dv["id"], (dv["zh"] or "")[:26], dv["imgs"], dv["mb"], dv["verdict"].upper()))
    print("\n=== 东方画师 %d 条 ===" % len([s for s in keep if s.get("touhou_artist")]))
    for s in keep:
        if s.get("touhou_artist"):
            print("   %-22s %s" % (s["id"][:22], (s.get("zh") or "")[:30]))
    json.dump({"decisions": decisions, "dropped": dropped, "moved": moved},
              open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
