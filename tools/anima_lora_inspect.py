# -*- coding: utf-8 -*-
"""解析已下载 Anima LoRA 的 safetensors 头部：键构成（unet/te 比例）、dim/alpha、训练 tag 频率。"""
import json, os, struct, sys

LORA_DIR = r"D:\ComfyUI\models\loras\Anima"


def load_header(path):
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        return json.loads(f.read(n).decode("utf-8"))


def summarize(path):
    h = load_header(path)
    meta = h.pop("__metadata__", {}) or {}
    unet = [k for k in h if k.startswith("lora_unet_")]
    te = [k for k in h if k.startswith("lora_te_")]
    other = [k for k in h if k not in unet and k not in te]
    alphas = {}
    dims = {}
    for k, v in h.items():
        if k.endswith("alpha"):
            val = v if isinstance(v, (int, float)) else "?"
            alphas[val] = alphas.get(val, 0) + 1
        if k.endswith("lora_down.weight"):
            d = v.get("shape", []) if isinstance(v, dict) else []
            key = d[0] if len(d) == 2 else (d[0] if d else "?")
            dims[key] = dims.get(key, 0) + 1
    out = {
        "file": os.path.basename(path),
        "mb": round(os.path.getsize(path) / 1048576, 1),
        "unet_tensors": len(unet),
        "te_tensors": len(te),
        "other_tensors": len(other),
        "other_sample": other[:3],
        "alphas": alphas,
        "dims": dims,
        "ss_base_model_version": meta.get("ss_base_model_version"),
        "ss_network_dim": meta.get("ss_network_dim"),
        "ss_network_alpha": meta.get("ss_network_alpha"),
        "ss_num_train_images": meta.get("ss_num_train_images"),
        "ss_resolution": meta.get("ss_resolution"),
        "ss_output_name": meta.get("ss_output_name"),
        "modelspec_title": meta.get("modelspec.title"),
        "modelspec_arch": meta.get("modelspec.architecture"),
        "modelspec_res": meta.get("modelspec.resolution"),
        "modelspec_pred": meta.get("modelspec.prediction_type"),
    }
    tf = meta.get("ss_tag_frequency")
    if tf:
        try:
            d = json.loads(tf) if isinstance(tf, str) else tf
            buckets = {}
            for bucket, tags in d.items():
                top = sorted(tags.items(), key=lambda kv: -kv[1])[:40]
                buckets[bucket] = top
                out.setdefault("tag_buckets", {})[bucket] = {
                    "n_tags": len(tags),
                    "top": top,
                }
        except Exception as e:
            out["tag_freq_error"] = str(e)
    return out


def main():
    targets = sys.argv[1:] or [f for f in os.listdir(LORA_DIR) if f.endswith(".safetensors")]
    res = []
    for t in targets:
        p = t if os.path.isabs(t) else os.path.join(LORA_DIR, t)
        if not os.path.exists(p) or os.path.getsize(p) < 10000:
            continue
        try:
            res.append(summarize(p))
        except Exception as e:
            res.append({"file": os.path.basename(p), "error": str(e)})
    outp = r"D:\ComfyUI\logs\anima_lora_inspect.json"
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    for r in res:
        print("=== %s  %sMB" % (r.get("file"), r.get("mb")))
        print("    unet=%s te=%s other=%s alphas=%s dims=%s" % (
            r.get("unet_tensors"), r.get("te_tensors"), r.get("other_tensors"),
            r.get("alphas"), r.get("dims")))
        print("    base=%s dim=%s alpha=%s imgs=%s res=%s title=%s" % (
            r.get("ss_base_model_version"), r.get("ss_network_dim"), r.get("ss_network_alpha"),
            r.get("ss_num_train_images"), r.get("ss_resolution"), r.get("modelspec_title")))
        for b, info in (r.get("tag_buckets") or {}).items():
            print("    [%s] %d tags; top: %s" % (b, info["n_tags"],
                  ", ".join("%s(%d)" % (k, v) for k, v in info["top"][:22])))
    print("\nJSON -> %s" % outp)


if __name__ == "__main__":
    main()
