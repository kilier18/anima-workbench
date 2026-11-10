# -*- coding: utf-8 -*-
"""仓库与本地一致性校验。

用途：确认「工作区里的文件」和「已经提交到仓库的内容」完全一致，
      避免出现「本地改了但没提交」或「仓库里的文件和本地不一样」。

只用标准库，不依赖 git 之外的东西。

用法：
    python tools/verify_repo.py            # 详细报告
    python tools/verify_repo.py --quiet    # 只输出结论行（给安装脚本用）
    python tools/verify_repo.py --remote   # 额外比对本地 HEAD 与远程 main

退出码：0 = 完全一致；1 = 有差异。
"""
import hashlib
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def git(*args, check=False):
    # core.quotepath=false：否则中文文件名会被转成 \346\216 形式，路径就找不到了
    p = subprocess.run(["git", "-c", "core.quotepath=false"] + list(args),
                       cwd=ROOT, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError("git %s 失败: %s" % (" ".join(args), p.stderr.decode("utf-8", "replace")))
    return p


def head_files():
    """仓库 HEAD 里被跟踪的文件列表（相对路径，/ 分隔）。"""
    p = git("ls-tree", "-r", "--name-only", "HEAD")
    if p.returncode != 0:
        return None
    return [x for x in p.stdout.decode("utf-8", "replace").split("\n") if x.strip()]


def head_blob(path):
    p = git("show", "HEAD:" + path)
    return p.stdout if p.returncode == 0 else None


def sha(b):
    return hashlib.sha256(b).hexdigest()


def norm_crlf(b):
    """git 在 Windows 上可能把 LF 转成 CRLF，比对前统一成 LF 再算 hash。"""
    return b.replace(b"\r\n", b"\n")


def main():
    quiet = "--quiet" in sys.argv
    do_remote = "--remote" in sys.argv

    if git("rev-parse", "--git-dir").returncode != 0:
        print("× 这里不是 git 仓库，无法校验")
        return 1

    files = head_files()
    if files is None:
        print("× 仓库还没有任何提交")
        return 1

    same, modified, missing = [], [], []
    for f in files:
        fp = os.path.join(ROOT, f.replace("/", os.sep))
        blob = head_blob(f)
        if not os.path.exists(fp):
            missing.append(f)
            continue
        try:
            local = open(fp, "rb").read()
        except Exception as e:
            modified.append((f, "读取失败: %s" % e))
            continue
        if blob is not None and sha(norm_crlf(local)) == sha(norm_crlf(blob)):
            same.append(f)
        else:
            lc = norm_crlf(local).decode("utf-8", "replace").count("\n")
            bc = norm_crlf(blob or b"").decode("utf-8", "replace").count("\n")
            modified.append((f, "本地 %d 行 / 仓库 %d 行" % (lc, bc)))

    # 工作区里存在、但没被跟踪的文件（排除 .gitignore 命中的）
    st = git("status", "--porcelain", "--untracked-files=normal")
    untracked = []
    for line in st.stdout.decode("utf-8", "replace").split("\n"):
        if line.startswith("?? "):
            untracked.append(line[3:].strip())
        elif line[:2] in (" M", "M ", "MM", "A ", " D", "D "):
            pass  # 已在上面的 modified / missing 里体现

    ok = not modified and not missing

    if not quiet:
        print("=" * 62)
        print(" 仓库 / 本地 一致性校验")
        print("=" * 62)
        print(" 仓库跟踪文件      %d" % len(files))
        print(" 内容一致          %d" % len(same))
        print(" 内容有差异        %d" % len(modified))
        print(" 本地缺失          %d" % len(missing))
        if untracked:
            print(" 未被跟踪(未入库)  %d" % len(untracked))
        print("-" * 62)
        if modified:
            print(" 差异明细：")
            for f, why in modified:
                print("   ! %-46s %s" % (f, why))
        if missing:
            print(" 缺失明细：")
            for f in missing:
                print("   x %s" % f)
        if untracked and len(untracked) <= 20:
            print(" 未入库（正常，多为本地产物）：")
            for f in untracked:
                print("   ? %s" % f)
        elif untracked:
            print(" 未入库：%d 个（过多，已省略明细）" % len(untracked))

    if do_remote:
        git("fetch", "origin", "--quiet")
        local_head = git("rev-parse", "HEAD").stdout.decode().strip()
        r = git("rev-parse", "origin/main")
        remote_head = r.stdout.decode().strip() if r.returncode == 0 else ""
        if not quiet:
            print("-" * 62)
        if not remote_head:
            print(" 远程比对：拿不到 origin/main")
        elif local_head == remote_head:
            if not quiet:
                print(" 远程比对：本地 HEAD == origin/main (%s)" % local_head[:8])
        else:
            ahead = git("rev-list", "--count", "origin/main..HEAD").stdout.decode().strip()
            behind = git("rev-list", "--count", "HEAD..origin/main").stdout.decode().strip()
            print(" 远程比对：不一致  本地 %s / 远程 %s  (领先 %s，落后 %s)"
                  % (local_head[:8], remote_head[:8], ahead, behind))
            ok = False

    print("=" * 62)
    print("结论：%s" % ("✓ 本地与仓库完全一致" if ok else "× 存在差异，见上"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
