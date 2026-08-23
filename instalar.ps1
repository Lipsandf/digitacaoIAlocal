$ProgressPreference = 'SilentlyContinue'
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "         DIGITADOR IA (VOZ) - INSTALADOR               " -ForegroundColor Yellow
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Selecione uma opcao:" -ForegroundColor White
Write-Host "[1] Instalar o Digitador IA" -ForegroundColor Green
Write-Host "[2] Desinstalar o Digitador IA (Apagar tudo)" -ForegroundColor Red
Write-Host ""
$choice = Read-Host "Digite o numero da opcao e aperte Enter (1 ou 2)"

if ($choice -eq "2") {
    Write-Host ""
    Write-Host "=======================================================" -ForegroundColor Red
    Write-Host "       INICIANDO DESINSTALACAO COMPLETA E LIMPEZA      " -ForegroundColor Yellow
    Write-Host "=======================================================" -ForegroundColor Red

    # 1. Encerra processos
    Write-Host "[1/5] Encerrando processos do Digitador IA em execucao..." -ForegroundColor Yellow
    Stop-Process -Name "wscript" -ErrorAction SilentlyContinue
    Stop-Process -Name "pythonw" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Write-Host "  -> Processos encerrados com sucesso." -ForegroundColor Green

    # 2. Apaga Atalhos (Startup, Área de Trabalho em todas as variações)
    Write-Host "[2/5] Removendo atalhos do sistema e Area de Trabalho..." -ForegroundColor Yellow
    $shortcuts = @(
        "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Digitador_IA.lnk",
        "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Digitador IA.lnk",
        "$([Environment]::GetFolderPath('Desktop'))\Digitador IA.lnk",
        "$([Environment]::GetFolderPath('Desktop'))\Digitador_IA.lnk",
        "$env:USERPROFILE\Desktop\Digitador IA.lnk",
        "$env:USERPROFILE\Area de Trabalho\Digitador IA.lnk"
    )
    foreach ($s in $shortcuts) {
        if (Test-Path $s) {
            Remove-Item -Path $s -Force -ErrorAction SilentlyContinue
            Write-Host "  -> Removido atalho: $s" -ForegroundColor Cyan
        }
    }

    # 3. Apaga Cache das Inteligências Artificiais baixadas (HuggingFace cache)
    Write-Host "[3/5] Removendo modelos de Inteligencia Artificial baixados (Cache HuggingFace)..." -ForegroundColor Yellow
    $hfCache = "$env:USERPROFILE\.cache\huggingface\hub"
    if (Test-Path $hfCache) {
        Get-ChildItem -Path $hfCache -Filter "*whisper*" -ErrorAction SilentlyContinue | ForEach-Object {
            Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  -> Modelo de IA removido: $($_.Name)" -ForegroundColor Cyan
        }
    }

    # 4. Apaga a pasta principal de instalação e o ambiente virtual (venv)
    Write-Host "[4/5] Apagando pasta de instalacao e venv ($env:USERPROFILE\DigitadorIA)..." -ForegroundColor Yellow
    $InstallDir = "$env:USERPROFILE\DigitadorIA"
    if (Test-Path $InstallDir) {
        Remove-Item -Path $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  -> Pasta do programa e venv totalmente removidas." -ForegroundColor Green
    }

    # 5. Apaga arquivos temporários de instalação no TEMP
    Write-Host "[5/5] Limpando arquivos temporarios..." -ForegroundColor Yellow
    $tempZip = "$env:TEMP\DigitadorIA.zip"
    if (Test-Path $tempZip) { Remove-Item -Path $tempZip -Force -ErrorAction SilentlyContinue }
    $tempFolder = "$env:TEMP\digitacaoIAlocal-main"
    if (Test-Path $tempFolder) { Remove-Item -Path $tempFolder -Recurse -Force -ErrorAction SilentlyContinue }
    Write-Host "  -> Arquivos temporarios limpos." -ForegroundColor Green

    Write-Host ""
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host "     DESINSTALACAO CONCLUIDA COM SUCESSO!              " -ForegroundColor Green
    Write-Host "=======================================================" -ForegroundColor Cyan
    Write-Host "Observacao: O Python e os Drivers de Video foram mantidos" -ForegroundColor Gray
    Write-Host "para a seguranca e estabilidade do seu sistema operacional." -ForegroundColor Gray
    Write-Host ""
    exit
}

if ($choice -ne "1") {
    Write-Host "Opcao invalida. Saindo..." -ForegroundColor Red
    exit
}

Write-Host ""
Write-Host "Qual Inteligencia Artificial voce deseja baixar?" -ForegroundColor Yellow
Write-Host "[1] IA Leve/Rapida (PADRAO) -> Funciona em qualquer PC e Notebook" -ForegroundColor Green
Write-Host "[2] IA Pesada/Ultra   (PRO) -> EXIGE placa de video NVIDIA potente" -ForegroundColor Cyan
Write-Host ""
$aiChoice = Read-Host "Digite o numero da opcao e aperte Enter (1 ou 2)"
$modelChoiceText = "small"
if ($aiChoice -eq "2") {
    $modelChoiceText = "large-v3"
}

$InstallDir = "$env:USERPROFILE\DigitadorIA"
Write-Host ""
Write-Host "Iniciando instalacao em: $InstallDir" -ForegroundColor Cyan
Write-Host "Ola! Baixando o codigo do Github..." -ForegroundColor Green

# Encerra processos antigos para liberar os arquivos
Stop-Process -Name "wscript" -ErrorAction SilentlyContinue
Stop-Process -Name "pythonw" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
} else {
    # Apaga o conteudo interno para nao falhar se o terminal estiver aberto na pasta
    Get-ChildItem -Path $InstallDir -Exclude "venv" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

$zipPath = "$env:TEMP\DigitadorIA.zip"
Invoke-WebRequest -Uri "https://github.com/Lipsandf/digitacaoIAlocal/archive/refs/heads/main.zip" -OutFile $zipPath
Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
Move-Item -Path "$env:TEMP\digitacaoIAlocal-main\*" -Destination $InstallDir -Force
Remove-Item -Path $zipPath -Force
Remove-Item -Path "$env:TEMP\digitacaoIAlocal-main" -Recurse -Force

Set-Location $InstallDir

# Salva a escolha do usuario
$modelChoiceText | Out-File -FilePath "$InstallDir\model_choice.txt" -Encoding ascii

Write-Host "Escaneando o Hardware da maquina..." -ForegroundColor Green
$gpus = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
$gpuType = "cpu"
foreach ($g in $gpus) {
    if ($g -like "*NVIDIA*") {
        $gpuType = "nvidia"
        break
    }
    if ($g -like "*AMD*" -or $g -like "*Radeon*") {
        $gpuType = "amd"
    }
}

Write-Host "Hardware detectado: Placa de Video -> $gpuType" -ForegroundColor Cyan
$gpuType | Out-File -FilePath "$InstallDir\hardware.txt" -Encoding ascii

Write-Host "Verificando a versao do Python..." -ForegroundColor Green
$pythonExe = "python"
$pythonOutput = python --version 2>&1 | Out-String

# Se nao tiver python ou se NAO for versao 3.11, força o download do Python 3.11.8
if ($LASTEXITCODE -ne 0 -or $pythonOutput -notmatch "3\.11") {
    Write-Host "Garantindo ambiente estavel com Python 3.11.8..." -ForegroundColor Yellow
    Write-Host "Isso pode levar cerca de 1 a 2 minutos. Aguarde..." -ForegroundColor Yellow
    
    $pythonUrl = "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe"
    $installerPath = "$env:TEMP\python-installer.exe"
    Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath
    
    Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" -Wait
    Remove-Item -Path $installerPath -Force
    
    $pythonExe = "$env:USERPROFILE\AppData\Local\Programs\Python\Python311\python.exe"
    if (-not (Test-Path $pythonExe)) {
        Write-Host "ERRO CRITICO: A instalacao automatica do Python 3.11 falhou." -ForegroundColor Red
        Write-Host "Por favor, baixe manualmente em python.org" -ForegroundColor Red
        exit
    }
    Write-Host "Python 3.11 instalado com sucesso!" -ForegroundColor Green
}

Write-Host "[1/4] Criando ambiente virtual isolado com Python 3.11..." -ForegroundColor Green
& $pythonExe -m venv venv

if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "ERRO CRITICO: Falha ao criar a Virtual Environment do Python!" -ForegroundColor Red
    exit
}

Write-Host "[2/4] Baixando as dependencias otimizadas para ($gpuType)..." -ForegroundColor Green
$pipCmd = ".\venv\Scripts\python.exe"
& $pipCmd -m pip install --upgrade pip --quiet

if ($gpuType -eq "nvidia") {
    Write-Host "Baixando drivers de aceleracao NVIDIA CUDA..." -ForegroundColor Cyan
    & $pipCmd -m pip install faster-whisper SpeechRecognition PyAudio soundfile nvidia-cublas-cu12 nvidia-cudnn-cu12 PyQt6 pynput pillow
} elseif ($gpuType -eq "amd") {
    Write-Host "Baixando drivers de aceleracao AMD DirectML..." -ForegroundColor Cyan
    & $pipCmd -m pip install SpeechRecognition PyAudio soundfile PyQt6 pynput pillow onnxruntime-directml optimum[onnxruntime] torch
} else {
    Write-Host "Baixando pacote leve otimizado para CPU..." -ForegroundColor Cyan
    & $pipCmd -m pip install faster-whisper SpeechRecognition PyAudio soundfile PyQt6 pynput pillow
}

Write-Host "[3/4] Baixando o modelo de IA ($modelChoiceText) no seu PC..." -ForegroundColor Green
$env:PYTHONUNBUFFERED = "1"
& $pipCmd "$InstallDir\download_model.py" $modelChoiceText
if ($LASTEXITCODE -ne 0) {
    Write-Host "AVISO: Houve um problema ao baixar a IA antecipadamente." -ForegroundColor Yellow
}

Write-Host "[4/4] Criando inicializador invisivel e atalhos..." -ForegroundColor Green
$VBS_PATH = "$InstallDir\launcher.vbs"
$vbsContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "$InstallDir"
WshShell.Run chr(34) & "$InstallDir\venv\Scripts\pythonw.exe" & chr(34) & " " & chr(34) & "$InstallDir\voice_typer.py" & chr(34), 0, False
Set WshShell = Nothing
"@
Set-Content -Path $VBS_PATH -Value $vbsContent

$wshell = New-Object -ComObject WScript.Shell

# Atalho no Startup (Inicializar com o PC)
$shortcutPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Digitador_IA.lnk"
$shortcut = $wshell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$VBS_PATH`""
$shortcut.IconLocation = "$InstallDir\icon.ico"
$shortcut.WorkingDirectory = "$InstallDir"
$shortcut.Save()

# Atalho na Area de Trabalho
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutDesktopPath = "$desktopPath\Digitador_IA.lnk"
$shortcutDesktop = $wshell.CreateShortcut($shortcutDesktopPath)
$shortcutDesktop.TargetPath = "wscript.exe"
$shortcutDesktop.Arguments = "`"$VBS_PATH`""
$shortcutDesktop.IconLocation = "$InstallDir\icon.ico"
$shortcutDesktop.WorkingDirectory = "$InstallDir"
$shortcutDesktop.Save()

# Arquivo .bat de inicialização direta
$batContent = "@echo off`r`ncd /d `"$InstallDir`"`r`nwscript.exe `"$VBS_PATH`""
Set-Content -Path "$InstallDir\Iniciar_Digitador_IA.bat" -Value $batContent

Write-Host "Iniciando o Digitador IA agora..." -ForegroundColor Green
Start-Process -FilePath "wscript.exe" -ArgumentList "`"$VBS_PATH`"" -WorkingDirectory "$InstallDir"

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "          INSTALACAO CONCLUIDA COM SUCESSO!            " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "O Digitador IA agora vai iniciar junto com o Windows."
Write-Host "Procure o icone de um microfone roxo perto do relogio."
Write-Host "Pressione CTRL + ESPACO para comecar a ditar!"
Write-Host ""
