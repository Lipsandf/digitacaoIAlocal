Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "         INSTALACAO DO DIGITADOR IA (VOZ)              " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Ola! Baixando o codigo do Github..." -ForegroundColor Green

$InstallDir = "$env:USERPROFILE\DigitadorIA"
if (Test-Path $InstallDir) {
    Remove-Item -Path $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

$zipPath = "$env:TEMP\DigitadorIA.zip"
Invoke-WebRequest -Uri "https://github.com/Lipsandf/digitacaoIAlocal/archive/refs/heads/main.zip" -OutFile $zipPath
Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
Move-Item -Path "$env:TEMP\digitacaoIAlocal-main\*" -Destination $InstallDir -Force
Remove-Item -Path "$env:TEMP\digitacaoIAlocal-main" -Recurse -Force
Remove-Item -Path $zipPath -Force

Set-Location $InstallDir

Write-Host "Verificando o Python..." -ForegroundColor Green
$pythonExe = "python"
$pythonOutput = python --version 2>&1 | Out-String
if ($LASTEXITCODE -ne 0 -or $pythonOutput -match "not found") {
    Write-Host "O Python não foi encontrado. Baixando e instalando silenciosamente..." -ForegroundColor Yellow
    Write-Host "Isso pode levar cerca de 1 a 2 minutos. Aguarde..." -ForegroundColor Yellow
    
    $pythonUrl = "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe"
    $installerPath = "$env:TEMP\python-installer.exe"
    Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath
    
    Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" -Wait
    Remove-Item -Path $installerPath -Force
    
    $pythonExe = "$env:USERPROFILE\AppData\Local\Programs\Python\Python311\python.exe"
    if (-not (Test-Path $pythonExe)) {
        Write-Host "ERRO CRITICO: A instalacao automatica do Python falhou." -ForegroundColor Red
        Write-Host "Por favor, baixe manualmente em python.org" -ForegroundColor Red
        exit
    }
    Write-Host "Python 3.11 instalado com sucesso!" -ForegroundColor Green
}

Write-Host "[1/4] Criando ambiente virtual isolado..." -ForegroundColor Green
& $pythonExe -m venv venv

if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "ERRO CRITICO: Falha ao criar a Virtual Environment do Python!" -ForegroundColor Red
    exit
}

Write-Host "[2/4] Baixando as dependencias do projeto (Isso pode demorar um pouco)..." -ForegroundColor Green
$pipCmd = ".\venv\Scripts\python.exe"
& $pipCmd -m pip install --upgrade pip --quiet
& $pipCmd -m pip install faster-whisper SpeechRecognition PyAudio soundfile nvidia-cublas-cu12 nvidia-cudnn-cu12 PyQt6 pynput pillow

Write-Host "[3/4] Criando arquivos de execucao invisivel..." -ForegroundColor Green
$VBS_PATH = "$InstallDir\launcher.vbs"
$vbsContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "$InstallDir\venv\Scripts\pythonw.exe" & chr(34) & " " & chr(34) & "$InstallDir\voice_typer.py" & chr(34), 0, False
Set WshShell = Nothing
"@
Set-Content -Path $VBS_PATH -Value $vbsContent

Write-Host "[4/4] Adicionando o programa ao Windows..." -ForegroundColor Green
$wshell = New-Object -ComObject WScript.Shell

# Atalho no Startup (Inicializar com o PC)
$shortcutPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Digitador_IA.lnk"
$shortcut = $wshell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$VBS_PATH`""
$shortcut.IconLocation = "$InstallDir\venv\Scripts\pythonw.exe"
$shortcut.WorkingDirectory = "$InstallDir"
$shortcut.Save()

# Atalho na Area de Trabalho
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutDesktopPath = "$desktopPath\Digitador_IA.lnk"
$shortcutDesktop = $wshell.CreateShortcut($shortcutDesktopPath)
$shortcutDesktop.TargetPath = "wscript.exe"
$shortcutDesktop.Arguments = "`"$VBS_PATH`""
$shortcutDesktop.IconLocation = "$InstallDir\venv\Scripts\pythonw.exe"
$shortcutDesktop.WorkingDirectory = "$InstallDir"
$shortcutDesktop.Save()

Write-Host "Iniciando o Digitador IA agora..." -ForegroundColor Green
Invoke-Item $VBS_PATH

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "          INSTALACAO CONCLUIDA COM SUCESSO!            " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "O Digitador IA agora vai iniciar junto com o Windows."
Write-Host "Procure o icone de um microfone roxo perto do relogio."
Write-Host "Pressione CTRL + ESPACO para comecar a ditar!"
Write-Host ""
