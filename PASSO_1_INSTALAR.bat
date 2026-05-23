@echo off
chcp 65001 >nul
title Instalador - Sistema de Captura de Leads
cls

echo.
echo  ================================================
echo   PASSO 1 - INSTALACAO DO SISTEMA
echo  ================================================
echo.
echo  Este processo instala tudo que e necessario.
echo  Faca isso uma unica vez.
echo.
echo  Aguarde, pode demorar alguns minutos...
echo  ------------------------------------------------
echo.

REM --- Verifica se o Python esta instalado ---
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=python
    goto :instalar
)

py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON=py
    goto :instalar
)

REM --- Python nao encontrado ---
echo  [ERRO] O Python nao foi encontrado no seu computador.
echo.
echo  Siga estes passos para instalar:
echo.
echo   1. O site de download vai abrir automaticamente
echo   2. Clique no botao amarelo "Download Python"
echo   3. Execute o arquivo baixado
echo   4. MUITO IMPORTANTE: marque a opcao
echo      "Add Python to PATH" antes de clicar em Install
echo   5. Conclua a instalacao
echo   6. Feche esta janela e clique em PASSO_1_INSTALAR.bat novamente
echo.
pause
start https://www.python.org/downloads/windows/
exit /b 1

:instalar
echo  [OK] Python encontrado!
echo.
echo  Instalando bibliotecas necessarias...
%PYTHON% -m pip install --upgrade pip --quiet
%PYTHON% -m pip install playwright requests

echo.
echo  Instalando o navegador automatizado (Chromium)...
echo  (esta parte pode demorar 2 a 5 minutos)
%PYTHON% -m playwright install chromium

echo.
echo  ================================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo.
echo   Proximo passo:
echo   Clique duas vezes em PASSO_2_RODAR.bat
echo  ================================================
echo.
pause
