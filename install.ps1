param(
    [string]$Dir = "D:\ComfyUI",
    [int]$Only = 0,
    [switch]$Yes,
    [switch]$NoModels,
    [string]$Repo = "https://github.com/kilier18/anima-workbench.git"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
# 控制台用 UTF-8 输出，否则中文在 CP936 下全是乱码
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
try { $Host.UI.RawUI.WindowTitle = "Anima Workbench 安装向导" } catch { }

# ============================================================
#  基础工具
# ============================================================
$script:Fail = 0
$script:Skip = 0

function Invoke-Py {
    param([string]$Python, [string[]]$PyArgs)
    $old = $ErrorActionPreference
    $oldEnc = $env:PYTHONIOENCODING
    $ErrorActionPreference = "Continue"
    $env:PYTHONIOENCODING = "utf-8"   # 否则 python 的中文输出在 CP936 控制台是乱码
    try {
        $out = (& $Python @PyArgs 2>&1 | Out-String)
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $old
        $env:PYTHONIOENCODING = $oldEnc
    }
    return [pscustomobject]@{ Code = $code; Out = $out.Trim() }
}

function Invoke-Git {
    # PowerShell 5.1 会把 native 命令的 stderr 当成 ErrorRecord，配合
    # $ErrorActionPreference="Stop" 会直接中断脚本。统一在这里吞掉噪音、
    # 只回传退出码与合并输出。
    param([string[]]$GitArgs)
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = (& git @GitArgs 2>&1 | Out-String)
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $old
    }
    return [pscustomobject]@{ Code = $code; Out = $out.Trim() }
}

function Say([string]$m, [string]$c = "Gray") {
    Write-Host $m -ForegroundColor $c
}
function Head([int]$n, [string]$t) {
    Say ""
    Say ("=" * 66) "DarkCyan"
    Say ("  第 $n 步  $t") "Cyan"
    Say ("=" * 66) "DarkCyan"
}
function Ok([string]$m)   { Say ("  [OK]   " + $m) "Green" }
function Warn([string]$m) { Say ("  [注意] " + $m) "Yellow"; $script:Fail++ }
function Bad([string]$m)  { Say ("  [失败] " + $m) "Red"; $script:Fail++ }
function Info([string]$m) { Say ("         " + $m) "DarkGray" }

function Ask([string]$q, [string]$def = "y") {
    if ($Yes) { return $true }
    $hint = if ($def -eq "y") { "[Y/n]" } else { "[y/N]" }
    $a = Read-Host ("  " + $q + " " + $hint)
    if ([string]::IsNullOrWhiteSpace($a)) { $a = $def }
    return ($a.Trim().ToLower() -in @("y", "yes", "是"))
}

function Have([string]$exe) {
    return [bool](Get-Command $exe -ErrorAction SilentlyContinue)
}

function Get-File([string]$url, [string]$out) {
    Info ("下载 " + (Split-Path $out -Leaf))
    Info $url
    try {
        if (Have "curl.exe") {
            & curl.exe -L --fail --retry 3 --progress-bar -o $out $url
            if ($LASTEXITCODE -ne 0) { throw "curl 退出码 $LASTEXITCODE" }
        } else {
            Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing
        }
        return $true
    } catch {
        Say ("         下载失败：" + $_.Exception.Message) "Red"
        if (Test-Path $out) { Remove-Item $out -Force -ErrorAction SilentlyContinue }
        return $false
    }
}

function Get-Size([string]$p) {
    if (Test-Path $p) { return [math]::Round((Get-Item $p).Length / 1MB, 1) }
    return 0
}

# ============================================================
#  第 1 步：环境自检
# ============================================================
function Step1 {
    Head 1 "环境自检"

    $os = [System.Environment]::OSVersion.Version
    Ok ("Windows " + $os.Major + "." + $os.Minor + " (" + [System.Environment]::Is64BitOperatingSystem + ")")

    $driveLetter = ([System.IO.Path]::GetPathRoot($Dir)) -replace '[:\\]', ''
    $free = 0
    try { $free = [math]::Round((Get-PSDrive -Name $driveLetter).Free / 1GB, 1) } catch { }
    if ($free -gt 0 -and $free -lt 30) { Warn ("目标盘只剩 " + $free + " GB，模型约 8 GB + 输出，建议留 30 GB 以上") }
    elseif ($free -gt 0) { Ok ("目标盘可用空间 " + $free + " GB") }
    else { Warn ("读不到 " + $driveLetter + " 盘的剩余空间") }

    if (Have "git") {
        $gv = Invoke-Git @("--version")
        $v = ($gv.Out -replace "git version ", "").Trim()
        Ok ("git " + $v)
    } else {
        Bad "没有 git。请先安装：winget install --id Git.Git -e"
        Info "装完重开一个终端再跑本脚本"
    }

    $gpu = $null
    try {
        $gpu = Get-CimInstance Win32_VideoController -ErrorAction Stop |
               Where-Object { $_.Name -match "NVIDIA|AMD|Intel" } |
               Select-Object -First 1
    } catch { }
    if ($gpu) {
        $mem = if ($gpu.AdapterRAM) { [math]::Round($gpu.AdapterRAM / 1GB, 1) } else { "?" }
        Ok ("显卡 " + $gpu.Name + "  显存约 " + $mem + " GB")
        if ($gpu.Name -notmatch "NVIDIA") {
            Warn "本手册只覆盖 NVIDIA 路径，其它显卡可能需要额外配置"
        }
    } else {
        Warn "没检测到显卡信息，继续但可能无法出图"
    }

    $ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
    Ok ("内存 " + $ram + " GB")
    if ($ram -lt 15) { Warn "内存低于 16 GB，批量出图可能吃紧" }

    Ok ("安装目录 " + $Dir)
}

# ============================================================
#  第 2 步：ComfyUI
# ============================================================
function Step2 {
    Head 2 "安装 ComfyUI"

    $portable = Join-Path $Dir "ComfyUI_windows_portable"
    $py = Join-Path $portable "python_embeded\python.exe"

    if (Test-Path $py) {
        Ok "已存在 ComfyUI，跳过"
        Info $portable
        return
    }

    Say "  ComfyUI 需要单独下载。三个来源："
    Info "A) 官方 releases（7z，约 1.4 GB）"
    Info "   https://github.com/comfyanonymous/ComfyUI/releases/latest"
    Info "B) 国内镜像可搜 ComfyUI_windows_portable"
    Info "C) 已经装过：把 ComfyUI_windows_portable 整个目录放到 $Dir 下即可"
    Say ""

    if (Ask "要我尝试自动下载官方 portable 包吗？(需要能访问 GitHub)" "y") {
        $tmp = Join-Path $env:TEMP "comfy_portable.7z"
        $api = "https://api.github.com/repos/comfyanonymous/ComfyUI/releases/latest"
        $url = $null
        try {
            $rel = Invoke-RestMethod -Uri $api -UseBasicParsing -Headers @{ "User-Agent" = "aw" }
            $asset = $rel.assets | Where-Object { $_.name -like "*windows_portable*nvidia*.7z" } | Select-Object -First 1
            if ($asset) { $url = $asset.browser_download_url }
        } catch { }
        if (-not $url) {
            Warn "自动查最新版本失败（可能被墙或 API 限流），请手动下载"
        } elseif (Get-File $url $tmp) {
            $sevenZip = Join-Path $env:TEMP "7zr.exe"
            if (-not (Test-Path $sevenZip)) {
                Get-File "https://www.7-zip.org/a/7zr.exe" $sevenZip | Out-Null
            }
            if (Test-Path $sevenZip) {
                Info "解压中（约 1–3 分钟）…"
                New-Item -ItemType Directory -Force -Path $Dir | Out-Null
                & $sevenZip x $tmp ("-o" + $Dir) -y | Out-Null
                Ok "解压完成"
            } else {
                Warn ("已下载到 " + $tmp + "，但缺少 7zr.exe，请手动解压到 " + $Dir)
            }
        }
    }

    if (Test-Path $py) {
        Ok "ComfyUI 就绪"
    } else {
        Warn "ComfyUI 未就绪 —— 放好后再跑一次：install.cmd 2"
    }
}

# ============================================================
#  第 3 步：模型目录
# ============================================================
function Step3 {
    Head 3 "建立模型目录"

    $m = Join-Path $Dir "models"
    $dirs = @(
        "diffusion_models\Anima", "text_encoders", "vae", "loras\Anima",
        "checkpoints", "controlnet", "upscale_models", "ipadapter",
        "clip_vision", "embeddings", "ultralytics\bbox", "ultralytics\segm"
    )
    foreach ($d in $dirs) {
        New-Item -ItemType Directory -Force -Path (Join-Path $m $d) | Out-Null
    }
    Ok ($dirs.Count.ToString() + " 个模型子目录就绪")

    $yaml = Join-Path $Dir "extra_model_paths.yaml"
    if (Test-Path $yaml) {
        Ok "extra_model_paths.yaml 已存在，保留不覆盖"
        return
    }
    $body = @"
# ComfyUI 模型路径重定向：让 portable 包指向统一的模型目录，
# 换 ComfyUI 版本时不丢模型。
comfyui:
  base_path: $($m -replace '\\','/')
  checkpoints: checkpoints
  loras: loras
  vae: vae
  controlnet: controlnet
  upscale_models: upscale_models
  ipadapter: ipadapter
  clip_vision: clip_vision
  clip: clip
  text_encoders: text_encoders
  unet: unet
  embeddings: embeddings
  diffusion_models: diffusion_models
  ultralytics_bbox: ultralytics/bbox
  ultralytics_segm: ultralytics/segm
  impact: impact
"@
    Set-Content -LiteralPath $yaml -Value $body -Encoding UTF8
    Ok "已写 extra_model_paths.yaml"
}

# ============================================================
#  第 4 步：模型文件
# ============================================================
function Step4 {
    Head 4 "下载模型文件"

    if ($NoModels) { Say "  (已指定 -NoModels，跳过)"; return }

    $m = Join-Path $Dir "models"
    $items = @(
        @{ n = "qwen_3_06b_base.safetensors"; p = "text_encoders"; s = 1137;
           u = "https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/text_encoders/qwen_3_06b_base.safetensors" },
        @{ n = "qwen_image_vae.safetensors"; p = "vae"; s = 242;
           u = "https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/vae/qwen_image_vae.safetensors" },
        @{ n = "anima-base-v1.0.safetensors"; p = "diffusion_models\Anima"; s = 3989;
           u = "https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/diffusion_models/anima-base-v1.0.safetensors" }
    )

    foreach ($it in $items) {
        $dst = Join-Path (Join-Path $m $it.p) $it.n
        if ((Get-Size $dst) -gt ($it.s * 0.9)) {
            Ok ($it.n + " 已存在 (" + (Get-Size $dst) + " MB)")
            continue
        }
        Say ("  " + $it.n + "  约 " + $it.s + " MB  ->  models\" + $it.p)
        if (Ask ("  下载它？") "y") {
            if (Get-File $it.u $dst) { Ok ("完成 " + (Get-Size $dst) + " MB") }
            else { Warn ("没下成，请手动下载：" + $it.u) }
        } else {
            Info ("跳过。地址：" + $it.u)
        }
    }

    Say ""
    Say "  以下文件需要手动获取（作者不提供直链）：" "Yellow"
    Info "LoRA  anima-turbo-lora-v0.2.safetensors  -> models\loras\Anima\"
    Info "LoRA  kinokohime_v2.safetensors           -> models\loras\Anima\"
    Info "LoRA  konyaKarasue_Anima1_lora_V42.safetensors -> models\loras\Anima\"
    Info "融合版 miaomiaoHarem_anima12.safetensors  -> models\diffusion_models\Anima\"
    Info "（换模型后要改 webui\assistant.py 里的 ANIMA_UNET）"
    Info "缺 LoRA 也能跑：把 assistant.py 里 ANIMA_LORAS 对应行删掉或权重改 0"
}

# ============================================================
#  第 5 步：自定义节点
# ============================================================
function Step5 {
    Head 5 "安装自定义节点"

    $cn = Join-Path $Dir "ComfyUI_windows_portable\ComfyUI\custom_nodes"
    if (-not (Test-Path $cn)) {
        Warn ("找不到 " + $cn + "，先完成第 2 步")
        return
    }

    $nodes = @(
        @{ d = "ComfyUI-Manager";        u = "https://github.com/ltdrdata/ComfyUI-Manager";        need = $true },
        @{ d = "ComfyUI-Impact-Pack";    u = "https://github.com/ltdrdata/ComfyUI-Impact-Pack";    need = $true },
        @{ d = "ComfyUI-Impact-Subpack"; u = "https://github.com/ltdrdata/ComfyUI-Impact-Subpack"; need = $true },
        @{ d = "ComfyUI-GGUF";           u = "https://github.com/city96/ComfyUI-GGUF";             need = $false },
        @{ d = "ComfyUI_IPAdapter_plus"; u = "https://github.com/cubiq/ComfyUI_IPAdapter_plus";    need = $false }
    )

    foreach ($n in $nodes) {
        $t = Join-Path $cn $n.d
        if (Test-Path $t) { Ok ($n.d + " 已存在"); continue }
        $tag = if ($n.need) { "必需" } else { "可选" }
        Say ("  " + $n.d + "  [" + $tag + "]")
        if (Ask "  拉取？" "y") {
            $r = Invoke-Git @("clone", "--depth", "1", $n.u, $t)
            if (Test-Path $t) { Ok ($n.d + " 完成") }
            elseif ($n.need) { Bad ($n.d + " 拉取失败：" + $n.u) }
            else { Warn ($n.d + " 拉取失败（可选，可忽略）") }
        } else {
            if ($n.need) { Warn ($n.d + " 未安装 —— 出图会报节点缺失") }
        }
    }
}

# ============================================================
#  第 6 步：安装工作台
# ============================================================
function Step6 {
    Head 6 "安装工作台（本仓库）"

    $hasPy = Test-Path (Join-Path $Dir "webui\assistant.py")

    if ($hasPy) {
        Ok "工作台已存在"
        $cur = (Invoke-Git @("-C", $Dir, "rev-parse", "--short", "HEAD")).Out
        if ($cur) { Info ("当前提交 " + $cur) }
        if (Ask "从远程更新到最新版？" "y") {
            $br = (Invoke-Git @("-C", $Dir, "rev-parse", "--abbrev-ref", "HEAD")).Out
            Invoke-Git @("-C", $Dir, "fetch", "origin", "--quiet") | Out-Null
            Invoke-Git @("-C", $Dir, "branch", "--set-upstream-to=origin/$br", $br) | Out-Null
            $r = Invoke-Git @("-C", $Dir, "pull", "--ff-only")
            if ($r.Code -eq 0) { Ok "已更新到最新版" } else { Warn ("更新失败：" + $r.Out) }
        }
    } else {
        New-Item -ItemType Directory -Force -Path $Dir | Out-Null
        if (Test-Path (Join-Path $Dir ".git")) {
            Warn "目录已有 .git，跳过克隆"
        } else {
            $tmp = Join-Path $env:TEMP ("aw_" + [guid]::NewGuid().ToString("N").Substring(0, 8))
            Info ("克隆 " + $Repo)
            $r = Invoke-Git @("clone", "--depth", "1", $Repo, $tmp)
            if (Test-Path (Join-Path $tmp "webui\assistant.py")) {
                # 只复制仓库里的东西，不动 ComfyUI 等已有内容
                Copy-Item -Path (Join-Path $tmp "*") -Destination $Dir -Recurse -Force
                Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
                Ok "工作台文件已就位"
            } else {
                Bad "克隆失败。手动执行：git clone $Repo `"$Dir`""
                return
            }
        }
    }

    # 把脚本里的 D:\ComfyUI 换成实际安装目录
    $fixed = 0
    foreach ($f in @("_setup\start_engine.cmd", "_setup\start_assistant.cmd", "_setup\start_ollama.cmd")) {
        $p = Join-Path $Dir $f
        if (-not (Test-Path $p)) { continue }
        $raw = [System.IO.File]::ReadAllText($p)
        if ($raw -match [regex]::Escape($Dir)) { continue }
        $new = $raw -replace [regex]::Escape("D:\ComfyUI"), [regex]::Escape($Dir).Replace('\', '\')
        $new = $new.Replace("D:\ComfyUI", $Dir)
        [System.IO.File]::WriteAllText($p, $new, [System.Text.Encoding]::ASCII)
        $fixed++
    }
    $ps1 = Join-Path $Dir "ComfyUI控制台.ps1"
    if (Test-Path $ps1) {
        $raw = [System.IO.File]::ReadAllText($ps1)
        if ($raw -notmatch [regex]::Escape("`$ROOT     = '" + $Dir + "'")) {
            $new = $raw.Replace("`$ROOT     = 'D:\ComfyUI'", "`$ROOT     = '" + $Dir + "'")
            [System.IO.File]::WriteAllText($ps1, $new, (New-Object System.Text.UTF8Encoding($true)))
            $fixed++
        }
    }
    if ($fixed -gt 0) { Ok ("已把 $fixed 个脚本里的路径改成 " + $Dir) }
    else { Ok "脚本路径已是目标目录，无需修改" }
}

# ============================================================
#  第 7 步：冒烟验证
# ============================================================
function Step7 {
    Head 7 "冒烟验证"

    # 优先用 ComfyUI 自带的 python；没有就退回系统 python（数据体检不依赖 ComfyUI）
    $py = Join-Path $Dir "ComfyUI_windows_portable\python_embeded\python.exe"
    if (-not (Test-Path $py)) {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($cmd) { $py = $cmd.Source; Info "用系统 python 验证数据（ComfyUI 还没装）" }
    }
    if (-not $py) { Warn "既没有 ComfyUI 的 python，也没有系统 python，跳过"; return }

    foreach ($f in @("webui\assistant.py", "webui\planner.py", "tools\build_atoms.py", "tools\gen_workbench.py", "tools\verify_repo.py")) {
        $p = Join-Path $Dir $f
        if (-not (Test-Path $p)) { Bad ("缺文件 " + $f); continue }
        $r = Invoke-Py $py @("-m", "py_compile", $p)
        if ($r.Code -eq 0) { Ok ($f + " 编译通过") } else { Bad ($f + " 编译失败：" + $r.Out) }
    }

    $hc = Join-Path $Dir "tools\health_check.py"
    if (Test-Path $hc) {
        Say "  数据体检："
        $r = Invoke-Py $py @($hc)
        ($r.Out -split "`n" | Select-Object -Last 4) | ForEach-Object { Info $_ }
    }

    $vr = Join-Path $Dir "tools\verify_repo.py"
    if (Test-Path $vr) {
        Say "  仓库一致性："
        $r = Invoke-Py $py @($vr, "--quiet")
        ($r.Out -split "`n" | Where-Object { $_.Trim() } | Select-Object -Last 6) | ForEach-Object { Info $_ }
        Info "（第 6 步把脚本里的路径改写成了本机目录，所以这几行报差异属正常）"
    }

    Say ""
    Say "  手动确认清单：" "Cyan"
    Info "1. 双击 _setup\start_engine.cmd，等到日志出现 http://127.0.0.1:8188"
    Info "2. 双击 _setup\start_assistant.cmd"
    Info "3. 浏览器打开 http://127.0.0.1:8190 ，应能看到资料库有数据"
    Info "4. 选一个角色点「生成」，30–60 秒出图即成功"
}

# ============================================================
#  主流程
# ============================================================
Clear-Host
Say ""
Say "  Anima Workbench 安装向导" "Cyan"
Say "  目标目录：$Dir" "Gray"
Say "  分步执行：install.cmd 1 / 2 / 3 …   全部执行：install.cmd" "DarkGray"

$steps = @(
    @{ n = 1; t = "环境自检";       f = { Step1 } },
    @{ n = 2; t = "安装 ComfyUI";   f = { Step2 } },
    @{ n = 3; t = "建立模型目录";   f = { Step3 } },
    @{ n = 4; t = "下载模型文件";   f = { Step4 } },
    @{ n = 5; t = "安装自定义节点"; f = { Step5 } },
    @{ n = 6; t = "安装工作台";     f = { Step6 } },
    @{ n = 7; t = "冒烟验证";       f = { Step7 } }
)

if ($Only -gt 0) {
    $s = $steps | Where-Object { $_.n -eq $Only }
    if (-not $s) { Say ("没有第 $Only 步") "Red"; exit 1 }
    & $s.f
} else {
    foreach ($s in $steps) { & $s.f }
}

Say ""
Say ("=" * 66) "DarkCyan"
if ($script:Fail -eq 0) {
    Say "  全部完成，没有发现问题。" "Green"
} else {
    Say ("  有 " + $script:Fail + " 处需要注意，见上方黄色/红色行。") "Yellow"
}
Say ("=" * 66) "DarkCyan"
Say ""
if (-not $Yes) { Read-Host "按回车退出" | Out-Null }
