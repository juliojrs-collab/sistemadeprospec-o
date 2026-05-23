#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
 CAPTURA DE LEADS LOCAIS — Google Maps + Extracao de E-mail
==============================================================================
Sistema de prospeccao em 2 etapas:
  ETAPA 1  Raspa o Google Maps (nicho + cidade) -> nome, telefone, site,
           endereco, categoria, avaliacao, nº de reviews.
  ETAPA 2  Visita o site de cada empresa e extrai e-mails de contato.
  SAIDA    CSV pronto pra abrir no Excel / importar no CRM.

------------------------------------------------------------------------------
 COMO USAR
------------------------------------------------------------------------------
 1. Instale as dependencias (uma vez):
        pip install playwright requests
        playwright install chromium

 2. Edite o bloco CONFIG abaixo (suas buscas, cidade, limites).

 3. Rode:
        python captura_leads.py

------------------------------------------------------------------------------
 AVISOS HONESTOS
------------------------------------------------------------------------------
 - Raspar o Google Maps fere os Termos de Uso do Google. Use com bom senso,
   volume moderado e respeitando as pausas (evita bloqueio de IP).
 - Os SELETORES do Maps mudam de tempos em tempos. Quando o robo parar de
   achar dados, conserte na secao "SELETORES" — esta isolada de proposito.
 - Rode com HEADLESS=False na primeira vez pra VER o navegador trabalhando e
   resolver eventual tela de consentimento/captcha manualmente.
==============================================================================
"""

import csv
import re
import time
import random
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


# ==========================================================================
#  CONFIG  — edite aqui
# ==========================================================================
CONFIG = {
    # Cada item da lista e uma busca. Formato livre: "nicho cidade".
    "buscas": [
        "restaurantes em Curitiba PR",
        "clinicas odontologicas em Curitiba PR",
        "academias em Curitiba PR",
    ],

    # Quantas empresas tentar coletar POR busca (limite de seguranca).
    "max_por_busca": 40,

    # Visitar o site de cada empresa pra extrair e-mail? (deixa mais lento)
    "extrair_emails": True,

    # Mostrar o navegador (True = visivel, recomendado na 1a vez).
    "headless": False,

    # Arquivo de saida.
    "saida_csv": "leads.csv",

    # Pausas (segundos) pra parecer humano e nao tomar bloqueio.
    "pausa_min": 1.2,
    "pausa_max": 3.0,
}


# ==========================================================================
#  SELETORES  — conserte AQUI quando o Maps mudar o layout
# ==========================================================================
SEL = {
    # Painel rolavel com a lista de resultados
    "feed": 'div[role="feed"]',
    # Cada card de empresa dentro do feed (links de lugar)
    "cards": 'a[href*="/maps/place/"]',
    # --- dentro da ficha aberta (painel da direita) ---
    "nome": 'h1',
    "categoria": 'button[jsaction*="category"]',
    "rating": 'div.F7nice span[aria-hidden="true"]',
    "reviews": 'div.F7nice span[aria-label*="avaliac"], div.F7nice span[aria-label*="review"]',
    # Botoes de info usam data-item-id — jeito mais estavel de pegar tel/site/endereco
    "endereco": 'button[data-item-id="address"]',
    "site": 'a[data-item-id="authority"]',
    "telefone": 'button[data-item-id^="phone"]',
    # Botao de fechar a tela de consentimento de cookies (varia por regiao)
    "aceitar_cookies": 'button[aria-label*="Aceitar"], button[aria-label*="Accept all"]',
}


# Regex de e-mail + lixo a descartar (assets, libs, exemplos)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
EMAIL_LIXO = ("example.com", "sentry.", "wixpress.com", ".png", ".jpg",
              "@sentry", "domain.com", "email.com", "your-email")
PAGINAS_CONTATO = ("", "contato", "contact", "fale-conosco", "sobre", "about")


def pausa(cfg):
    """Espera um tempo aleatorio entre acoes."""
    time.sleep(random.uniform(cfg["pausa_min"], cfg["pausa_max"]))


def texto_seguro(locator):
    """Retorna o texto de um elemento ou '' se nao existir."""
    try:
        if locator.count() > 0:
            return (locator.first.inner_text() or "").strip()
    except Exception:
        pass
    return ""


def attr_seguro(locator, attr):
    """Retorna um atributo de um elemento ou '' se nao existir."""
    try:
        if locator.count() > 0:
            return (locator.first.get_attribute(attr) or "").strip()
    except Exception:
        pass
    return ""


# ==========================================================================
#  ETAPA 1 — Google Maps
# ==========================================================================
def rolar_feed(page, max_itens, cfg):
    """Rola o painel de resultados ate carregar itens suficientes (ou acabar)."""
    feed = page.locator(SEL["feed"])
    if feed.count() == 0:
        return
    ultimo_total = -1
    estagnado = 0
    while True:
        cards = page.locator(SEL["cards"])
        total = cards.count()
        if total >= max_itens:
            break
        if total == ultimo_total:
            estagnado += 1
            if estagnado >= 3:      # nao carrega mais nada -> fim da lista
                break
        else:
            estagnado = 0
        ultimo_total = total
        feed.first.evaluate("el => el.scrollBy(0, el.scrollHeight)")
        pausa(cfg)


def extrair_ficha(page):
    """Le os dados da ficha aberta no painel da direita."""
    pessoa = {
        "nome": texto_seguro(page.locator(SEL["nome"])),
        "categoria": texto_seguro(page.locator(SEL["categoria"])),
        "avaliacao": texto_seguro(page.locator(SEL["rating"])),
        "reviews": texto_seguro(page.locator(SEL["reviews"])),
        "endereco": texto_seguro(page.locator(SEL["endereco"])),
        "telefone": texto_seguro(page.locator(SEL["telefone"])),
        "site": attr_seguro(page.locator(SEL["site"]), "href"),
        "emails": "",
    }
    # Limpa o "reviews" deixando so o numero
    m = re.search(r"[\d.\,]+", pessoa["reviews"])
    pessoa["reviews"] = m.group(0) if m else ""
    return pessoa


def raspar_busca(page, termo, cfg):
    """Executa UMA busca no Maps e devolve a lista de empresas."""
    print(f"\n[BUSCA] {termo}")
    url = "https://www.google.com/maps/search/" + termo.replace(" ", "+")
    page.goto(url, timeout=60000)
    pausa(cfg)

    # Tela de cookies, se aparecer
    try:
        botao = page.locator(SEL["aceitar_cookies"])
        if botao.count() > 0:
            botao.first.click(timeout=4000)
            pausa(cfg)
    except Exception:
        pass

    try:
        page.wait_for_selector(SEL["feed"], timeout=15000)
    except PWTimeout:
        print("  ! Nao carregou a lista (consentimento/captcha?). Pulando.")
        return []

    rolar_feed(page, cfg["max_por_busca"], cfg)

    cards = page.locator(SEL["cards"])
    total = min(cards.count(), cfg["max_por_busca"])
    print(f"  -> {total} empresas encontradas. Abrindo fichas...")

    resultados = []
    for i in range(total):
        try:
            cards.nth(i).click(timeout=8000)
            pausa(cfg)
            page.wait_for_selector(SEL["nome"], timeout=8000)
            dados = extrair_ficha(page)
            dados["busca"] = termo
            if dados["nome"]:
                resultados.append(dados)
                print(f"     {i+1:>3}. {dados['nome']}  |  {dados['telefone'] or 's/ tel'}")
        except Exception as e:
            print(f"     {i+1:>3}. (erro ao ler ficha: {type(e).__name__})")
            continue
    return resultados


# ==========================================================================
#  ETAPA 2 — Extracao de e-mails dos sites
# ==========================================================================
def extrair_emails_do_site(url):
    """Visita a home + paginas de contato comuns e pesca e-mails."""
    if not url:
        return ""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/120.0 Safari/537.36"}
    achados = set()
    for sub in PAGINAS_CONTATO:
        alvo = urljoin(url if url.endswith("/") else url + "/", sub)
        try:
            r = requests.get(alvo, headers=headers, timeout=12)
            if r.status_code != 200:
                continue
            for mail in EMAIL_RE.findall(r.text):
                low = mail.lower()
                if not any(j in low for j in EMAIL_LIXO):
                    achados.add(low)
        except Exception:
            continue
        time.sleep(random.uniform(0.5, 1.2))
        if achados:        # achou na home/contato? ja basta, nao varre tudo
            break
    return "; ".join(sorted(achados))


# ==========================================================================
#  SAIDA / ORQUESTRACAO
# ==========================================================================
COLUNAS = ["busca", "nome", "categoria", "avaliacao", "reviews",
           "telefone", "endereco", "site", "emails"]


def salvar_csv(linhas, caminho):
    """Grava o CSV (UTF-8 com BOM pra abrir certinho no Excel)."""
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        for linha in linhas:
            w.writerow({c: linha.get(c, "") for c in COLUNAS})


def main():
    cfg = CONFIG
    vistos = set()          # dedup por (nome, telefone)
    leads = []

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=cfg["headless"])
        page = navegador.new_page(locale="pt-BR")
        page.set_default_timeout(15000)

        for termo in cfg["buscas"]:
            try:
                for emp in raspar_busca(page, termo, cfg):
                    chave = (emp["nome"].lower(), emp["telefone"])
                    if chave in vistos:
                        continue
                    vistos.add(chave)
                    leads.append(emp)
            except Exception as e:
                print(f"  ! Falha na busca '{termo}': {e}")
            pausa(cfg)

        navegador.close()

    print(f"\n[TOTAL] {len(leads)} empresas unicas coletadas.")

    if cfg["extrair_emails"]:
        print("\n[ETAPA 2] Buscando e-mails nos sites...")
        for i, lead in enumerate(leads, 1):
            if lead["site"]:
                lead["emails"] = extrair_emails_do_site(lead["site"])
                marca = lead["emails"] or "(nenhum)"
                print(f"  {i:>3}/{len(leads)}  {lead['nome'][:35]:<35}  {marca}")

    salvar_csv(leads, cfg["saida_csv"])
    com_email = sum(1 for l in leads if l["emails"])
    com_tel = sum(1 for l in leads if l["telefone"])
    print(f"\n[OK] Salvo em '{cfg['saida_csv']}'")
    print(f"     {len(leads)} empresas | {com_tel} com telefone | {com_email} com e-mail")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuario.")
        sys.exit(0)
