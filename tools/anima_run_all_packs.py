# -*- coding: utf-8 -*-
"""批量跑 Anima 画风包：同一角色、同一 seed、同一写法，一批一目录，文件按画师 slug 命名。
用法: python anima_run_all_packs.py [batch名] [--ledger 路径] [--seed N] [--limit N] [--start N]
"""
import json, os, sys, time, urllib.request

API = "http://127.0.0.1:8188"
UNET = "Anima\\miaomiaoHarem_anima12.safetensors"
CLIP = "qwen_3_06b_base.safetensors"
VAE = "qwen_image_vae.safetensors"
TURBO = "Anima\\anima-turbo-lora-v0.2.safetensors"
LEDGER = r"D:\ComfyUI\logs\anima_fetch_batch.json"
OUT = r"D:\ComfyUI\_style_test"
W = "white background, simple background, looking at viewer, cowboy shot"
NEG = "worst quality, low quality, lowres, bad anatomy, bad hands, extra digits, watermark, signature"

FEAT = ("red eyes, light blue hair, short hair, short hair with long locks, bat wings, black bat wings, "
        "mob cap, pink mob cap, pink dress, red ribbon, ascot, frilled dress, puffy short sleeves, wrist cuffs")


def post(p, d):
    r = urllib.request.Request(API + p, data=json.dumps(d).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=60).read().decode())


def get(p):
    return json.loads(urllib.request.urlopen(API + p, timeout=60).read().decode())


def main():
    batch = "batch"
    seed = 777
    limit = None
    start = 0
    ledger_path = LEDGER
    for i, a in enumerate(sys.argv):
        if i == 1 and not a.startswith("--"):
            batch = a
        if a == "--seed":
            seed = int(sys.argv[i + 1])
        if a == "--limit":
            limit = int(sys.argv[i + 1])
        if a == "--start":
            start = int(sys.argv[i + 1])
        if a == "--ledger":
            ledger_path = sys.argv[i + 1]

    led = json.load(open(ledger_path, encoding="utf-8"))
    items = []
    for k, v in led.items():
        f = v.get("file", "")
        if not f.startswith("packs"):
            f = os.path.join(r"D:\ComfyUI\models\loras\Anima\packs", os.path.basename(f))
        else:
            f = os.path.join(r"D:\ComfyUI\models\loras\Anima", f)
        if not os.path.exists(f):
            continue
        items.append((k, v, f))
    items.sort(key=lambda kv: kv[1].get("mb", 0), reverse=True)
    items = items[start:]
    if limit:
        items = items[:limit]

    done = []
    for idx, (mid, v, path) in enumerate(items, 1):
        lora = "Anima\\packs\\" + os.path.basename(path)
        trig = v.get("trig") or []
        trig = ", ".join(trig[:2]) if isinstance(trig, list) else str(trig)
        text = ", ".join(x for x in ["1girl", "solo", "remilia scarlet", "touhou", trig, FEAT, W] if x)
        slug = v.get("slug") or os.path.splitext(os.path.basename(path))[0]
        pref = "%s/%s" % (batch, slug)
        wf = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
            "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "stable_diffusion", "device": "default"}},
            "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
            "10": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": text}},
            "11": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
            "12": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1536, "batch_size": 1}},
            "13": {"class_type": "KSampler", "inputs": {"model": ["21", 0], "positive": ["10", 0], "negative": ["11", 0],
                                                        "latent_image": ["12", 0], "seed": seed, "steps": 10, "cfg": 1.0,
                                                        "sampler_name": "er_sde", "scheduler": "beta", "denoise": 1.0}},
            "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["3", 0]}},
            "15": {"class_type": "SaveImage", "inputs": {"images": ["14", 0], "filename_prefix": pref}},
            "20": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": TURBO, "strength_model": 0.7}},
            "21": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["20", 0], "lora_name": lora, "strength_model": 1.0}},
        }
        try:
            pid = post("/prompt", {"prompt": wf, "client_id": "allpacks"})["prompt_id"]
        except Exception as e:
            print("REJECT %s %s" % (slug, str(e)[:150]), flush=True)
            continue
        t0 = time.time()
        ok = False
        while time.time() - t0 < 300:
            time.sleep(2)
            h = get("/history/" + pid)
            if pid in h and h[pid].get("status", {}).get("completed"):
                fn = [o["filename"] for o in h[pid]["outputs"]["15"]["images"]]
                print("ok %-24s %2.0fs %s" % (slug, time.time() - t0, v.get("label") or v.get("name", "")), flush=True)
                done.append({"idx": len(done) + 1, "tag": v.get("label") or v.get("name", ""), "slug": slug,
                             "count": 0, "file": batch + "/" + fn[0], "mid": mid})
                ok = True
                break
            if pid in h and h[pid].get("status", {}).get("status_str") == "error":
                print("ERR %s %s" % (slug, json.dumps(h[pid]["status"])[:160]), flush=True)
                break
        if not ok:
            print("TIMEOUT %s" % slug, flush=True)
    json.dump(done, open(r"D:\ComfyUI\logs\%s.json" % batch, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nTOTAL %d -> D:\\ComfyUI\\logs\\%s.json" % (len(done), batch))


if __name__ == "__main__":
    main()
