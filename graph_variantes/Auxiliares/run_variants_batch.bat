@echo off
setlocal enabledelayedexpansion

set PROJECT_DIR=%~dp0
cd /d "%PROJECT_DIR%"

set ERROR_LOG=errors_batch.log
if exist "%ERROR_LOG%" del "%ERROR_LOG%"

set ROOT_DIR=%~1
if "%ROOT_DIR%"=="" set /p ROOT_DIR=Digite o caminho da pasta raiz: 

echo.
set /p PROVIDER=Digite o provider (gemini / maritaca): 
set /p API_KEY=Digite a API KEY: 

for /d %%D in ("%ROOT_DIR%\*") do (
    echo ---------------------------------
    echo Pasta: %%~nxD
    for %%F in ("%%D\*.txt") do (
        echo Processando: %%~nxF

        python -m graph_variantes.run_variants "%%F" %PROVIDER% %API_KEY%

        if errorlevel 1 (
            echo [ERRO] %%F >> "%ERROR_LOG%"
        ) else (
            echo    OK
        )
    )
)

pause