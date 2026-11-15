$ErrorActionPreference = 'Stop'
$diagnostics = Join-Path $PWD 'startup-diagnostics'
New-Item -ItemType Directory -Force -Path $diagnostics | Out-Null
$startTime = Get-Date
$repo = $env:GITHUB_REPOSITORY
$downloads = Join-Path $env:RUNNER_TEMP 'dub-download'
New-Item -ItemType Directory -Force -Path $downloads | Out-Null
gh release download v0.1.0-windows.1 --repo $repo --pattern '*Setup.exe' --pattern SHA256SUMS.txt --dir $downloads
if ($LASTEXITCODE -ne 0) { throw 'Release download failed' }
$setup = Get-ChildItem -LiteralPath $downloads -Filter '*Setup.exe' | Select-Object -First 1
$expected = ((Get-Content (Join-Path $downloads 'SHA256SUMS.txt') | Where-Object { $_ -like '*Setup.exe' }) -split '\s+')[0]
$actual = (Get-FileHash -LiteralPath $setup.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw 'Installer checksum mismatch' }
$installDir = Join-Path $env:RUNNER_TEMP 'Dub-Off Editor'
$installer = Start-Process -FilePath $setup.FullName -ArgumentList @('/S', "/D=$installDir") -PassThru
if (-not $installer.WaitForExit(180000)) { throw 'Installer timed out' }
"Installer exit code: $($installer.ExitCode)" | Tee-Object -FilePath (Join-Path $diagnostics 'installation.txt')
if ($installer.ExitCode -ne 0) { throw "Installer exited with $($installer.ExitCode)" }
Get-Process -Name 'Dub-Off Editor' -ErrorAction SilentlyContinue | Stop-Process -Force
$exe = Join-Path $installDir 'Dub-Off Editor.exe'
$files = Get-ChildItem -LiteralPath $installDir -Recurse -File
$files | Select-Object FullName,Length | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $diagnostics 'installed-files.json')
"Installed files: $($files.Count); main executable exists: $(Test-Path -LiteralPath $exe)" | Tee-Object -FilePath (Join-Path $diagnostics 'installation.txt') -Append
if (-not (Test-Path -LiteralPath $exe)) { throw 'Installer did not extract the main executable' }
$log = Join-Path $diagnostics 'electron.log'
$env:ELECTRON_ENABLE_LOGGING = '1'
$p = Start-Process -FilePath $exe -ArgumentList @('--enable-logging=file', "--log-file=`"$log`"", '--remote-debugging-port=9229') -PassThru -RedirectStandardOutput (Join-Path $diagnostics 'stdout.log') -RedirectStandardError (Join-Path $diagnostics 'stderr.log')
try {
    $pages = $null
    for ($i=0; $i -lt 45; $i++) {
        Start-Sleep -Seconds 1
        $p.Refresh()
        if ($p.HasExited) { throw "App exited before showing its page. Exit code: $($p.ExitCode)" }
        try { $pages = Invoke-RestMethod 'http://127.0.0.1:9229/json/list' -TimeoutSec 2 } catch { continue }
        if (@($pages | Where-Object { $_.type -eq 'page' -and $_.url -like 'file://*' }).Count -gt 0) { break }
    }
    $pages | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $diagnostics 'pages.json')
    $page = $pages | Where-Object { $_.type -eq 'page' -and $_.url -like 'file://*' } | Select-Object -First 1
    if (-not $page) { throw 'No editor page became available within the startup timeout' }
    $socket = [System.Net.WebSockets.ClientWebSocket]::new()
    $cancel = [System.Threading.CancellationTokenSource]::new(30000)
    $socket.ConnectAsync([Uri]$page.webSocketDebuggerUrl,$cancel.Token).GetAwaiter().GetResult()
    $expression = "(async()=>({title:document.title,state:document.readyState,text:document.body.innerText,bridge:typeof window.editor,status:window.editor?await window.editor.status():null}))()"
    $request = @{id=1;method='Runtime.evaluate';params=@{expression=$expression;returnByValue=$true;awaitPromise=$true}} | ConvertTo-Json -Depth 8 -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($request)
    $socket.SendAsync([ArraySegment[byte]]::new($bytes),[System.Net.WebSockets.WebSocketMessageType]::Text,$true,$cancel.Token).GetAwaiter().GetResult()
    $buffer = New-Object byte[] 65536
    $response = [System.Text.StringBuilder]::new()
    do {
        $received = $socket.ReceiveAsync([ArraySegment[byte]]::new($buffer),$cancel.Token).GetAwaiter().GetResult()
        [void]$response.Append([System.Text.Encoding]::UTF8.GetString($buffer,0,$received.Count))
    } while (-not $received.EndOfMessage)
    $text = $response.ToString()
    $text | Set-Content (Join-Path $diagnostics 'renderer.json')
    Write-Output $text
    $value = ($text | ConvertFrom-Json).result.result.value
    if (-not $value -or $value.bridge -ne 'object' -or [string]::IsNullOrWhiteSpace($value.text)) { throw 'The editor renderer or preload bridge did not initialize' }
    'Native Windows installer, startup, renderer, and IPC status checks passed.' | Set-Content (Join-Path $diagnostics 'result.txt')
} finally {
    if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log -Tail 80 }
    Get-Content (Join-Path $diagnostics 'stderr.log') -ErrorAction SilentlyContinue
    Get-Process -Name 'Dub-Off Editor' -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-WinEvent -FilterHashtable @{LogName='Application';StartTime=$startTime} -ErrorAction SilentlyContinue | Where-Object { $_.Message -like '*Dub-Off*' } | Select-Object TimeCreated,Id,ProviderName,Message | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $diagnostics 'windows-events.json')
}
