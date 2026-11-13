# -*- coding: utf-8 -*-
"""单点跑图：指定 LoRA 文件 + 触发词 + 角色，白底裸测。
用法: python anima_run_pack.py <batch名> <角色key> "lora文件|强度|触发词;lora2|强度|触发词..."
"""
import json, sys, time, urllib.request, urllib.error

API = "http://127.0.0.1:8188"
UNET = "Anima\\miaomiaoHarem_anima12.safetensors"
CLIP = "qwen_3_06b_base.safetensors"
VAE = "qwen_image_vae.safetensors"
TURBO = "Anima\\anima-turbo-lora-v0.2.safetensors"
SEED = 868612345
NEG = "worst quality, low quality, lowres, bad anatomy, bad hands, extra digits, watermark, signature"
WHITE = "white background, simple background, looking at viewer, cowboy shot"

CHARS = {
    "reimu":  "hakurei reimu, brown eyes, brown hair, long hair, hair bow, hair tubes, red bow, detached sleeves, red skirt",
    "sakuya": "sakuya izayoi, blue eyes, silver hair, short hair, maid headdress, braid, maid outfit, white apron",
    "youmu":  "konpaku youmu, green eyes, short hair, silver hair, hair ribbon, green vest, white shirt",
    "reisen": "reisen udongein inaba, red eyes, purple hair, long hair, rabbit ears, white shirt, red skirt",
    "sanae":  "kochiya sanae, green eyes, green hair, long hair, snake hair ornament, frog hair ornament, white shirt, blue skirt",
    "koishi": "komeiji koishi, green eyes, green hair, short hair, third eye, black hat, closed eyes",
    "cirno":  "cirno, blue eyes, blue hair, short hair, hair ribbon, blue dress, wings",
    "yuyuko": "saigyouji yuyuko, pink eyes, pink hair, short hair, mob cap, kimono",
    "marisa": "kirisame marisa, yellow eyes, blonde hair, long hair, side braid, witch hat, black dress, white apron",
    "remilia": "remilia scarlet, red eyes, light blue hair, short hair, short hair with long locks, bat wings, black bat wings, mob cap, pink mob cap, pink dress, red ribbon, ascot, frilled dress, puffy short sleeves, wrist cuffs",
    "flandre": "flandre scarlet, red eyes, blonde hair, side ponytail, crystal wings, mob cap, red dress, red ribbon, frilled dress",
    "patchouli": "patchouli knowledge, purple eyes, purple hair, long hair, mob cap, striped dress, ribbon, frilled dress",
    "alice": "alice margatroid, blue eyes, blonde hair, short hair, hair ribbon, white shirt, blue dress",
    "satori": "komeiji satori, red eyes, pink hair, short hair, third eye, hair ribbon, blue dress",
    "utils": "kazami yuuka, red eyes, green hair, short hair, hair ribbon, plaid vest, long skirt",
}


def post(p, d):
    r = urllib.request.Request(API + p, data=json.dumps(d).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=60).read().decode())


def get(p):
    return json.loads(urllib.request.urlopen(API + p, timeout=60).read().decode())


def main():
    global SEED
    batch, char, spec = sys.argv[1], sys.argv[2], sys.argv[3]
    if char not in CHARS:
        # 角色名缺失会让 prompt 里只剩 touhou，模型自由发挥 → 出别的东方角色
        raise SystemExit("CHARS 缺角色 '%s'，现有: %s" % (char, ", ".join(sorted(CHARS))))
    for i, a in enumerate(sys.argv):
        if a == "--seed":
            SEED = int(sys.argv[i + 1])
    items = []
    for blk in spec.split(";"):
        parts = blk.split("|")
        lora = parts[0]
        w = float(parts[1]) if len(parts) > 1 and parts[1] else 1.0
        trig = parts[2] if len(parts) > 2 else ""
        items.append((lora, w, trig))
    done = []
    for lora, w, trig in items:
        # 每批一个子目录，避免多批图混在同一层导致合图错位
        prefix = (batch + "/" + lora.split("\\")[-1].replace(".safetensors", ""))[:72]
        text = ", ".join(x for x in [trig, "touhou", "1girl", "solo", CHARS.get(char, ""), WHITE] if x)
        wf = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
            "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "stable_diffusion", "device": "default"}},
            "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
            "10": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": text}},
            "11": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
            "12": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1536, "batch_size": 1}},
            "13": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["10", 0], "negative": ["11", 0],
                                                        "latent_image": ["12", 0], "seed": SEED, "steps": 10, "cfg": 1.0,
                                                        "sampler_name": "er_sde", "scheduler": "beta", "denoise": 1.0}},
            "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["3", 0]}},
            "15": {"class_type": "SaveImage", "inputs": {"images": ["14", 0], "filename_prefix": prefix}},
            "20": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": TURBO, "strength_model": 0.7}},
        }
        prev = ["20", 0]
        # 除 turbo 外的所有 LoRA 依次挂
        if not lora.startswith("Anima\\anima-turbo"):
            wf["21"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": prev, "lora_name": lora, "strength_model": w}}
            prev = ["21", 0]
        wf["13"]["inputs"]["model"] = prev
        try:
            pid = post("/prompt", {"prompt": wf, "client_id": "runone"})["prompt_id"]
        except urllib.error.HTTPError as e:
            print("REJECT", lora, e.read().decode()[:300], flush=True)
            continue
        t0 = time.time()
        while time.time() - t0 < 600:
            time.sleep(2)
            h = get("/history/" + pid)
            if pid in h:
                st = h[pid].get("status", {})
                if st.get("completed"):
                    fn = [o.get("filename") for o in h[pid].get("outputs", {}).get("15", {}).get("images", [])]
                    print("ok %-42s %.0fs %s" % (lora[-42:], time.time() - t0, fn), flush=True)
                    done.append({"idx": len(done) + 1, "tag": trig or lora.split("\\")[-1][:20], "count": 0,
                                 "slug": lora, "file": (batch + "/" + fn[0]) if fn else None,
                                 "char": char, "scene": "white", "batch": batch})
                    break
                if st.get("status_str") == "error":
                    print("ERROR", json.dumps(st)[:300], flush=True)
                    break
    json.dump(done, open(r"D:\ComfyUI\logs\%s.json" % batch, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("-> %s.json (%d)" % (batch, len(done)))


if __name__ == "__main__":
    main()
