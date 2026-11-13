# -*- coding: utf-8 -*-
"""按 Civitai model id 批量抓 Anima 版 LoRA（登录墙会 307，跳过并记档）。
用法: python anima_fetch_batch.py [id1,id2,...]
"""
import json, os, sys, time, urllib.request, urllib.error

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_TK = os.environ.get("CIVITAI_TOKEN", "").strip()
if _TK:
    UA["Authorization"] = "Bearer " + _TK
OUT = r"D:\ComfyUI\models\loras\Anima\packs"
LEDGER = r"D:\ComfyUI\logs\anima_fetch_batch.json"

IDS = [
    2651927,  # 美少女万华镜 16in1
    2983682,  # Happoubi Jin (八宝備仁)
    2967583,  # yuzusoft style v2
    2662404, 2662235,  # Yuzu Soft SD / CG
    2759648,  # Wada Arco
    2742720,  # ASK
    2735185,  # Pako
    2725640,  # Rurudo
    2647563,  # modare
    2632034,  # pottsness
    2970319,  # mignon
    2737482,  # Nixeu
    2240934,  # sakimichan
    2637182,  # wlop
    2701134,  # ogipote
    2724437,  # FKEY
    2770454,  # kantoku
    2631223,  # Incase [Anima]
    2909209,  # Afrobull
    16244,    # Harada Takehito
    2594289,  # Tony Taka 5in1
    2237877,  # Kanojo x Kanojo
    2010995,  # Moonlight Lady
    362766,   # Citron Secret Styles
    2629905,  # 米山舞 (MOSS/Krea2/Anima)
    1778443,  # Yoneyama lighting
    2768845,  # ArtistStyleMix 3
    2777283,  # Shindou Mitsuko
    457382, 461280,  # CutifiedAnimeCharacterDesign D/F
    586367,   # Touhou Alice PC-98
]


def slug(s):
    import re
    s = re.sub(r"[^0-9A-Za-z_\u4e00-\u9fff]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_")[:48].lower()


def main():
    ids = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else IDS
    os.makedirs(OUT, exist_ok=True)
    ledger = json.load(open(LEDGER, encoding="utf-8")) if os.path.exists(LEDGER) else {}
    for mid in ids:
        key = str(mid)
        if ledger.get(key, {}).get("status") == "ok":
            print("skip", mid, ledger[key]["file"], flush=True)
            continue
        try:
            d = json.loads(urllib.request.urlopen(
                urllib.request.Request("https://civitai.com/api/v1/models/%d" % mid, headers=UA), timeout=40).read().decode())
            av = [v for v in d.get("modelVersions", []) if v.get("baseModel") == "Anima"]
            if not av:
                ledger[key] = {"status": "no-anima"}
                print("no-anima", mid, d.get("name"), flush=True)
                continue
            v = av[0]
            f = [x for x in v["files"] if x.get("type") == "Model" and x.get("sizeKB", 0) > 10000][0]
            name = slug(v.get("name") or d.get("name")) or key
            dest = os.path.join(OUT, "%s_%s.safetensors" % (key, name))
            if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000:
                ledger[key] = {"status": "ok", "file": dest, "name": d.get("name"), "mb": os.path.getsize(dest) / 1048576}
                print("exists", mid, os.path.basename(dest), flush=True)
                continue
            r = urllib.request.urlopen(urllib.request.Request(v["downloadUrl"], headers=UA), timeout=600)
            with open(dest + ".part", "wb") as o:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    o.write(b)
            sz = os.path.getsize(dest + ".part")
            if sz < 1_000_000:
                os.remove(dest + ".part")
                raise RuntimeError("too small %d bytes (login wall?)" % sz)
            os.replace(dest + ".part", dest)
            ledger[key] = {"status": "ok", "file": dest, "name": d.get("name"), "ver": v.get("name"),
                           "mb": round(sz / 1048576, 1), "trig": (v.get("trainedWords") or [])[:3]}
            print("OK   %-9s %-46s %6.1fMB  trig=%s" % (mid, d.get("name")[:46], sz / 1048576,
                  (v.get("trainedWords") or [""])[0][:24]), flush=True)
        except urllib.error.HTTPError as e:
            ledger[key] = {"status": "http-%d" % e.code}
            print("HTTP %-9s %s" % (mid, e.code), flush=True)
        except Exception as e:
            ledger[key] = {"status": "err: %s" % e}
            print("ERR  %-9s %s" % (mid, str(e)[:120]), flush=True)
        json.dump(ledger, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(1)
    ok = [k for k, v in ledger.items() if v.get("status") == "ok"]
    print("\n成功 %d / 尝试 %d，落盘目录 %s" % (len(ok), len(ids), OUT))


if __name__ == "__main__":
    main()
