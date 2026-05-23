#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
 CAPTURA DE LEADS LOCAIS — Google Maps + Dados de Contato
==============================================================================
Sistema de prospecção em 2 etapas:
  ETAPA 1  Raspa o Google Maps (nicho + cidade) → nome, telefone, site,
           endereço, categoria, avaliação, nº de reviews.
           Gera link direto de WhatsApp a partir do telefone capturado.
  ETAPA 2  Visita o site de cada empresa e extrai:
             • E-mails de contato
             • Perfil do Instagram
             • Página do Facebook
             • Nome do responsável/proprietário (quando disponível no site)
  SAÍDA    CSV pronto pra abrir no Excel / importar no CRM.
           Inclui colunas em branco pra controle da equipe:
           status, atribuido_para, data_contato, observacoes.

------------------------------------------------------------------------------
 COMO USAR
------------------------------------------------------------------------------
 1. Instale as dependências (uma vez):
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
 - Os SELETORES do Maps mudam de tempos em tempos. Quando o robô parar de
   achar dados, conserte na seção "SELETORES" — está isolada de propósito.
 - Rode com HEADLESS=False na primeira vez pra VER o navegador trabalhando e
   resolver eventual tela de consentimento/captcha manualmente.
==============================================================================
"""

import csv
import re
import time
import random
import sys
from urllib.parse import urljoin

import requests
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


# ==========================================================================
#  CONFIG  — edite aqui
# ==========================================================================
CONFIG = {
    # Cada item da lista é uma busca. Formato livre: "nicho cidade".
    "buscas": [
        "restaurantes em Curitiba PR",
        "clinicas odontologicas em Curitiba PR",
        "academias em Curitiba PR",
    ],

    # Quantas empresas tentar coletar POR busca (limite de segurança).
    "max_por_busca": 40,

    # Visitar o site de cada empresa pra extrair e-mail, redes sociais
    # e nome do responsável? (deixa mais lento, mas traz muito mais dados)
    "extrair_dados_site": True,

    # Mostrar o navegador (True = visível, recomendado na 1ª vez).
    "headless": False,

    # Arquivo de saída.
    "saida_csv": "leads.csv",

    # Pausas (segundos) pra parecer humano e não tomar bloqueio.
    "pausa_min": 1.2,
    "pausa_max": 3.0,
}


# ==========================================================================
#  SELETORES  — conserte AQUI quando o Maps mudar o layout
# ==========================================================================
SEL = {
    # Painel rolável com a lista de resultados
    "feed": 'div[role="feed"]',
    # Cada card de empresa dentro do feed (links de lugar)
    "cards": 'a[href*="/maps/place/"]',
    # --- dentro da ficha aberta (painel da direita) ---
    "nome": "h1",
    "categoria": 'button[jsaction*="category"]',
    "rating": 'div.F7nice span[aria-hidden="true"]',
    "reviews": 'div.F7nice span[aria-label*="avaliac"], div.F7nice span[aria-label*="review"]',
    # Botões de info usam data-item-id — jeito mais estável de pegar tel/site/endereço
    "endereco": 'button[data-item-id="address"]',
    "site":     'a[data-item-id="authority"]',
    "telefone": 'button[data-item-id^="phone"]',
    # Botão de fechar a tela de consentimento de cookies (varia por região)
    "aceitar_cookies": 'button[aria-label*="Aceitar"], button[aria-label*="Accept all"]',
}


# ==========================================================================
#  PADRÕES DE EXTRAÇÃO
# ==========================================================================

# E-mail + lixo a descartar (assets, libs, exemplos)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
EMAIL_LIXO = (
    "example.com", "sentry.", "wixpress.com", ".png", ".jpg",
    "@sentry", "domain.com", "email.com", "your-email",
)

# Instagram — captura o handle (ex.: instagram.com/minhaempresa)
INSTAGRAM_RE = re.compile(
    r'instagram\.com/([A-Za-z0-9][A-Za-z0-9_.]{1,29})(?:[/?"\'\s<]|$)',
    re.IGNORECASE,
)
# Caminhos próprios do Instagram que não são perfis de empresa
INSTAGRAM_LIXO = frozenset([
    "p", "reel", "tv", "stories", "highlights", "explore",
    "reels", "accounts", "oauth", "_u", "share", "sharer",
    "direct", "ar", "developer",
])

# Facebook — captura o slug da página (ex.: facebook.com/minhaempresa)
FACEBOOK_RE = re.compile(
    r'facebook\.com/([A-Za-z0-9][A-Za-z0-9._-]{2,59})(?:[/?"\'\s<]|$)',
    re.IGNORECASE,
)
# Caminhos próprios do Facebook que não são páginas de empresa
FACEBOOK_LIXO = frozenset([
    "sharer", "share", "login", "dialog", "plugins", "policies",
    "policy", "legal", "help", "about", "ads", "business", "groups",
    "events", "marketplace", "profile.php", "photo.php", "video.php",
    "permalink.php", "watch", "gaming", "pages", "hashtag",
    "friends", "messages", "notifications", "bookmarks",
])

# Nome do responsável/proprietário — padrão "Cargo: Nome Sobrenome"
# Inline flag (?i:...) aplica case-insensitive só nas palavras de cargo;
# o grupo de captura continua sensível a maiúsculas (busca nomes com inicial maiúscula).
_MAI = "A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇÀÜ"
_MIN = "a-záéíóúâêîôûãõçàü"
RESPONSAVEL_RE = re.compile(
    rf"(?i:(?:diretor[a]?|fundador[a]?|proprietári[oa]|gerente|ceo|cto|sóci[oa]|"
    rf"responsável|coordenador[a]?|presidente)\s*[:\-]?\s*)"
    rf"([{_MAI}][{_MIN}]+(?:\s[{_MAI}][{_MIN}]+){{1,3}})"
)

# Páginas visitadas no site em busca de dados de contato
PAGINAS_CONTATO = (
    "",             # home
    "contato",
    "contact",
    "fale-conosco",
    "sobre",
    "about",
    "quem-somos",
    "equipe",
    "team",
)

# Colunas do CSV final
COLUNAS = [
    # — dados do Google Maps —
    "busca", "nome", "categoria", "avaliacao", "reviews",
    "telefone", "whatsapp",
    "endereco", "site",
    # — dados extraídos do site —
    "instagram", "facebook",
    "emails", "responsavel",
    # — preenchidas pela equipe de prospecção —
    "status", "atribuido_para", "data_contato", "observacoes",
]


# ==========================================================================
#  UTILITÁRIOS
# ==========================================================================

def pausa(cfg):
    """Espera um tempo aleatório entre ações."""
    time.sleep(random.uniform(cfg["pausa_min"], cfg["pausa_max"]))


def texto_seguro(locator):
    """Retorna o texto de um elemento ou '' se não existir."""
    try:
        if locator.count() > 0:
            return (locator.first.inner_text() or "").strip()
    except Exception:
        pass
    return ""


def attr_seguro(locator, attr):
    """Retorna um atributo de um elemento ou '' se não existir."""
    try:
        if locator.count() > 0:
            return (locator.first.get_attribute(attr) or "").strip()
    except Exception:
        pass
    return ""


def gerar_whatsapp(telefone):
    """
    Gera link wa.me a partir de um número de telefone brasileiro.

    Entrada: qualquer formato — (41) 99999-8888, +55 41 99999-8888, etc.
    Saída:   https://wa.me/5541999998888   (ou '' se inválido)
    """
    if not telefone:
        return ""
    nums = re.sub(r"\D", "", telefone)
    if len(nums) < 8:
        return ""
    # Adiciona código do país +55 se necessário
    if nums.startswith("55") and len(nums) >= 12:
        pass                          # já tem código do país
    elif nums.startswith("0"):
        nums = "55" + nums[1:]        # remove 0 de discagem longa
    else:
        nums = "55" + nums
    return f"https://wa.me/{nums}"


# ==========================================================================
#  ETAPA 1 — Google Maps
# ==========================================================================

def rolar_feed(page, max_itens, cfg):
    """Rola o painel de resultados até carregar itens suficientes (ou acabar)."""
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
            if estagnado >= 3:      # não carrega mais nada → fim da lista
                break
        else:
            estagnado = 0
        ultimo_total = total
        feed.first.evaluate("el => el.scrollBy(0, el.scrollHeight)")
        pausa(cfg)


def extrair_ficha(page):
    """Lê os dados da ficha aberta no painel da direita."""
    telefone = texto_seguro(page.locator(SEL["telefone"]))
    pessoa = {
        "nome":      texto_seguro(page.locator(SEL["nome"])),
        "categoria": texto_seguro(page.locator(SEL["categoria"])),
        "avaliacao": texto_seguro(page.locator(SEL["rating"])),
        "reviews":   texto_seguro(page.locator(SEL["reviews"])),
        "endereco":  texto_seguro(page.locator(SEL["endereco"])),
        "telefone":  telefone,
        "whatsapp":  gerar_whatsapp(telefone),
        "site":      attr_seguro(page.locator(SEL["site"]), "href"),
        # preenchidos na Etapa 2
        "emails":      "",
        "instagram":   "",
        "facebook":    "",
        "responsavel": "",
    }
    # Limpa "reviews" deixando só o número
    m = re.search(r"[\d.,]+", pessoa["reviews"])
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
        print("  ! Não carregou a lista (consentimento/captcha?). Pulando.")
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
                wpp = "✓ wpp" if dados["whatsapp"] else "s/ wpp"
                print(
                    f"     {i+1:>3}. {dados['nome']:<40} "
                    f"{dados['telefone'] or 's/ tel'}  {wpp}"
                )
        except Exception as e:
            print(f"     {i+1:>3}. (erro ao ler ficha: {type(e).__name__})")
            continue
    return resultados


# ==========================================================================
#  ETAPA 2 — Extração de dados nos sites
# ==========================================================================

def extrair_dados_do_site(url):
    """
    Visita a home + páginas de contato/sobre e extrai:
      - e-mails de contato
      - perfil do Instagram
      - página do Facebook
      - nome do responsável/proprietário (best-effort)

    Retorna um dict com as chaves: emails, instagram, facebook, responsavel.
    """
    resultado = {"emails": "", "instagram": "", "facebook": "", "responsavel": ""}
    if not url:
        return resultado

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    emails_set    = set()
    instagram_set = set()
    facebook_set  = set()
    nomes_set     = set()

    base = url if url.endswith("/") else url + "/"

    for sub in PAGINAS_CONTATO:
        alvo = urljoin(base, sub)
        try:
            r = requests.get(alvo, headers=headers, timeout=10)
            if r.status_code != 200:
                continue
            texto = r.text

            # --- E-mails ---
            for mail in EMAIL_RE.findall(texto):
                low = mail.lower()
                if not any(j in low for j in EMAIL_LIXO):
                    emails_set.add(low)

            # --- Instagram ---
            for handle in INSTAGRAM_RE.findall(texto):
                h = handle.rstrip("/").lower()
                if h not in INSTAGRAM_LIXO and len(h) >= 2:
                    instagram_set.add(f"https://instagram.com/{h}")

            # --- Facebook ---
            for slug in FACEBOOK_RE.findall(texto):
                s = slug.rstrip("/").lower()
                if s not in FACEBOOK_LIXO and len(s) >= 3:
                    facebook_set.add(f"https://facebook.com/{s}")

            # --- Responsável ---
            for nome in RESPONSAVEL_RE.findall(texto):
                nomes_set.add(nome.strip())

        except Exception:
            continue

        time.sleep(random.uniform(0.5, 1.2))

        # Otimização: se achou e-mail E redes na home, não precisa varrer o resto
        if sub == "" and emails_set and (instagram_set or facebook_set):
            break

    resultado["emails"]      = "; ".join(sorted(emails_set))
    resultado["instagram"]   = "; ".join(sorted(instagram_set))
    resultado["facebook"]    = "; ".join(sorted(facebook_set))
    resultado["responsavel"] = "; ".join(sorted(nomes_set))
    return resultado


# ==========================================================================
#  SAÍDA / ORQUESTRAÇÃO
# ==========================================================================

def salvar_csv(linhas, caminho):
    """Grava o CSV (UTF-8 com BOM pra abrir certinho no Excel)."""
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        for linha in linhas:
            w.writerow({c: linha.get(c, "") for c in COLUNAS})


def main():
    cfg    = CONFIG
    vistos = set()
    leads  = []

    with sync_playwright() as pw:
        navegador = pw.chromium.launch(headless=cfg["headless"])
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

    print(f"\n[TOTAL] {len(leads)} empresas únicas coletadas do Maps.")

    if cfg.get("extrair_dados_site", True):
        print("\n[ETAPA 2] Extraindo dados dos sites (e-mail, redes sociais, responsável)...")
        for i, lead in enumerate(leads, 1):
            if lead["site"]:
                dados = extrair_dados_do_site(lead["site"])
                lead.update(dados)
                partes = []
                if dados["emails"]:
                    partes.append(f"📧 {dados['emails']}")
                if dados["instagram"]:
                    partes.append(f"📷 {dados['instagram'].split('/')[-1]}")
                if dados["facebook"]:
                    partes.append(f"👍 {dados['facebook'].split('/')[-1]}")
                if dados["responsavel"]:
                    partes.append(f"👤 {dados['responsavel']}")
                resumo = "  ".join(partes) if partes else "(nenhum)"
                print(f"  {i:>3}/{len(leads)}  {lead['nome'][:35]:<35}  {resumo}")

    salvar_csv(leads, cfg["saida_csv"])

    # --- Resumo final ---
    com_tel  = sum(1 for l in leads if l["telefone"])
    com_wpp  = sum(1 for l in leads if l["whatsapp"])
    com_mail = sum(1 for l in leads if l["emails"])
    com_ig   = sum(1 for l in leads if l["instagram"])
    com_fb   = sum(1 for l in leads if l["facebook"])
    com_resp = sum(1 for l in leads if l["responsavel"])

    print(f"\n[OK] Salvo em '{cfg['saida_csv']}'")
    print(f"     {len(leads)} empresas únicas")
    print(f"     Telefone:    {com_tel:>4}  |  WhatsApp (link): {com_wpp:>4}")
    print(f"     E-mail:      {com_mail:>4}  |  Instagram:       {com_ig:>4}  |  Facebook: {com_fb:>4}")
    print(f"     Responsável: {com_resp:>4}")
    print(f"\n     Colunas para a equipe preencherem no CSV:")
    print(f"     status · atribuido_para · data_contato · observacoes")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário.")
        sys.exit(0)
