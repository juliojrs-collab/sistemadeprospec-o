@echo off
chcp 65001 >nul
title Sistema de Captura de Leads
cls

echo.
echo  ================================================
echo   PASSO 2 - CAPTURANDO LEADS
echo  ================================================
echo.
echo  O navegador vai abrir automaticamente.
echo  Nao feche esta janela enquanto estiver rodando.
echo.
echo  ------------------------------------------------
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
%PYTHON% captura_leads.py

echo.
echo  ================================================
echo   CONCLUIDO!
echo.
echo   Seu arquivo de leads foi salvo como:
echo   leads.csv  (nesta mesma pasta)
echo.
echo   Abra com Excel ou Google Sheets.
echo  ================================================
echo.
pause
