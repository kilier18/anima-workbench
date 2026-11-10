param(
  [switch]$TestUi,
  [switch]$SelfTest,
  [switch]$TestStart,
  [switch]$TestStop
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[void][System.Windows.Forms.Application]::EnableVisualStyles()

$ROOT     = 'D:\ComfyUI'
$PORTABLE = Join-Path $ROOT 'ComfyUI_windows_portable'
$APPDIR   = Join-Path $PORTABLE 'ComfyUI'
$PY       = Join-Path $PORTABLE 'python_embeded\python.exe'
$LOG      = Join-Path $ROOT '_setup\comfy.log'
$ERRLOG   = Join-Path $ROOT '_setup\comfy.err.log'
$PIDFILE  = Join-Path $ROOT '_setup\comfy.pid'
$WEBUI    = Join-Path $ROOT 'webui'
$WV2DIR   = Join-Path $ROOT '_setup\webview2'
$ENGINE_CMD = Join-Path $ROOT '_setup\start_engine.cmd'
$AI_CMD     = Join-Path $ROOT '_setup\start_assistant.cmd'
$OLLAMA_CMD = Join-Path $ROOT '_setup\start_ollama.cmd'
$API      = 'http://127.0.0.1:8188'
$AI       = 'http://127.0.0.1:8190'
$FORGE    = 'http://127.0.0.1:8190/'
$STUDIO   = 'http://127.0.0.1:8190/'
$LIBRARY  = 'http://127.0.0.1:8190/'
$COMFYUI  = 'http://127.0.0.1:8188'

# ---- 出图目录：与工坊 webui/data/wb_config.json 保持一致 ----
$CFGFILE  = Join-Path $WEBUI 'data\wb_config.json'
function Get-OutDir {
  try {
    if (Test-Path $CFGFILE) {
      $j = Get-Content -LiteralPath $CFGFILE -Raw -Encoding UTF8 | ConvertFrom-Json
      if ($j.output_dir -and ([string]$j.output_dir).Trim().Length -gt 0) {
        return ([string]$j.output_dir).Trim()
      }
    }
  } catch { }
  if ($env:COMFY_OUTPUT -and $env:COMFY_OUTPUT.Trim().Length -gt 0) { return $env:COMFY_OUTPUT.Trim() }
  return (Join-Path $ROOT 'output')
}
$OUTDIR   = Get-OutDir
$ARGS     = @('-s','main.py','--windows-standalone-build','--lowvram',
              '--use-pytorch-cross-attention','--preview-method','none',
              '--port','8188','--listen','127.0.0.1',
              '--output-directory', $OUTDIR,
              '--extra-model-paths-config', (Join-Path $ROOT 'extra_model_paths.yaml'))

# ---- WebView2 程序集 ----
try {
  Add-Type -Path (Join-Path $WV2DIR 'Microsoft.Web.WebView2.Core.dll')
  Add-Type -Path (Join-Path $WV2DIR 'Microsoft.Web.WebView2.WinForms.dll')
  $env:PATH = $WV2DIR + ';' + $env:PATH
  $script:hasWv2 = $true
} catch { $script:hasWv2 = $false }

function Port-Open([int]$port = 8188, [int]$ms = 120) {
  # 非阻塞探测：最多等 $ms 毫秒，绝不卡住 UI 线程
  $c = New-Object System.Net.Sockets.TcpClient
  try {
    $ar = $c.BeginConnect('127.0.0.1', $port, $null, $null)
    if (-not $ar.AsyncWaitHandle.WaitOne($ms)) { return $false }
    $c.EndConnect($ar)
    return $c.Connected
  } catch { return $false }
  finally { try { $c.Close() } catch {} }
}

function Get-ComfyPid {
  if (Test-Path $PIDFILE) {
    $raw = Get-Content $PIDFILE -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($raw -match '^\d+$') {
      $p = Get-Process -Id ([int]$raw) -ErrorAction SilentlyContinue
      if ($p) { return [int]$raw }
    }
  }
  return 0
}

$form = New-Object System.Windows.Forms.Form
$form.Text = 'ComfyUI 工坊'
$form.Size = New-Object System.Drawing.Size(1180, 860)
$form.StartPosition = 'CenterScreen'
$form.BackColor = [System.Drawing.Color]::FromArgb(24, 26, 30)
$form.ForeColor = [System.Drawing.Color]::FromArgb(232, 234, 238)
$form.Font = New-Object System.Drawing.Font('Microsoft YaHei UI', 9)
$form.MinimumSize = New-Object System.Drawing.Size(900, 600)

$bar = New-Object System.Windows.Forms.Panel
$bar.Dock = 'Top'
$bar.Height = 62
$bar.BackColor = [System.Drawing.Color]::FromArgb(18, 20, 24)
$form.Controls.Add($bar)

function New-Btn([string]$t, [int]$x, [int]$y, [int]$w, [int]$h, $c) {
  $b = New-Object System.Windows.Forms.Button
  $b.Text = $t
  $b.Location = New-Object System.Drawing.Point($x, $y)
  $b.Size = New-Object System.Drawing.Size($w, $h)
  $b.FlatStyle = 'Flat'
  $b.FlatAppearance.BorderSize = 0
  $b.BackColor = $c
  $b.ForeColor = [System.Drawing.Color]::White
  $b.Font = New-Object System.Drawing.Font('Microsoft YaHei UI', 10, [System.Drawing.FontStyle]::Bold)
  $b.Cursor = 'Hand'
  $bar.Controls.Add($b)
  return $b
}

$C_START = [System.Drawing.Color]::FromArgb(46, 160, 67)
$C_STOP  = [System.Drawing.Color]::FromArgb(190, 60, 60)
$C_GREY  = [System.Drawing.Color]::FromArgb(58, 62, 70)
$C_BLUE  = [System.Drawing.Color]::FromArgb(52, 108, 190)

$btnStart = New-Btn '▶ 启动引擎' 14 12 118 38 $C_START
$btnStop  = New-Btn '■ 停止'     138 12 88 38 $C_STOP
$btnReload= New-Btn '⟳ 重载界面' 232 12 104 38 $C_BLUE
$btnOut   = New-Btn '📁 出图'    342 12 82 38 $C_GREY
$btnDoc   = New-Btn '📖 教程'    430 12 82 38 $C_GREY

$lblState = New-Object System.Windows.Forms.Label
$lblState.Text = '○ 未运行'
$lblState.Location = New-Object System.Drawing.Point(526, 18)
$lblState.Size = New-Object System.Drawing.Size(620, 26)
$lblState.Font = New-Object System.Drawing.Font('Microsoft YaHei UI', 11, [System.Drawing.FontStyle]::Bold)
$lblState.ForeColor = [System.Drawing.Color]::FromArgb(200, 160, 90)
$bar.Controls.Add($lblState)

$tabs = New-Object System.Windows.Forms.TabControl
$tabs.Dock = 'Fill'
$tabs.Font = New-Object System.Drawing.Font('Microsoft YaHei UI', 10)
$form.Controls.Add($tabs)
$tabs.BringToFront()

$tabAi = New-Object System.Windows.Forms.TabPage
$tabAi.Text = '工坊'
$tabAi.BackColor = [System.Drawing.Color]::FromArgb(20, 22, 26)
$tabs.TabPages.Add($tabAi)

$tabLog = New-Object System.Windows.Forms.TabPage
$tabLog.Text = '引擎日志'
$tabLog.BackColor = [System.Drawing.Color]::FromArgb(20, 22, 26)
$tabs.TabPages.Add($tabLog)

$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Multiline = $true
$logBox.ScrollBars = 'Vertical'
$logBox.ReadOnly = $true
$logBox.Dock = 'Fill'
$logBox.BackColor = [System.Drawing.Color]::FromArgb(14, 15, 18)
$logBox.ForeColor = [System.Drawing.Color]::FromArgb(120, 220, 150)
$logBox.Font = New-Object System.Drawing.Font('Consolas', 9)
$logBox.BorderStyle = 'None'
$tabLog.Controls.Add($logBox)

function Log([string]$m) {
  $line = '[' + (Get-Date -Format 'HH:mm:ss') + '] ' + $m
  $script:logBox.AppendText($line + "`r`n")
  $script:logBox.SelectionStart = $script:logBox.TextLength
  $script:logBox.ScrollToCaret()
}

# ---- 生图助手服务 ----
function Ensure-Assistant {
  if (Port-Open 8190) { return }
  Log '拉起生图助手（8190）…'
  if (Test-Path $AI_CMD) {
    Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c', ('"' + $AI_CMD + '"')) -WindowStyle Hidden | Out-Null
  } else {
    Start-Process -FilePath $PY -ArgumentList @('-u','assistant.py') -WorkingDirectory $WEBUI -WindowStyle Hidden | Out-Null
  }
}


# ---- Prompt Forge 的 ComfyUI 代理（8199）----
function Ensure-ComfyProxy {
  if (Port-Open 8199) { return }
  Log '拉起 Comfy 代理（8199）…'
  $proxy = Join-Path $ROOT 'tools\comfy_proxy.py'
  if (Test-Path $proxy) {
    Start-Process -FilePath $PY -ArgumentList @('-u', $proxy) -WindowStyle Hidden | Out-Null
  }
}

# ---- WebView2 ----
$script:wv = $null
function Init-WebView {
  if (-not $script:hasWv2) {
    $lbl = New-Object System.Windows.Forms.Label
    $lbl.Text = '缺少 WebView2 组件，请用浏览器打开 http://127.0.0.1:8190/tool'
    $lbl.Dock = 'Fill'; $lbl.TextAlign = 'MiddleCenter'
    $tabAi.Controls.Add($lbl)
    return
  }
  $nav = New-Object System.Windows.Forms.Panel
  $nav.Dock = 'Top'
  $nav.Height = 34
  $nav.BackColor = [System.Drawing.Color]::FromArgb(26, 28, 34)
  $tabAi.Controls.Add($nav)

  function New-NavBtn($text, $url) {
    $b = New-Object System.Windows.Forms.Button
    $b.Text = $text
    $b.AutoSize = $true
    $b.FlatStyle = 'Flat'
    $b.ForeColor = [System.Drawing.Color]::FromArgb(225, 228, 235)
    $b.BackColor = [System.Drawing.Color]::FromArgb(38, 41, 50)
    $b.Margin = New-Object System.Windows.Forms.Padding(4, 2, 4, 2)
    $b.Add_Click({ try { $script:wv.CoreWebView2.Navigate($url) } catch {} })
    $nav.Controls.Add($b)
    return $b
  }
  [void](New-NavBtn '工坊（主界面）' $FORGE)
  [void](New-NavBtn 'ComfyUI 原界面' $COMFYUI)
  $lblNav = New-Object System.Windows.Forms.Label
  $lblNav.Text = '   ← 主界面：提示词 / 资料库 / Studio / 出图 都在一页里'
  $lblNav.AutoSize = $true
  $lblNav.ForeColor = [System.Drawing.Color]::FromArgb(130, 138, 155)
  $lblNav.Margin = New-Object System.Windows.Forms.Padding(10, 8, 4, 2)
  $nav.Controls.Add($lblNav)

  $script:wv = New-Object Microsoft.Web.WebView2.WinForms.WebView2
  $script:wv.Dock = 'Fill'
  $tabAi.Controls.Add($script:wv)
  $script:wv.BringToFront()
  try {
    $udf = Join-Path $ROOT '_setup\wv2data'
    $t0 = [Microsoft.Web.WebView2.Core.CoreWebView2Environment]::CreateAsync($null, $udf, $null)
    while (-not $t0.IsCompleted) { [System.Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 60 }
    $wenv = $t0.Result
    $t = $script:wv.EnsureCoreWebView2Async($wenv)
    while (-not $t.IsCompleted) { [System.Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 60 }
    $script:wv.CoreWebView2.Navigate($FORGE)
    Log '工坊已载入（单页）'
  } catch {
    Log ('WebView2 初始化失败：' + $_.Exception.Message + '（可用浏览器打开 ' + $AI + '）')
  }
}

function Ensure-Ollama {
  # 扩写要用的本地模型服务：固定 11435 + D:\ollama-models
  if (Port-Open 11435 200) { return }
  if (-not (Test-Path $OLLAMA_CMD)) { Log '缺少 ollama 启动脚本（扩写会退化成规则直转）'; return }
  Log '拉起本地模型服务（Ollama 11435）…'
  Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c', ('"' + $OLLAMA_CMD + '"')) -WindowStyle Hidden | Out-Null
}

function Start-Comfy {
  $pid0 = Get-ComfyPid
  if ($pid0) { Log "引擎已在跑（PID $pid0）"; return }
  if (Port-Open 8188 200) { Log '引擎已在响应 8188，无需再启动'; return }
  if (-not (Test-Path $ENGINE_CMD)) { Log ('缺少启动脚本：' + $ENGINE_CMD); return }
  Ensure-Ollama
  Ensure-Assistant
  Ensure-ComfyProxy
  Log '启动 ComfyUI 引擎（约 30-60 秒，日志在 _setup\comfy.log）…'
  Remove-Item $PIDFILE -ErrorAction SilentlyContinue
  try {
    $p = Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c', ('"' + $ENGINE_CMD + '"')) -WindowStyle Hidden -PassThru
    Set-Content -Path $PIDFILE -Value $p.Id -Encoding ascii
    Log "已拉起 PID $($p.Id)（cmd 包装，python 是其子进程）"
  } catch {
    Log ('启动失败：' + $_.Exception.Message)
  }
}

function Stop-Comfy {
  $pid0 = Get-ComfyPid
  if ($pid0) {
    Log "停止 PID $pid0 …"
    & taskkill /PID $pid0 /T /F 2>$null | Out-Null
  } else {
    $c = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" -ErrorAction SilentlyContinue |
         Where-Object { $_.CommandLine -match 'main\.py' -or $_.CommandLine -match 'start_engine' } | Select-Object -First 1
    if ($c) { & taskkill /PID $c.ProcessId /T /F 2>$null | Out-Null }
    else { Log '引擎没在跑'; return }
  }
  Remove-Item $PIDFILE -ErrorAction SilentlyContinue
  Log '已停止，显存释放'
}

$btnStart.Add_Click({ Start-Comfy })
$btnStop.Add_Click({ Stop-Comfy })
$btnReload.Add_Click({ if ($script:wv -and $script:wv.CoreWebView2) { $script:wv.CoreWebView2.Navigate($AI + '?t=' + [DateTime]::Now.Ticks) } else { Ensure-Assistant } })
$btnOut.Add_Click({
  # 每次点击都重读配置，工坊里改过目录也能立刻跟上
  $d = Get-OutDir
  if (Test-Path -LiteralPath $d) {
    Start-Process explorer.exe -ArgumentList "`"$d`""
    Log ("打开出图目录 " + $d)
  } else {
    Log ("出图目录不存在，已回到默认：" + $d)
    Start-Process explorer.exe -ArgumentList "`"$(Join-Path $ROOT 'output')`""
  }
})
$btnDoc.Add_Click({ Start-Process (Join-Path $ROOT '使用教程.html') })

$script:readySince = $null
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 2500
$timer.Add_Tick({
  $up = Port-Open 8188 150
  if ($up) {
    if (-not $script:readySince) { $script:readySince = Get-Date; Log '引擎就绪 → 可以出图了' }
    $sec = [int]((Get-Date) - $script:readySince).TotalSeconds
    $script:lblState.Text = "● 引擎运行中    $API    已就绪 $sec 秒"
    $script:lblState.ForeColor = [System.Drawing.Color]::FromArgb(80, 220, 120)
    $script:btnStart.Enabled = $false
  } else {
    $script:readySince = $null
    $script:lblState.Text = '○ 引擎未运行（点左上角启动）'
    $script:lblState.ForeColor = [System.Drawing.Color]::FromArgb(200, 160, 90)
    $script:btnStart.Enabled = $true
  }
})

$form.Add_Shown({
  Log '工坊已开：左边「生图助手」是全部日常操作；引擎状态看上面那行字。'
  Ensure-Ollama
  Ensure-Assistant
  Ensure-ComfyProxy
  Init-WebView
  $timer.Start()
  if ($TestUi) {
    $script:auto = New-Object System.Windows.Forms.Timer
    $script:auto.Interval = 5000
    $script:auto.Add_Tick({ $script:auto.Stop(); $form.Close() })
    $script:auto.Start()
  }
})

$form.Add_FormClosing({ $timer.Stop() })

if ($TestStart) {
  Start-Comfy
  $t0 = Get-Date
  while (((Get-Date) - $t0).TotalSeconds -lt 110) {
    if (Port-Open 8188 300) { break }
    Start-Sleep -Milliseconds 800
  }
  $ok = Port-Open 8188 500
  Write-Output ('TEST-START ' + $(if ($ok) { 'OK' } else { 'FAIL' }))
  if (-not $ok -and (Test-Path $ERRLOG)) { Get-Content $ERRLOG -Tail 8 | ForEach-Object { Write-Output ('  err: ' + $_) } }
  return
}
if ($TestStop) {
  Stop-Comfy
  Start-Sleep -Seconds 2
  Write-Output ('TEST-STOP ' + $(if (Port-Open 8188 300) { 'FAIL' } else { 'OK' }))
  return
}
if ($SelfTest) {
  Log ('WebView2 程序集: ' + $script:hasWv2)
  Log ('引擎端口: ' + (Port-Open 8188))
  Log ('助手端口: ' + (Port-Open 8190))
  return
}

[void]$form.ShowDialog()
