# ==============================================================================
# DIGITADOR IA - ATUALIZADOR ULTRA-RAPIDO E SILENCIOSO (UPDATER)
# ==============================================================================
param (
    [string]$TargetDir = "$env:ProgramFiles\DigitadorIA"
)

$ErrorActionPreference = "SilentlyContinue"

if (-not (Test-Path $TargetDir)) {
    $TargetDir = "$PSScriptRoot"
}

# 1. Encerramento imediato do processo anterior
Stop-Process -Name "pythonw", "python" -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 200

# 2. Configura TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# 3. Download direto e ultra-rapido dos arquivos atualizados (milissegundos)
$ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$filesToUpdate = @(
    @{ Url = "https://lip.tec.br/voice_typer.py"; Fallback = "https://raw.githubusercontent.com/Lipsandf/digitacaoIAlocal/main/voice_typer.py"; Path = "$TargetDir\voice_typer.py" },
    @{ Url = "https://lip.tec.br/version.txt"; Fallback = "https://raw.githubusercontent.com/Lipsandf/digitacaoIAlocal/main/version.txt"; Path = "$TargetDir\version.txt" },
    @{ Url = "https://lip.tec.br/updater.ps1"; Fallback = "https://raw.githubusercontent.com/Lipsandf/digitacaoIAlocal/main/updater.ps1"; Path = "$TargetDir\updater.ps1" }
)

foreach ($f in $filesToUpdate) {
    $success = $false
    try {
        Invoke-WebRequest -Uri "$($f.Url)?t=$ts" -OutFile "$($f.Path).tmp" -UseBasicParsing -TimeoutSec 10
        if (Test-Path "$($f.Path).tmp") {
            Move-Item -Path "$($f.Path).tmp" -Destination $f.Path -Force
            $success = $true
        }
    } catch {}

    if (-not $success) {
        try {
            Invoke-WebRequest -Uri "$($f.Fallback)?t=$ts" -OutFile "$($f.Path).tmp" -UseBasicParsing -TimeoutSec 10
            if (Test-Path "$($f.Path).tmp") {
                Move-Item -Path "$($f.Path).tmp" -Destination $f.Path -Force
            }
        } catch {}
    }
}

# 4. Assegura launcher.vbs atualizado
$vbsContent = @"
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = scriptDir
pyExe = scriptDir & "\venv\Scripts\pythonw.exe"
If Not fso.FileExists(pyExe) Then pyExe = scriptDir & "\venv\Scripts\python.exe"
WshShell.Run chr(34) & pyExe & chr(34) & " " & chr(34) & scriptDir & "\voice_typer.py" & chr(34), 0, False
Set WshShell = Nothing
"@
Set-Content -Path "$TargetDir\launcher.vbs" -Value $vbsContent -Encoding ascii -Force

# 5. Reabre o aplicativo instantaneamente
$pyExe = "$TargetDir\venv\Scripts\pythonw.exe"
if (-not (Test-Path $pyExe)) { $pyExe = "$TargetDir\venv\Scripts\python.exe" }
$pyScript = "$TargetDir\voice_typer.py"

if (Test-Path $pyExe) {
    Start-Process -FilePath $pyExe -ArgumentList "`"$pyScript`"" -WorkingDirectory "$TargetDir"
} else {
    $wscriptExe = "$env:SystemRoot\System32\wscript.exe"
    Start-Process -FilePath $wscriptExe -ArgumentList "`"$TargetDir\launcher.vbs`"" -WorkingDirectory "$TargetDir"
}
