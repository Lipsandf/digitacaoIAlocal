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
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "$TargetDir"
WshShell.Run chr(34) & "$TargetDir\venv\Scripts\python.exe" & chr(34) & " " & chr(34) & "$TargetDir\voice_typer.py" & chr(34), 0, False
Set WshShell = Nothing
"@
Set-Content -Path "$TargetDir\launcher.vbs" -Value $vbsContent -Encoding ascii -Force

# Dispara o aplicativo de forma desacoplada
$pythonExe = "$TargetDir\venv\Scripts\pythonw.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "$TargetDir\venv\Scripts\python.exe"
}
if (Test-Path $pythonExe) {
    Start-Process -FilePath $pythonExe -ArgumentList "`"$TargetDir\voice_typer.py`"" -WorkingDirectory "$TargetDir"
} else {
    $wscriptExe = "$env:SystemRoot\System32\wscript.exe"
    Start-Process -FilePath $wscriptExe -ArgumentList "`"$TargetDir\launcher.vbs`"" -WorkingDirectory "$TargetDir"
}
