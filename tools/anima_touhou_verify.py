# -*- coding: utf-8 -*-
"""核对画风包是否「东方画师」（判定放宽：画过东方即可）。
证据源：Civitai 模型详情（作者自述 description + tags）。tags 可能是 str 数组也可能是对象数组，两种都兼容。
"""
import json, os, re, time, urllib.request

STYLES = r"D:\ComfyUI\webui\data\anima_styles.json"
OUT = r"D:\ComfyUI\logs\touhou_verify.json"
TOKEN = open(os.path.expanduser(r"~\.dsh\civitai-token.txt"), encoding="utf-8").read().strip()

TOUHOU = re.compile(
    r"(touhou|toho|東方|东方|とうほう|幻想郷|幻想乡|gensokyo|hakurei|reimu|marisa|kirisame|"
    r"sakuya|izayoi|youmu|konpaku|reisen|sanae|kochiya|remilia|flandre|scarlet|patchouli|"
    r"knowledge|cirno|koishi|satori|komeiji|suwako|kanako|aya ?shameimaru|youkai|yakumo|"
    r"kaguya|mokou|tenshi|utsuho|orin|yuuka|komachi|eiki|byakuren|miko|seija|kasen|"
    r"alice ?margatroid|nitori|momiji|hatate|suika|yuugi|parsee|yamame|kisume|rumia|"
    r"daiyousei|letty|chen|ran|yukari|keine|tewi|mystia|wriggle|medicine|eirin|kaguya|"
    r"aya|komachi|shikieiki|yuyuko|saigyouji|youmu|ran|sakuya)",
    re.I)


def api(url):
    r = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Authorization": "Bearer " + TOKEN})
    with urllib.request.urlopen(r, timeout=60) as x:
        return json.loads(x.read().decode("utf-8"))


def flat_tags(m):
    out = []
    for t in (m.get("tags") or []):
        if isinstance(t, dict):
            out.append(str(t.get("name") or ""))
        else:
            out.append(str(t))
    return [x for x in out if x]


def model_id(s):
    m = re.search(r"civitai:(\d+)", str(s.get("src") or ""))
    if m:
        return m.group(1)
    sid = str(s.get("id") or "")
    return sid if sid.isdigit() else None


def main():
    d = json.load(open(STYLES, encoding="utf-8"))
    rows, cache = [], {}
    for s in d["styles"]:
        if s.get("verdict") != "keep":
            continue
        mid = model_id(s)
        r = {"id": s["id"], "zh": s.get("zh"), "group": s.get("group"),
             "flagged": bool(s.get("touhou_artist")), "mid": mid, "hits": [], "err": None,
             "name": None, "tags": []}
        if not mid:
            r["err"] = "no-model-id"
            rows.append(r); continue
        try:
            if mid not in cache:
                cache[mid] = api("https://civitai.com/api/v1/models/" + mid)
                time.sleep(0.6)
            m = cache[mid]
            r["name"] = m.get("name")
            r["tags"] = flat_tags(m)[:15]
            blob = " ".join([m.get("name") or "", m.get("description") or "", " ".join(flat_tags(m))])
            r["hits"] = sorted(set(x.lower() for x in TOUHOU.findall(blob)))[:8]
        except Exception as e:
            r["err"] = str(e)[:70]
        rows.append(r)
    json.dump(rows, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    hit = [r for r in rows if r["hits"]]
    miss = [r for r in rows if not r["hits"] and not r["err"]]
    err = [r for r in rows if r["err"]]
    print("keep=%d | 有东方证据=%d | 无=%d | 取不到=%d\n" % (len(rows), len(hit), len(miss), len(err)))
    print("=== 有东方证据（建议标东方画师）===")
    for r in hit:
        print("%-22s %-26s grp=%-12s flag=%-2s %s" % (
            r["id"][:22], (r["zh"] or "")[:26], r["group"], "Y" if r["flagged"] else "-", ",".join(r["hits"][:5])))
    print("\n=== 标了东方但无证据（建议复核/撤销）===")
    for r in rows:
        if r["flagged"] and not r["hits"]:
            print("%-22s %-26s grp=%-12s %s" % (r["id"][:22], (r["zh"] or "")[:26], r["group"], r["err"] or ""))
    print("\n=== 无证据且未标（正常非东方）%d 条 ===" % len([r for r in miss if not r["flagged"]]))
    for r in err[:10]:
        print("  ERR %-20s %s" % (r["id"][:20], r["err"]))
    print("\nOUT", OUT)


if __name__ == "__main__":
    main()
