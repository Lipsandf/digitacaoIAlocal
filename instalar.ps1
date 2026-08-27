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
    $startupFolders = @(
        "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
        "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Startup"
    )
    $legacyStartupFiles = @(
        "DigitadorPorVoz.vbs", "DigitadorPorVoz.lnk", "DigitadorPorVoz.bat",
        "Digitador_IA.vbs", "Digitador_IA.lnk", "Digitador IA.lnk", "Digitador IA.vbs",
        "DigitadorIA.lnk", "DigitadorIA.vbs", "voice_typer.lnk", "voice_typer.vbs"
    )
    foreach ($sf in $startupFolders) {
        if (Test-Path $sf) {
            foreach ($lf in $legacyStartupFiles) {
                $targetFile = Join-Path $sf $lf
                if (Test-Path $targetFile) {
                    Remove-Item -Path $targetFile -Force -ErrorAction SilentlyContinue
                    Write-Host "  -> Removido atalho antigo: $targetFile" -ForegroundColor Cyan
                }
            }
        }
    }

    $desktopShortcuts = @(
        "$([Environment]::GetFolderPath('Desktop'))\Digitador IA.lnk",
        "$([Environment]::GetFolderPath('Desktop'))\Digitador_IA.lnk",
        "$env:USERPROFILE\Desktop\Digitador IA.lnk",
        "$env:USERPROFILE\Desktop\Digitador_IA.lnk",
        "$env:USERPROFILE\Area de Trabalho\Digitador IA.lnk",
        "$env:USERPROFILE\Area de Trabalho\Digitador_IA.lnk",
        "$env:PUBLIC\Desktop\Digitador IA.lnk",
        "$env:PUBLIC\Desktop\Digitador_IA.lnk"
    )
    foreach ($s in $desktopShortcuts) {
        if (Test-Path $s) {
            Remove-Item -Path $s -Force -ErrorAction SilentlyContinue
            Write-Host "  -> Removido atalho da Área de Trabalho: $s" -ForegroundColor Cyan
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
    Write-Host "[4/5] Apagando pastas de instalacao e venv..." -ForegroundColor Yellow
    $AllInstallDirs = @(
        "$env:ProgramFiles\DigitadorIA",
        "$env:LOCALAPPDATA\DigitadorIA",
        "$env:USERPROFILE\DigitadorIA"
    )
    foreach ($d in $AllInstallDirs) {
        if (Test-Path $d) {
            Remove-Item -Path $d -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  -> Pasta removida: $d" -ForegroundColor Green
        }
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

$InstallDir = "$env:ProgramFiles\DigitadorIA"
$LegacyDirs = @("$env:LOCALAPPDATA\DigitadorIA", "$env:USERPROFILE\DigitadorIA")
Write-Host ""
Write-Host "Iniciando instalacao oficial em: $InstallDir" -ForegroundColor Cyan

# Encerra processos antigos para liberar os arquivos
Stop-Process -Name "wscript" -ErrorAction SilentlyContinue
Stop-Process -Name "pythonw" -ErrorAction SilentlyContinue
Stop-Process -Name "python" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
}

# Concede permissao total na pasta de instalacao para que o programa possa atualizar e salvar arquivos
icacls "$InstallDir" /grant "*S-1-5-32-545:(OI)(CI)F" /T /C /Q 2>&1 | Out-Null
icacls "$InstallDir" /grant "Users:(OI)(CI)F" /T /C /Q 2>&1 | Out-Null
icacls "$InstallDir" /grant "Todos:(OI)(CI)F" /T /C /Q 2>&1 | Out-Null
icacls "$InstallDir" /grant "Everyone:(OI)(CI)F" /T /C /Q 2>&1 | Out-Null

# Migração Inteligente de pastas anteriores se existirem (preserva historico e configuracoes)
foreach ($leg in $LegacyDirs) {
    if ((Test-Path $leg) -and ($leg -ne $InstallDir)) {
        Write-Host "Detectada instalacao anterior em: $leg" -ForegroundColor Yellow
        Get-ChildItem -Path $leg -Filter "*.json" -ErrorAction SilentlyContinue | Copy-Item -Destination $InstallDir -Force
        Get-ChildItem -Path $leg -Filter "*.txt" -ErrorAction SilentlyContinue | Copy-Item -Destination $InstallDir -Force
    }
}

# Backup de seguranca do historico e configuracoes antes de baixar os arquivos novos
$backupConfig = $null
$backupHistory = $null
$backupModel = $null
if (Test-Path "$InstallDir\config.json") {
    $backupConfig = Get-Content -Raw -Path "$InstallDir\config.json"
}
if (Test-Path "$InstallDir\transcriptions_history.json") {
    $backupHistory = Get-Content -Raw -Path "$InstallDir\transcriptions_history.json"
}
if (Test-Path "$InstallDir\model_choice.txt") {
    $backupModel = Get-Content -Raw -Path "$InstallDir\model_choice.txt"
}

Write-Host "Baixando o codigo mais recente do Github..." -ForegroundColor Green
$zipPath = "$env:TEMP\DigitadorIA.zip"
Invoke-WebRequest -Uri "https://github.com/Lipsandf/digitacaoIAlocal/archive/refs/heads/main.zip" -OutFile $zipPath
Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
Copy-Item -Path "$env:TEMP\digitacaoIAlocal-main\*" -Destination $InstallDir -Recurse -Force
Remove-Item -Path $zipPath -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:TEMP\digitacaoIAlocal-main" -Recurse -Force -ErrorAction SilentlyContinue

# Restaura o historico e as configuracoes do usuario
if ($backupConfig) {
    Set-Content -Path "$InstallDir\config.json" -Value $backupConfig -Encoding utf8
}
if ($backupHistory) {
    Set-Content -Path "$InstallDir\transcriptions_history.json" -Value $backupHistory -Encoding utf8
}

Set-Location $InstallDir

# Salva a escolha do usuario (ou restaura a anterior se ja existia)
if ($modelChoiceText) {
    $modelChoiceText | Out-File -FilePath "$InstallDir\model_choice.txt" -Encoding ascii
} elseif ($backupModel) {
    Set-Content -Path "$InstallDir\model_choice.txt" -Value $backupModel -Encoding ascii
}

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

Write-Host "[1/4] Verificando e criando ambiente virtual isolado com Python 3.11..." -ForegroundColor Green
if (Test-Path "venv\Scripts\python.exe") {
    $testResult = & ".\venv\Scripts\python.exe" -c "import sys; print('OK')" 2>&1
    if ($testResult -notmatch "OK") {
        Write-Host "Ambiente virtual anterior corrompido. Recriando..." -ForegroundColor Yellow
        Remove-Item -Path "venv" -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path "venv\Scripts\python.exe")) {
    & $pythonExe -m venv venv
}

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
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = scriptDir
pyExe = scriptDir & "\venv\Scripts\pythonw.exe"
If Not fso.FileExists(pyExe) Then pyExe = scriptDir & "\venv\Scripts\python.exe"
WshShell.Run chr(34) & pyExe & chr(34) & " " & chr(34) & scriptDir & "\voice_typer.py" & chr(34), 0, False
Set WshShell = Nothing
"@
Set-Content -Path $VBS_PATH -Value $vbsContent -Encoding ascii

$wshell = New-Object -ComObject WScript.Shell

# Limpa TODOS os atalhos obsoletos ou quebrados do Startup (Usuário atual e Todos os Usuários)
$startupFolders = @(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Startup"
)
$legacyStartupFiles = @(
    "DigitadorPorVoz.vbs", "DigitadorPorVoz.lnk", "DigitadorPorVoz.bat",
    "Digitador_IA.vbs", "Digitador_IA.lnk", "Digitador IA.lnk", "Digitador IA.vbs",
    "DigitadorIA.lnk", "DigitadorIA.vbs", "voice_typer.lnk", "voice_typer.vbs"
)
foreach ($sf in $startupFolders) {
    if (Test-Path $sf) {
        foreach ($lf in $legacyStartupFiles) {
            $targetFile = Join-Path $sf $lf
            if (Test-Path $targetFile) {
                Remove-Item -Path $targetFile -Force -ErrorAction SilentlyContinue
                Write-Host "  -> Removido atalho antigo de inicializacao: $targetFile" -ForegroundColor Cyan
            }
        }
    }
}

# Remove entradas antigas no Registro Run se existirem
$regPaths = @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run"
)
foreach ($rp in $regPaths) {
    if (Test-Path $rp) {
        Get-ItemProperty -Path $rp -ErrorAction SilentlyContinue | Get-Member -MemberType NoteProperty | ForEach-Object {
            if ($_.Name -like "*Digitador*" -or $_.Name -like "*VoiceTyper*") {
                Remove-ItemProperty -Path $rp -Name $_.Name -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

# Atalho no Startup (Inicializar com o PC)
$userStartup = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$shortcutPath = "$userStartup\Digitador_IA.lnk"
$wscriptExe = "$env:SystemRoot\System32\wscript.exe"
if (-not (Test-Path $wscriptExe)) { $wscriptExe = "wscript.exe" }

$shortcut = $wshell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $wscriptExe
$shortcut.Arguments = "`"$VBS_PATH`""
$shortcut.IconLocation = "$InstallDir\icon.ico"
$shortcut.WorkingDirectory = "$InstallDir"
$shortcut.Save()

# Atalho na Area de Trabalho
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutDesktopPath = "$desktopPath\Digitador_IA.lnk"
$shortcutDesktop = $wshell.CreateShortcut($shortcutDesktopPath)
$shortcutDesktop.TargetPath = $wscriptExe
$shortcutDesktop.Arguments = "`"$VBS_PATH`""
$shortcutDesktop.IconLocation = "$InstallDir\icon.ico"
$shortcutDesktop.WorkingDirectory = "$InstallDir"
$shortcutDesktop.Save()

# Arquivo .bat de inicialização direta
$batContent = "@echo off`r`ncd /d `"$InstallDir`"`r`nwscript.exe `"$VBS_PATH`""
Set-Content -Path "$InstallDir\Iniciar_Digitador_IA.bat" -Value $batContent

Write-Host "Iniciando o Digitador IA agora..." -ForegroundColor Green
Start-Process -FilePath $wscriptExe -ArgumentList "`"$VBS_PATH`"" -WorkingDirectory "$InstallDir"

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "          INSTALACAO CONCLUIDA COM SUCESSO!            " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "O Digitador IA agora vai iniciar junto com o Windows."
Write-Host "Procure o icone de um microfone roxo perto do relogio."
Write-Host "Pressione CTRL + ESPACO para comecar a ditar!"
Write-Host ""
