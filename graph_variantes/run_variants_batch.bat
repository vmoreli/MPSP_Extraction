@echo off
setlocal enabledelayedexpansion

REM ============================
REM CONFIGURAÇÕES
REM ============================

REM caminho do projeto (onde está graph_variantes)
set PROJECT_DIR=%~dp0
cd /d "%PROJECT_DIR%\.."

REM arquivo de log de erros
set ERROR_LOG=errors_batch.log

REM limpa log antigo
if exist "%ERROR_LOG%" del "%ERROR_LOG%"

REM ============================
REM INPUT DA PASTA RAIZ
REM ============================

set ROOT_DIR=%~1

if "%ROOT_DIR%"=="" (
    echo.
    set /p ROOT_DIR=Digite o caminho da pasta raiz com os processos: 
)

if not exist "%ROOT_DIR%" (
    echo.
    echo [ERRO] Pasta nao encontrada:
    echo %ROOT_DIR%
    pause
    exit /b 1
)

REM ============================
REM INPUT DA API KEY
REM ============================

echo.
set /p MARITACA_API_KEY=Digite sua MARITACA_API_KEY: 

if "%MARITACA_API_KEY%"=="" (
    echo.
    echo [ERRO] API key nao informada.
    pause
    exit /b 1
)

set MARITACA_API_KEY=%MARITACA_API_KEY%

REM ============================
REM INPUT DO MODELO
REM ============================

echo.
set /p MARITACA_MODEL=Digite o modelo (ex: sabia-3): 

if "%MARITACA_MODEL%"=="" (
    echo.
    echo [ERRO] Modelo nao informado.
    pause
    exit /b 1
)

set MARITACA_MODEL=%MARITACA_MODEL%

echo.
echo ===============================
echo INICIANDO BATCH MARITACA
echo Pasta raiz : %ROOT_DIR%
echo Modelo     : %MARITACA_MODEL%
echo ===============================
echo.

REM ============================
REM LOOP NAS SUBPASTAS
REM ============================
for /d %%D in ("%ROOT_DIR%\*") do (
    echo ---------------------------------
    echo Pasta: %%~nxD
    echo ---------------------------------

    REM loop em todos os .txt da subpasta
    for %%F in ("%%D\*.txt") do (
        echo Processando: %%~nxF

        python -m graph_variantes.run_variants "%%F"
        if errorlevel 1 (
            echo [ERRO] %%F >> "%ERROR_LOG%"
            echo    ^> erro ignorado, seguindo...
        ) else (
            echo    OK
        )
        echo.
    )
)

echo ===============================
echo FINALIZADO
echo ===============================

if exist "%ERROR_LOG%" (
    echo.
    echo Alguns arquivos falharam.
    echo Veja o log em: %ERROR_LOG%
) else (
    echo.
    echo Nenhum erro encontrado.
)

pause
