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

echo [1/5] Verificando e criando ambiente virtual isolado...
if exist "venv" (
    venv\Scripts\python.exe -c "import sys" >nul 2>&1
    if %errorlevel% neq 0 (
        echo Ambiente virtual anterior corrompido. Recriando venv...
        rmdir /s /q "venv"
    )
)
if not exist "venv" (
    python -m venv venv
)
echo Ambiente virtual configurado com sucesso!
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
echo Set fso = CreateObject^("Scripting.FileSystemObject"^)
echo scriptDir = fso.GetParentFolderName^(WScript.ScriptFullName^)
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.CurrentDirectory = scriptDir
echo pyExe = scriptDir ^& "\venv\Scripts\pythonw.exe"
echo If Not fso.FileExists^(pyExe^) Then pyExe = scriptDir ^& "\venv\Scripts\python.exe"
echo WshShell.Run chr^(34^) ^& pyExe ^& chr^(34^) ^& " " ^& chr^(34^) ^& scriptDir ^& "\voice_typer.py" ^& chr^(34^), 0, False
echo Set WshShell = Nothing
) > "%VBS_PATH%"
echo Lancador invisivel criado!
echo.

echo [4/5] Adicionando o programa a inicializacao do Windows...
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP_FOLDER%\DigitadorPorVoz.vbs" del /f /q "%STARTUP_FOLDER%\DigitadorPorVoz.vbs"
if exist "%STARTUP_FOLDER%\DigitadorPorVoz.lnk" del /f /q "%STARTUP_FOLDER%\DigitadorPorVoz.lnk"
if exist "%STARTUP_FOLDER%\Digitador_IA.vbs" del /f /q "%STARTUP_FOLDER%\Digitador_IA.vbs"
if exist "%STARTUP_FOLDER%\Digitador_IA.lnk" del /f /q "%STARTUP_FOLDER%\Digitador_IA.lnk"
if exist "%STARTUP_FOLDER%\Digitador IA.lnk" del /f /q "%STARTUP_FOLDER%\Digitador IA.lnk"
if exist "%STARTUP_FOLDER%\DigitadorIA.lnk" del /f /q "%STARTUP_FOLDER%\DigitadorIA.lnk"
if exist "%STARTUP_FOLDER%\voice_typer.lnk" del /f /q "%STARTUP_FOLDER%\voice_typer.lnk"

set "SHORTCUT_PATH=%STARTUP_FOLDER%\Digitador_IA.lnk"
powershell -NoProfile -Command "$wshell = New-Object -ComObject WScript.Shell; $shortcut = $wshell.CreateShortcut('%SHORTCUT_PATH%'); $shortcut.TargetPath = 'wscript.exe'; $shortcut.Arguments = '""%VBS_PATH%""'; $shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $shortcut.Save()"
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
