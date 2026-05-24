@echo off
chcp 65001 >nul
title Sistema de Captura de Leads
cls

echo.
echo  ================================================
echo   Abrindo a interface...
echo  ================================================
echo.

REM --- Verifica se o Python esta instalado ---
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=python
    goto :rodar
)

py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=py
    goto :rodar
)

echo  [ERRO] Python nao encontrado.
echo  Execute o PASSO_1_INSTALAR.bat primeiro.
echo.
pause
exit /b 1

:rodar
%PYTHON% interface.py
