# ==============================================================================
# DIGITADOR IA - ATUALIZADOR AUTOMATICO E SILENCIOSO (UPDATER)
# ==============================================================================
param (
    [string]$TargetDir = "$env:ProgramFiles\DigitadorIA"
)

$ErrorActionPreference = "SilentlyContinue"

if (-not (Test-Path $TargetDir)) {
    $TargetDir = "$PSScriptRoot"
}

# Auto-elevacao para Administrador se necessario para gravar em Program Files
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin -and ($TargetDir -like "*Program Files*")) {
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`" -TargetDir `"$TargetDir`"" -Verb RunAs
    exit
}

# 1. Aguarda o aplicativo principal fechar completamente para liberar os arquivos
for ($i = 0; $i -lt 15; $i++) {
    $procs = Get-Process -Name "pythonw", "python" -ErrorAction SilentlyContinue
    if (-not $procs) { break }
    Stop-Process -Name "pythonw" -Force -ErrorAction SilentlyContinue
    Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 400
}

# 2. Backup de seguranca das configuracoes, chave Groq e historico
$backupConfig = $null
$backupHistory = $null
$backupModel = $null

if (Test-Path "$TargetDir\config.json") {
    $backupConfig = Get-Content -Raw -Path "$TargetDir\config.json" -Encoding utf8
}
if (Test-Path "$TargetDir\transcriptions_history.json") {
    $backupHistory = Get-Content -Raw -Path "$TargetDir\transcriptions_history.json" -Encoding utf8
}
if (Test-Path "$TargetDir\model_choice.txt") {
    $backupModel = Get-Content -Raw -Path "$TargetDir\model_choice.txt" -Encoding ascii
}

# 3. Baixa o pacote completo mais recente do GitHub
$zipPath = "$env:TEMP\DigitadorIA_update.zip"
$extractPath = "$env:TEMP\DigitadorIA_update_extracted"

Remove-Item -Path $zipPath -Force -ErrorAction SilentlyContinue
Remove-Item -Path $extractPath -Recurse -Force -ErrorAction SilentlyContinue

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri "https://github.com/Lipsandf/digitacaoIAlocal/archive/refs/heads/main.zip" -OutFile $zipPath -UseBasicParsing -TimeoutSec 30
    Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
    
    $sourceDir = "$extractPath\digitacaoIAlocal-main"
    if (Test-Path $sourceDir) {
        # Copia todos os arquivos atualizados preservando o ambiente virtual venv existente
        Get-ChildItem -Path $sourceDir -Exclude "venv" | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $TargetDir -Recurse -Force
        }
    }
} catch {
    Write-Host "Falha ao baixar update: $_"
}

# 4. Limpeza de arquivos temporarios de download
Remove-Item -Path $zipPath -Force -ErrorAction SilentlyContinue
Remove-Item -Path $extractPath -Recurse -Force -ErrorAction SilentlyContinue

# 5. Restaura o historico e as configuracoes do usuario
if ($backupConfig) {
    Set-Content -Path "$TargetDir\config.json" -Value $backupConfig -Encoding utf8
}
if ($backupHistory) {
    Set-Content -Path "$TargetDir\transcriptions_history.json" -Value $backupHistory -Encoding utf8
}
if ($backupModel) {
    Set-Content -Path "$TargetDir\model_choice.txt" -Value $backupModel -Encoding ascii
}

# 6. Concede permissao total na pasta
icacls "$TargetDir" /grant "*S-1-5-32-545:(OI)(CI)F" /T /C /Q 2>&1 | Out-Null
icacls "$TargetDir" /grant "Users:(OI)(CI)F" /T /C /Q 2>&1 | Out-Null
icacls "$TargetDir" /grant "Todos:(OI)(CI)F" /T /C /Q 2>&1 | Out-Null
icacls "$TargetDir" /grant "Everyone:(OI)(CI)F" /T /C /Q 2>&1 | Out-Null

# 7. Recria o launcher.vbs e reabre o aplicativo obrigatoriamente
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

# Limpa atalhos legados do Startup
$startupFolders = @(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Startup"
)
$legacyStartupFiles = @(
    "DigitadorPorVoz.vbs", "DigitadorPorVoz.lnk", "DigitadorPorVoz.bat",
    "Digitador_IA.vbs", "Digitador IA.lnk", "Digitador IA.vbs",
    "DigitadorIA.lnk", "DigitadorIA.vbs", "voice_typer.lnk", "voice_typer.vbs"
)
foreach ($sf in $startupFolders) {
    if (Test-Path $sf) {
        foreach ($lf in $legacyStartupFiles) {
            $tf = Join-Path $sf $lf
            if (Test-Path $tf) {
                Remove-Item -Path $tf -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

# Atualiza atalho do Startup
$wshell = New-Object -ComObject WScript.Shell
$userStartup = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$shortcutPath = "$userStartup\Digitador_IA.lnk"
$wscriptExe = "$env:SystemRoot\System32\wscript.exe"
if (-not (Test-Path $wscriptExe)) { $wscriptExe = "wscript.exe" }
$shortcut = $wshell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $wscriptExe
$shortcut.Arguments = "`"$TargetDir\launcher.vbs`""
$shortcut.IconLocation = "$TargetDir\icon.ico"
$shortcut.WorkingDirectory = "$TargetDir"
# 8. Reabre o aplicativo garantindo execucao imediata na sessao do usuario
$pyExe = "$TargetDir\venv\Scripts\pythonw.exe"
if (-not (Test-Path $pyExe)) { $pyExe = "$TargetDir\venv\Scripts\python.exe" }
$pyScript = "$TargetDir\voice_typer.py"

if (Test-Path $pyExe) {
    Start-Process -FilePath $pyExe -ArgumentList "`"$pyScript`"" -WorkingDirectory "$TargetDir"
} else {
    Start-Process -FilePath $wscriptExe -ArgumentList "`"$TargetDir\launcher.vbs`"" -WorkingDirectory "$TargetDir"
}
