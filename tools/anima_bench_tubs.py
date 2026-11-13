# -*- coding: utf-8 -*-
"""画师桶分批扫描：ai-styles-dump 里 81 个画师桶，按训练图数降序固定编号 1..81。
每批 10 个，文件名 = 画师名，墙上标签 = "[编号] @画师名"。
角色每批轮换（东方，不重复）。
用法: python anima_bench_tubs.py --char sakuya --start 10 --limit 10 [--nsfw]
"""
import json, os, re, struct, sys, time, urllib.request, urllib.error

API = "http://127.0.0.1:8188"
UNET = "Anima\\miaomiaoHarem_anima12.safetensors"
CLIP = "qwen_3_06b_base.safetensors"
VAE = "qwen_image_vae.safetensors"
TURBO = "Anima\\anima-turbo-lora-v0.2.safetensors"
AINUM = "Anima\\ai-styles-dump-anima-v5.safetensors"
LORA_FILE = r"D:\ComfyUI\models\loras\Anima\ai-styles-dump-anima-v5.safetensors"
LEDGER = r"D:\ComfyUI\logs\tubs_ledger.json"
SEED = 868612345
NEG = "worst quality, low quality, lowres, bad anatomy, bad hands, extra digits, watermark, signature"

CHARS = {
    "reimu":     "hakurei reimu, brown eyes, brown hair, long hair, hair bow, hair tubes, red bow, detached sleeves, red skirt",
    "marisa":    "kirisame marisa, yellow eyes, blonde hair, long hair, side braid, witch hat, black dress, white apron",
    "sakuya":    "sakuya izayoi, blue eyes, silver hair, short hair, maid headdress, braid, maid outfit, white apron",
    "youmu":     "konpaku youmu, green eyes, short hair, silver hair, hair ribbon, green vest, white shirt",
    "reisen":    "reisen udongein inaba, red eyes, purple hair, long hair, rabbit ears, white shirt, red skirt",
    "sanae":     "kochiya sanae, green eyes, green hair, long hair, snake hair ornament, frog hair ornament, white shirt, blue skirt",
    "remilia":   "remilia scarlet, red eyes, light blue hair, short hair, bat wings, mob cap, pink dress",
    "flandre":   "flandre scarlet, red eyes, blonde hair, side ponytail, mob cap, red dress, crystal wings",
    "patchouli": "patchouli knowledge, purple eyes, purple hair, long hair, mob cap, striped dress, ribbon",
    "koishi":    "komeiji koishi, green eyes, green hair, short hair, third eye, black hat, closed eyes",
}

# 白底裸测：不写场景/光线/服装，只留构图骨架，让画师桶和底模先验自己说话
SFW = "white background, simple background, looking at viewer, cowboy shot"
NSFW = ("1boy, hetero, sex, penis in pussy, vaginal, lying on back, on bed, "
        "cowboy shot, looking at viewer, indoor, dim lighting, completely nude")


def slug(tag):
    s = tag.lstrip("@").strip()
    s = re.sub(r"[()]", "", s)
    s = re.sub(r"[^0-9A-Za-z_\u4e00-\u9fff]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_").lower()


def read_tubs():
    with open(LORA_FILE, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        h = json.loads(f.read(n).decode("utf-8"))
    tf = json.loads(h["__metadata__"]["ss_tag_frequency"])
    tubs = []
    for bucket in tf:
        for tag, cnt in tf[bucket].items():
            if tag.startswith("@"):
                tubs.append((tag, cnt, bucket))
    tubs.sort(key=lambda x: -x[1])
    out = []
    for i, (tag, cnt, bucket) in enumerate(tubs, 1):
        out.append({"idx": i, "tag": tag, "count": cnt, "bucket": bucket, "slug": slug(tag)})
    return out


def post(p, d):
    r = urllib.request.Request(API + p, data=json.dumps(d).encode(),
                               headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=60).read().decode())


def get(p):
    return json.loads(urllib.request.urlopen(API + p, timeout=60).read().decode())


def build(prefix, tag, char, scene):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "stable_diffusion", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "10": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": tag + ", touhou, 1girl, solo, " + char + ", " + scene}},
        "11": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
        "12": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1536, "batch_size": 1}},
        "13": {"class_type": "KSampler", "inputs": {"model": ["21", 0], "positive": ["10", 0], "negative": ["11", 0],
                                                    "latent_image": ["12", 0], "seed": SEED, "steps": 10, "cfg": 1.0,
                                                    "sampler_name": "er_sde", "scheduler": "beta", "denoise": 1.0}},
        "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["3", 0]}},
        "15": {"class_type": "SaveImage", "inputs": {"images": ["14", 0], "filename_prefix": prefix}},
        "20": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": TURBO, "strength_model": 0.7}},
        "21": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["20", 0], "lora_name": AINUM, "strength_model": 1.0}},
    }


def main():
    args = sys.argv[1:]
    nsfw = "--nsfw" in args
    char = "reimu"
    start, limit, batch = 0, 10, ""
    for i, a in enumerate(args):
        if a == "--char":
            char = args[i + 1]
        if a == "--start":
            start = int(args[i + 1])
        if a == "--limit":
            limit = int(args[i + 1])
        if a == "--batch":
            batch = args[i + 1]
    if char not in CHARS:
        print("UNKNOWN CHAR", char, list(CHARS))
        return
    tubs = read_tubs()[start:start + limit]
    print("角色=%s  共 %d 个画师桶  %s" % (char, len(tubs), "NSFW" if nsfw else "SFW"), flush=True)
    scene = NSFW if nsfw else SFW
    done = []
    for i, t in enumerate(tubs, 1):
        # 每批一个子目录，避免多批图混层导致合图错位
        prefix = "%s/%s" % (batch or ("tubsn" if nsfw else "tubs"), t["slug"])
        try:
            pid = post("/prompt", {"prompt": build(prefix, t["tag"], CHARS[char], scene), "client_id": "tubs"})["prompt_id"]
        except urllib.error.HTTPError as e:
            print("[%02d/%d] REJECT %s %s" % (i, len(tubs), t["slug"], e.read().decode()[:300]), flush=True)
            continue
        t0 = time.time()
        while time.time() - t0 < 600:
            time.sleep(2)
            h = get("/history/" + pid)
            if pid in h:
                st = h[pid].get("status", {})
                if st.get("completed"):
                    fn = [o.get("filename") for o in h[pid].get("outputs", {}).get("15", {}).get("images", [])]
                    print("[%02d/%d] %-3d %-30s %.0fs %s" % (i, len(tubs), t["idx"], t["tag"], time.time() - t0, fn), flush=True)
                    rec = dict(t)
                    rec.update({"file": (prefix.split("/")[0] + "/" + fn[0]) if fn else None, "char": char,
                                "scene": "nsfw" if nsfw else "sfw", "batch": batch})
                    done.append(rec)
                    break
                if st.get("status_str") == "error":
                    print("[%02d/%d] ERROR %s" % (i, len(tubs), json.dumps(st)[:300]), flush=True)
                    break
    ledger = json.load(open(LEDGER, encoding="utf-8")) if os.path.exists(LEDGER) else {}
    for r in done:
        ledger[str(r["idx"])] = r
    json.dump(ledger, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tag_ = "nsfw" if nsfw else "sfw"
    out = r"D:\ComfyUI\logs\tubs_%s_batch%s.json" % (tag_, batch or "x")
    json.dump(done, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("本批清单 -> %s  (%d 条)，总台账 %d 条" % (out, len(done), len(ledger)), flush=True)


if __name__ == "__main__":
    main()
