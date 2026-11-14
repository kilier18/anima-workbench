# -*- coding: utf-8 -*-
"""自由角色跑图（不限于东方）：python anima_run_char.py <batch> <slug> "<prompt>" [--seed N] [--lora 文件|权重|触发词]"""
import json, sys, time, urllib.request, urllib.error

API = "http://127.0.0.1:8188"
UNET = "Anima\\miaomiaoHarem_anima12.safetensors"
CLIP = "qwen_3_06b_base.safetensors"
VAE = "qwen_image_vae.safetensors"
TURBO = "Anima\\anima-turbo-lora-v0.2.safetensors"
NEG = "worst quality, low quality, lowres, bad anatomy, bad hands, extra digits, watermark, signature"
WHITE = "white background, simple background, looking at viewer"


def post(p, d):
    r = urllib.request.Request(API + p, data=json.dumps(d).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=60).read().decode())


def get(p):
    return json.loads(urllib.request.urlopen(API + p, timeout=60).read().decode())


def main():
    batch, slug, text = sys.argv[1], sys.argv[2], sys.argv[3]
    seed, extra = 20251113, None
    if "--seed" in sys.argv:
        seed = int(sys.argv[sys.argv.index("--seed") + 1])
    if "--lora" in sys.argv:
        # 支持多 LoRA："A.safetensors|0.6;B.safetensors|0.6"（分号分隔，链式挂）
        extra = [s for s in sys.argv[sys.argv.index("--lora") + 1].split(";") if s.strip()]
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "stable_diffusion", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "10": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": text}},
        "11": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
        "12": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1536, "batch_size": 1}},
        "13": {"class_type": "KSampler", "inputs": {"model": ["20", 0], "positive": ["10", 0], "negative": ["11", 0],
                                                    "latent_image": ["12", 0], "seed": seed, "steps": 10, "cfg": 1.0,
                                                    "sampler_name": "er_sde", "scheduler": "beta", "denoise": 1.0}},
        "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["3", 0]}},
        "15": {"class_type": "SaveImage", "inputs": {"images": ["14", 0], "filename_prefix": (batch + "/" + slug)[:72]}},
        "20": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": TURBO, "strength_model": 0.7}},
    }
    prev = "20"
    for i, spec in enumerate(extra or []):
        pr = spec.split("|")
        if not pr[0].strip():
            continue
        nid = str(21 + i)
        wf[nid] = {"class_type": "LoraLoaderModelOnly",
                   "inputs": {"model": [prev, 0], "lora_name": pr[0].strip(),
                              "strength_model": float(pr[1]) if len(pr) > 1 and pr[1].strip() else 1.0}}
        prev = nid
    if prev != "20":
        wf["13"]["inputs"]["model"] = [prev, 0]
    pid = post("/prompt", {"prompt": wf, "client_id": "runchar"})["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < 600:
        time.sleep(2)
        h = get("/history/" + pid)
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("completed"):
                fn = [o.get("filename") for o in h[pid].get("outputs", {}).get("15", {}).get("images", [])]
                print("ok %-24s %.0fs %s" % (slug, time.time() - t0, fn))
                json.dump({"batch": batch, "slug": slug, "file": (batch + "/" + fn[0]) if fn else None,
                           "prompt": text}, open(r"D:\ComfyUI\logs\%s_%s.json" % (batch, slug), "w", encoding="utf-8"),
                          ensure_ascii=False, indent=1)
                return
            if st.get("status_str") == "error":
                print("ERROR", json.dumps(st)[:400])
                return
    print("TIMEOUT", slug)


if __name__ == "__main__":
    main()
