#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""tagkit —— 提示词校验/归一/排序工具（本地 danbooru 词表驱动）

数据源：dsh-comfyui-workbench 自带 data/danbooru/{general,artists,characters,copyrights}.jsonl
（四类共 99372 条，含中文别名 names[]）

用途：
  1) 把用户中文/口语/别名解析成合法 danbooru tag（防幻觉：不存在的词一律标 unknown）
  2) 权重语法归一：(((tag))) -> (tag:1.3)；限制 0.1~2.0
  3) 冲突检测：solo vs 2girls、nude vs fully_clothed 等
  4) 最终按"质量前缀 -> 画师/风格 -> 角色/作品 -> 构图 -> 服装 -> 姿势 -> 表情 -> NSFW -> 背景"排序

CLI：
  python tagkit.py check "1girl, 博丽灵梦, nude, (smile:1.2)"
  python tagkit.py resolve 东方 裸体 俯视
  python tagkit.py expand-file p.txt        # 读文件逐行校验
"""
from __future__ import annotations

import json
import re
import sys
import difflib
from pathlib import Path

DEFAULT_DATA = Path.home() / ".dsh" / "profiles" / "desktop" / "node_modules" / "dsh-comfyui-workbench" / "data" / "danbooru"

QUALITY_PREFIX = ["masterpiece", "best_quality", "amazing_quality", "very_aesthetic", "highres", "absurdres"]

# 类别顺序（越小越靠前）
ORDER = {
    "quality": 0,
    "artist": 1,
    "copyright": 2,
    "character": 3,
    "meta": 4,
    "general": 5,
    "nsfw": 6,
}

QUALITY_TAGS = set(QUALITY_PREFIX) | {
    "best quality", "masterpiece", "high quality", "ultra detailed", "newest",
    "high resolution", "extremely detailed", "8k", "4k",
}

# 主观分组：用于排序与冲突判断（按 tag 前缀/关键词粗分）
NSFW_HINTS = (
    "nude", "naked", "nipple", "areola", "breast", "pussy", "vagina", "penis", "cum",
    "sex", "fellatio", "paizuri", "handjob", "creampie", "anus", "anal", "spread_legs",
    "masturbation", "ahegao", "orgasm", "pubic", "censored", "uncensored", "topless",
    "underwear_only", "no_bra", "no_panties", "panties_aside", "clothed_sex",
)
POSE_HINTS = (
    "pose", "standing", "sitting", "kneeling", "lying", "on_back", "on_stomach",
    "all_fours", "crouch", "squat", "leaning", "straddle", "legs_up", "arms_up",
    "crossed_legs", "spread", "bent_over", "from_above", "from_below", "from_side",
    "from_behind", "pov", "cowboy_shot", "missionary", "doggystyle", "mating_press",
)
COMPOSITION_HINTS = (
    "portrait", "upper_body", "lower_body", "full_body", "cowboy_shot", "close-up",
    "wide_shot", "depth_of_field", "blurry_background", "simple_background",
    "cinematic", "dynamic_pose", "symmetry", "framing", "composition",
)
EXPRESSION_HINTS = (
    "smile", "grin", "blush", "tears", "crying", "angry", "surprised", "expression",
    "half-closed_eyes", "closed_eyes", "open_mouth", "tongue_out", "smug", "embarrassed",
    "ahegao", "orgasm_face", "heavy_breathing",
)

CONFLICTS = [
    ({"solo"}, {"2girls", "2boys", "3girls", "multiple_girls", "multiple_boys", "multiple_others"}),
    ({"nude", "completely_nude"}, {"fully_clothed", "clothes", "shirt", "dress"}),
    ({"topless"}, {"shirt", "dress", "jacket"}),
    ({"no_bra"}, {"bra"}),
    ({"no_panties"}, {"panties"}),
    ({"censored"}, {"uncensored"}),
    ({"closed_eyes"}, {"looking_at_viewer"}),
]

WEIGHT_MIN, WEIGHT_MAX = 0.1, 2.0
PAREN_RE = re.compile(r"\(+([^()]+?)\)+")


def _norm(s: str) -> str:
    return re.sub(r"[\s\-]+", "_", s.strip().lower())


CJK_RE = re.compile(r"[\u3400-\u9fff\u3040-\u30ff]")

# 底模约定的质量前缀不是 danbooru tag，按白名单原样放行（统一写法）
QUALITY_CANON = {
    "masterpiece": "masterpiece",
    "best_quality": "best quality",
    "amazing_quality": "amazing quality",
    "very_aesthetic": "very aesthetic",
    "highres": "highres",
    "absurdres": "absurdres",
    "high_quality": "high quality",
    "ultra_detailed": "ultra detailed",
    "extremely_detailed": "extremely detailed",
    "newest": "newest",
    "high_resolution": "high resolution",
}


class TagKit:
    def __init__(self, data_dir: Path = DEFAULT_DATA):
        self.data_dir = Path(data_dir)
        self.by_tag: dict[str, dict] = {}
        self.alias: dict[str, str] = {}
        for fname in ("general.jsonl", "artists.jsonl", "characters.jsonl", "copyrights.jsonl"):
            p = self.data_dir / fname
            if not p.exists():
                continue
            with p.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    tag = _norm(rec.get("tag", ""))
                    if not tag:
                        continue
                    self.by_tag[tag] = rec
                    self.alias.setdefault(tag, tag)
                    for n in rec.get("names") or []:
                        self.alias.setdefault(_norm(n), tag)

    # ---------- 解析 ----------
    def resolve_one(self, raw: str) -> tuple[str | None, str]:
        """返回 (canonical_tag | None, source)。source: quality/exact/alias/prefix/cjk-fuzzy/unknown"""
        t = _norm(raw)
        if t in QUALITY_CANON:
            return t, "quality"
        if t in self.by_tag:
            return t, "exact"
        if t in self.alias:
            return self.alias[t], "alias"
        # 前缀匹配：kanpa -> kanpa_(campagne_9)；要求 >=4 字符且唯一
        if len(t) >= 4:
            hits = [tag for tag in self.by_tag if tag.split("(")[0].rstrip("_") == t]
            if len(hits) == 1:
                return hits[0], "prefix"
        # 中文/假名别名模糊：只对 CJK 生效，避免 ASCII 误配
        if len(t) >= 2 and CJK_RE.search(t):
            hit = difflib.get_close_matches(t, self.alias.keys(), n=1, cutoff=0.9)
            if hit:
                return self.alias[hit[0]], "cjk-fuzzy"
        return None, "unknown"

    def resolve_text(self, text: str, min_post: int = 0) -> list[dict]:
        out = []
        for piece in split_tags(text):
            tag, src = self.resolve_one(piece)
            rec = self.by_tag.get(tag, {}) if tag else {}
            out.append({
                "raw": piece, "tag": tag, "source": src,
                "kind": rec.get("kind"), "postCount": rec.get("postCount", 0),
                "ok": bool(tag) and rec.get("postCount", 0) >= min_post,
            })
        return out

    # ---------- 权重/括号归一 ----------
    @staticmethod
    def flatten_parens(piece: str) -> str:
        """(((tag))) -> (tag:1.3)；已有 (tag:1.2) 原样保留

        注意：像 kanpa_(campagne_9) / gap_(touhou) 这种 tag 自带括号的写法必须原样跳过。
        """
        s = piece.strip()
        if ":" in s:
            return piece
        if not s.startswith("("):
            return piece                      # 非包裹式，tag 自带括号，跳过
        if not s.endswith(")"):
            return piece
        core = s.strip("()")
        if not core or "(" in core or ")" in core:
            return piece
        depth = (len(s) - len(s.lstrip("(")))
        w = min(1.0 + 0.1 * max(0, depth - 1), 1.5)
        return f"({core}:{w:.2f})" if depth > 1 else piece

    @staticmethod
    def clamp_weight(piece: str) -> str:
        m = re.match(r"^\((.+):([0-9.]+)\)$", piece)
        if not m:
            return piece
        name, w = m.group(1), float(m.group(2))
        w = max(WEIGHT_MIN, min(WEIGHT_MAX, w))
        return f"({name}:{w:.2f})"

    # ---------- 排序 ----------
    def order_key(self, tag: str) -> tuple:
        rec = self.by_tag.get(tag, {})
        kind = rec.get("kind", "general")
        if tag in QUALITY_TAGS or kind == "quality":
            return (ORDER["quality"], -rec.get("postCount", 0), tag)
        if any(h in tag for h in NSFW_HINTS):
            return (ORDER["nsfw"], -rec.get("postCount", 0), tag)
        base = ORDER.get(kind, ORDER["general"])
        return (base, -rec.get("postCount", 0), tag)

    # ---------- 主校验 ----------
    def check(self, text: str, min_post: int = 30, dialect: str = "danbooru") -> dict:
        pieces = [p.strip() for p in split_tags(text) if p.strip()]
        resolved, unknown, fixed = [], [], []
        seen = set()
        for p in pieces:
            p2 = self.flatten_parens(p)
            if p2 != p:
                fixed.append(f"{p} -> {p2}")
            p2 = self.clamp_weight(p2)
            base = re.sub(r"^\((.+):[0-9.]+\)$", r"\1", p2).strip()
            tag, src = self.resolve_one(base)
            if tag is None:
                unknown.append(base)
                continue
            if tag in seen:
                fixed.append(f"duplicate {tag} dropped")
                continue
            seen.add(tag)
            if src == "quality":
                resolved.append({"piece": QUALITY_CANON[tag], "tag": tag, "source": src,
                                 "postCount": 10**7, "kind": "quality"})
                continue
            w = re.match(r"^\((.+):([0-9.]+)\)$", p2)
            piece = f"({tag}:{w.group(2)})" if w else tag
            resolved.append({"piece": piece, "tag": tag, "source": src,
                             "postCount": self.by_tag.get(tag, {}).get("postCount", 0),
                             "kind": self.by_tag.get(tag, {}).get("kind", "general")})

        low = [r["tag"] for r in resolved if r["postCount"] < min_post]
        conflicts = []
        tagset = set(r["tag"] for r in resolved)
        for a, b in CONFLICTS:
            if tagset & a and tagset & b:
                conflicts.append(f"{sorted(tagset & a)} vs {sorted(tagset & b)}")

        ordered = sorted(resolved, key=lambda r: self.order_key(r["tag"]))
        positive = ", ".join(r["piece"] for r in ordered)

        return {
            "positive": positive,
            "unknown": unknown,
            "rare": [f"{t}({self.by_tag.get(t, {}).get('postCount', 0)})" for t in low],
            "conflicts": conflicts,
            "fixed": fixed,
            "tags": [r["tag"] for r in ordered],
            "count": len(ordered),
            "dialect": dialect,
        }


def split_tags(text: str) -> list[str]:
    """按逗号/换行切分，但保留括号内的逗号"""
    out, buf, depth = [], [], 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch in ",\n" and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        out.append("".join(buf))
    return out


def main(argv: list[str]) -> int:
    kit = TagKit()
    if len(argv) < 3:
        print(__doc__)
        return 0
    cmd = argv[1]
    if cmd == "check":
        r = kit.check(argv[2])
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    if cmd == "resolve":
        for item in kit.resolve_text(" ".join(argv[2:])):
            print(f'{item["raw"]:>20} -> {item["tag"] or "??":<32} {item["source"]:<8} {item["kind"] or "-":<10} {item["postCount"]}')
        return 0
    if cmd == "expand-file":
        p = Path(argv[2])
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = kit.check(line)
                print(json.dumps({"in": line, **r}, ensure_ascii=False))
        return 0
    print(f"unknown command: {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
