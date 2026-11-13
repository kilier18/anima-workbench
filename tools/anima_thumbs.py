# -*- coding: utf-8 -*-
"""给每个保留的画风包跑一张固定角色半身图，作工作台缩略图。
输出 D:\ComfyUI\webui\static\style_thumbs\<id>.jpg （宽 512）
清单 D:\ComfyUI\logs\style_thumbs.json
用法: python anima_thumbs.py [--start N] [--limit N] [--only id,id]
"""
import json, os, sys, time, urllib.request, urllib.error

COMFY = "http://127.0.0.1:8188"
STYLES = r"D:\ComfyUI\webui\data\anima_styles.json"
OUTDIR = r"D:\ComfyUI\webui\static\style_thumbs"
LED = r"D:\ComfyUI\logs\style_thumbs.json"

UNET = "Anima\\miaomiaoHarem_anima12.safetensors"
CLIP = "qwen_3_06b_base.safetensors"
VAE = "qwen_image_vae.safetensors"
TURBO = "Anima\\anima-turbo-lora-v0.2.safetensors"

CHAR = ("remilia scarlet, touhou, 1girl, solo, upper body, portrait, "
        "red eyes, light blue hair, short hair, short hair with long locks, bat wings, black bat wings, "
        "mob cap, pink mob cap, pink dress, red ribbon, ascot, frilled dress, puffy short sleeves, wrist cuffs")
TAIL = "white background, simple background, looking at viewer"
NEG = "lowres, bad anatomy, bad hands, extra digits, watermark, signature, text"


def post(path, obj):
    req = urllib.request.Request(COMFY + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())


def get(path):
    return json.loads(urllib.request.urlopen(COMFY + path, timeout=60).read().decode())


def build(lora, trig, seed):
    text = ", ".join(x for x in [CHAR, trig, TAIL] if x)
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
        "15": {"class_type": "SaveImage", "inputs": {"images": ["14", 0], "filename_prefix": "thumbs/" + os.path.basename(lora).replace(".safetensors", "")}},
        "20": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": TURBO, "strength_model": 0.7}},
        "21": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["20", 0], "lora_name": lora, "strength_model": 1.0}},
    }
    return wf


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    d = json.load(open(STYLES, encoding="utf-8"))
    keep = [x for x in d["styles"] if x.get("verdict") == "keep" and x.get("on_disk")]
    only = None
    for i, a in enumerate(sys.argv):
        if a == "--only":
            only = set(sys.argv[i + 1].split(","))
    if only:
        keep = [x for x in keep if x["id"] in only]
    start = 0
    limit = 999
    for i, a in enumerate(sys.argv):
        if a == "--start":
            start = int(sys.argv[i + 1])
        if a == "--limit":
            limit = int(sys.argv[i + 1])
    keep = keep[start:start + limit]
    led = json.load(open(LED, encoding="utf-8")) if os.path.exists(LED) else {}
    for n, s in enumerate(keep, 1):
        sid = s["id"]
        jpg = os.path.join(OUTDIR, sid + ".jpg")
        if os.path.exists(jpg):
            print("skip %-14s %s" % (sid, s["zh"][:34]), flush=True)
            continue
        lora = s["lora"]
        trig = s.get("trig")
        if isinstance(trig, list):
            trig = trig[0] if trig else ""
        trig = (trig or "").split(" / ")[0].strip()
        seed = 777 + (abs(hash(sid)) % 100000)
        try:
            pid = post("/prompt", {"prompt": build(lora, trig, seed), "client_id": "thumbs"})["prompt_id"]
        except urllib.error.HTTPError as e:
            print("REJECT %-14s %s" % (sid, e.read().decode()[:220]), flush=True)
            continue
        t0 = time.time()
        while time.time() - t0 < 300:
            time.sleep(2)
            h = get("/history/" + pid)
            if pid in h:
                break
        else:
            print("TIMEOUT %s" % sid, flush=True)
            continue
        outs = h[pid]["outputs"]
        imgs = [v for k in outs for v in outs[k].get("images", [])]
        if not imgs:
            print("NOIMG %s" % sid, flush=True)
            continue
        src = os.path.join(r"D:\ComfyUI\_style_test", imgs[0]["subfolder"], imgs[0]["filename"])
        try:
            from PIL import Image
            im = Image.open(src).convert("RGB")
            im.thumbnail((512, 768), Image.LANCZOS)
            im.save(jpg, "JPEG", quality=86, optimize=True)
        except Exception as e:
            print("IMGERR %s %s" % (sid, e), flush=True)
            continue
        led[sid] = {"jpg": sid + ".jpg", "zh": s["zh"], "trig": trig, "mb": s["mb"],
                    "group": s.get("group"), "touhou": s.get("touhou_artist"), "lora": lora}
        json.dump(led, open(LED, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("ok %-14s %5.1fs %s" % (sid, time.time() - t0, s["zh"][:36]), flush=True)
    print("\nDONE %d thumbs -> %s" % (len(led), OUTDIR))


if __name__ == "__main__":
    main()
