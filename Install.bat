@echo off
title Instalador - Digitador IA
color 0B
echo =======================================================
echo          INSTALACAO DO DIGITADOR IA (VOZ)
echo =======================================================
echo.
echo Ola! Vamos configurar o ambiente para voce...
echo.

:: Verifica se o Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo ERRO: O Python nao foi encontrado no sistema.
    echo Por favor, instale o Python 3.10 ou superior e marque a opcao "Add Python to PATH".
    pause
    exit /b
)

echo [1/5] Criando ambiente virtual isolado...
if not exist "venv" (
    python -m venv venv
)
echo Ambiente virtual criado com sucesso!
echo.

echo [2/5] Baixando as dependencias do projeto (Isso pode demorar um pouco)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install faster-whisper SpeechRecognition PyAudio soundfile nvidia-cublas-cu12 nvidia-cudnn-cu12 PyQt6 pynput pillow
echo Dependencias instaladas com sucesso!
echo.

echo [3/5] Criando arquivos de execucao invisivel...
set "SCRIPT_DIR=%~dp0"
set "VBS_PATH=%SCRIPT_DIR%launcher.vbs"

(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run chr^(34^) ^& "%SCRIPT_DIR%venv\Scripts\pythonw.exe" ^& chr^(34^) ^& " " ^& chr^(34^) ^& "%SCRIPT_DIR%voice_typer.py" ^& chr^(34^), 0, False
echo Set WshShell = Nothing
) > "%VBS_PATH%"
echo Lancador invisivel criado!
echo.

echo [4/5] Adicionando o programa a inicializacao do Windows...
:: Usa PowerShell para criar o atalho
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\Digitador_IA.lnk"
powershell -Command "$wshell = New-Object -ComObject WScript.Shell; $shortcut = $wshell.CreateShortcut('%SHORTCUT_PATH%'); $shortcut.TargetPath = 'wscript.exe'; $shortcut.Arguments = '""%VBS_PATH%""'; $shortcut.IconLocation = '%SCRIPT_DIR%venv\Scripts\pythonw.exe'; $shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $shortcut.Save()"
echo Atalho de inicializacao adicionado!
echo.

echo [5/5] Iniciando o Digitador IA agora...
wscript.exe "%VBS_PATH%"

color 0A
echo.
echo =======================================================
echo          INSTALACAO CONCLUIDA COM SUCESSO!
echo =======================================================
echo O Digitador IA agora vai iniciar junto com o Windows.
echo Procure o icone de um microfone na bandeja do seu sistema (perto do relogio).
echo Pressione CTRL + ESPACO para começar a ditar!
echo.
pause
