# -*- coding: utf-8 -*-
"""AI 拟人角色一批跑图：全身、LoRA0.9 + 完整触发词。"""
import json, subprocess, sys

PY = r"D:\ComfyUI\ComfyUI_windows_portable\python_embeded\python.exe"
RUN = r"D:\ComfyUI\tools\anima_run_char.py"
BATCH = "musume2"
SEED = "20251114"
P = "Anima\\packs\\"

JOBS = [
    ("whale-chibi-09",
     "ds_whalemaid, chibi, 1girl, solo, full body, standing, maid outfit, frilled apron, white apron, "
     "maid headdress, blue hair, short hair, blue eyes, whale tail, frills, "
     "white background, simple background, looking at viewer", P + "deepseek-whalemaid-chibi.safetensors|0.9"),
    ("whale-chibi-10",
     "ds_whalemaid, chibi, 1girl, solo, full body, standing, maid outfit, frilled apron, white apron, "
     "maid headdress, blue hair, short hair, blue eyes, whale tail, frills, "
     "white background, simple background, looking at viewer", P + "deepseek-whalemaid-chibi.safetensors|1.0"),
    ("deepseek-qchibi",
     "deepseek [chibi] musume, (chibi:1.2), 1girl, solo, full body, standing, maid headdress, blue dress, "
     "white apron, frilled apron, blue hair, long hair, blue eyes, blue bow, ahoge, "
     "white background, simple background, looking at viewer", P + "deepseek-chibi-musume.safetensors|0.9"),
    ("deepseek-whale-full",
     "deepseek_whale_girl_zipzippipe, deepseek_maid_outfit_zipzippipe, 1girl, solo, full body, standing, "
     "maid outfit, white frilled apron, blue whale tail, frilled thighhighs, white thighhighs, "
     "navy blue mary janes, white background, simple background, looking at viewer",
     r"Anima\musume-deepseek-whale.safetensors|0.9"),
    ("gpt-dragon-new",
     "Chatgpt_dragon_girl, 1girl, solo, full body, standing, dragon girl, white hair, long hair, white horns, "
     "dragon horns, pointy ears, purple eyes, ahoge, hair ornament, dragon wings, dragon tail, "
     "white background, simple background, looking at viewer", P + "chatgpt-dragon-alt.safetensors|0.9"),
    ("gpt-dragon-old",
     "白龙娘, 1girl, solo, full body, standing, white background, simple background, looking at viewer",
     r"Anima\musume-gpt-white-dragon.safetensors|0.9"),
    ("claude-girl",
     "claude_girl, 1girl, solo, full body, standing, orange hair, very long hair, wavy hair, bangs, orange eyes, "
     "hair flower, hair bow, black bow, white dress, long dress, frills, long sleeves, puffy sleeves, capelet, "
     "corset, brooch, chain, tassel, white boots, white background, simple background, looking at viewer",
     P + "claude-girl.safetensors|0.9"),
    ("claude-chan",
     "ors scholar, 1girl, solo, full body, standing, hair flower, orange flower, black hair bow, white capelet, "
     "white dress, long sleeves, puffy sleeves, forearm corsets, black corset, earrings, black ascot, brooch, "
     "jabot, high collar, frilled sleeves, gold buttons, gold chain, overskirt, long skirt, "
     "white background, simple background, looking at viewer", P + "claude-chan.safetensors|0.9"),
    ("claude-chan-alt",
     "年轻Claude娘, 1girl, solo, full body, standing, white dress, orange hair, "
     "white background, simple background, looking at viewer", P + "claude-chan-alt.safetensors|0.9"),
]


def main():
    only = sys.argv[1:] or None
    for slug, prompt, lora in JOBS:
        if only and slug not in only:
            continue
        r = subprocess.run([PY, RUN, BATCH, slug, prompt, "--seed", SEED, "--lora", lora],
                           capture_output=True, text=True, encoding="utf-8")
        print(r.stdout.strip() or r.stderr.strip()[-300:], flush=True)


if __name__ == "__main__":
    main()
