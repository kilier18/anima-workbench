# -*- coding: utf-8 -*-
"""体检 v2：不跟随 302，逐项宽松超时。"""
import io, json, os, subprocess, sys, urllib.request, urllib.error

_PORT = os.environ.get("ASSISTANT_PORT", "8190")
A = os.environ.get("WORKBENCH_URL") or ("http://127.0.0.1:" + _PORT)
C = os.environ.get("COMFY_API", "http://127.0.0.1:8188")
P = os.environ.get("PROXY_URL", "http://127.0.0.1:8199")
rows = []

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener = urllib.request.build_opener(NoRedirect)

def req(url, data=None, timeout=20, ctype="application/json"):
    r = urllib.request.Request(url, data=data, headers={"Content-Type": ctype} if data else {})
    try:
        with opener.open(r, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b""
    except Exception as e:
        return "ERR:" + str(e)[:60], b""

def chk(name, url, expect=(200,), data=None, timeout=20):
    st, body = req(url, data=data, timeout=timeout)
    rows.append((st in expect, name, st, len(body), body[:90].decode("utf-8", "ignore")))

chk("主页 /", A + "/")
chk("教程 /guide", A + "/guide")
for p in ("/anima", "/wb", "/lib", "/assistant", "/tool", "/old", "/workbench", "/studio", "/wardrobe"):
    chk("旧页 302 " + p, A + p, (302,))
for f in ("wb_tags.json", "wb_chars.json", "wb_scenes.json", "wb_presets.json", "wb_zh.json", "wb_pools.json"):
    chk("data " + f, A + "/data/" + f)
chk("缩略图代理", A + "/anima-wardrobe-v5/thumb/hakurei_reimu")
chk("ComfyUI 8188", C + "/system_stats")
chk("代理 8199", P + "/system_stats")
chk("插件 health", C + "/anima-wardrobe-v5/health")
chk("POST /api/expand", A + "/api/expand", (200,), json.dumps({"text": "灵梦 后入 吐舌头 全身"}).encode(), timeout=60)
chk("GET /api/gen/job 未知 id", A + "/api/gen/job?id=deadbeef", (200,))
chk("GET /api/wb/zh", A + "/api/wb/zh", (200,))
chk("GET /api/wb/char", A + "/api/wb/char?tag=hakurei_reimu", (200,))
chk("GET /api/wb/scene", A + "/api/wb/scene?id=sc_rain_street_lookback", (200,))
chk("404 兜底", A + "/nope-not-exist", (404,))

D = r"D:\ComfyUI\webui\data"
stats = {}
try:
    stats["zh"] = len(json.load(io.open(os.path.join(D, "wb_zh.json"), encoding="utf-8")))
    stats["tags"] = sum(len(c["tags"]) for c in json.load(io.open(os.path.join(D, "wb_tags.json"), encoding="utf-8"))["cats"])
    stats["chars"] = len(json.load(io.open(os.path.join(D, "wb_chars.json"), encoding="utf-8"))["chars"])
    sc = json.load(io.open(os.path.join(D, "wb_scenes.json"), encoding="utf-8"))
    stats["scenes"] = "%d" % len(sc["anima"])
    pr = json.load(io.open(os.path.join(D, "wb_presets.json"), encoding="utf-8"))
    _n = len(pr["forge"]) + len(pr.get("anima") or [])
    stats["presets"] = "%d(%d+%d)" % (_n, len(pr["forge"]), len(pr.get("anima") or []))
except Exception as e:
    stats["err"] = str(e)

TH = r"D:\ComfyUI\ComfyUI_windows_portable\ComfyUI\custom_nodes\Comfyui-Anima-Wardrobe-V5\presets\thumbs"
stats["thumbs"] = len([f for f in os.listdir(TH) if f.endswith(".webp")]) if os.path.isdir(TH) else 0

rc = subprocess.run([sys.executable, "-m", "py_compile", r"D:\ComfyUI\webui\assistant.py"], capture_output=True)
rows.append((rc.returncode == 0, "py_compile assistant.py", rc.returncode, 0, ""))

for ok, name, st, n, extra in rows:
    print(("OK  " if ok else "FAIL"), "%-28s" % name, st, n, extra if not ok else "")
print("---")
print("统计", json.dumps(stats, ensure_ascii=False))
print("失败", sum(1 for r in rows if not r[0]), "/", len(rows))
