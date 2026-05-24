#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lógica de scraping — chamada pelo servidor Flask.
"""

import re
import time
import random
from datetime import date
from urllib.parse import urljoin

import requests as http
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


# ──────────────────────────────────────────────────────────────
#  SELETORES DO GOOGLE MAPS
#  Se o Google mudar o layout, só mexe aqui.
# ──────────────────────────────────────────────────────────────
SEL = {
    "feed":     'div[role="feed"]',
    "cards":    'a[href*="/maps/place/"]',
    "nome":     "h1",
    "categoria":'button[jsaction*="category"]',
    "rating":   'div.F7nice span[aria-hidden="true"]',
    "reviews":  'div.F7nice span[aria-label*="avaliac"], div.F7nice span[aria-label*="review"]',
    "endereco": 'button[data-item-id="address"]',
    "site":     'a[data-item-id="authority"]',
    "telefone": 'button[data-item-id^="phone"]',
    "cookies":  'button[aria-label*="Aceitar"], button[aria-label*="Accept all"]',
}


# ──────────────────────────────────────────────────────────────
#  PADRÕES DE EXTRAÇÃO
# ──────────────────────────────────────────────────────────────
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
EMAIL_LIXO = (
    "example.com", "sentry.", "wixpress.com", ".png", ".jpg",
    "@sentry", "domain.com", "email.com", "your-email",
)

INSTAGRAM_RE = re.compile(
    r'instagram\.com/([A-Za-z0-9][A-Za-z0-9_.]{1,29})(?:[/?"\'\s<]|$)',
    re.IGNORECASE,
)
INSTAGRAM_LIXO = frozenset([
    "p", "reel", "tv", "stories", "highlights", "explore",
    "reels", "accounts", "oauth", "_u", "share", "sharer", "direct",
])

FACEBOOK_RE = re.compile(
    r'facebook\.com/([A-Za-z0-9][A-Za-z0-9._-]{2,59})(?:[/?"\'\s<]|$)',
    re.IGNORECASE,
)
FACEBOOK_LIXO = frozenset([
    "sharer", "share", "login", "dialog", "plugins", "policies",
    "policy", "legal", "help", "about", "ads", "business", "groups",
    "events", "marketplace", "profile.php", "photo.php", "video.php",
    "permalink.php", "watch", "gaming", "pages", "hashtag",
])

_MAI = "A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇÀÜ"
_MIN = "a-záéíóúâêîôûãõçàü"
RESPONSAVEL_RE = re.compile(
    rf"(?i:(?:diretor[a]?|fundador[a]?|proprietári[oa]|gerente|ceo|cto|sóci[oa]|"
    rf"responsável|coordenador[a]?|presidente)\s*[:\-]?\s*)"
    rf"([{_MAI}][{_MIN}]+(?:\s[{_MAI}][{_MIN}]+){{1,3}})"
)

PAGINAS_CONTATO = ("", "contato", "contact", "fale-conosco", "sobre", "about", "quem-somos")


# ──────────────────────────────────────────────────────────────
#  COLUNAS DO CSV (ordem final)
# ──────────────────────────────────────────────────────────────
COLUNAS = [
    "data", "nome", "categoria", "avaliacao", "reviews",
    "telefone", "whatsapp",
    "emails", "instagram", "facebook",
    "endereco", "site", "responsavel",
    "status", "atribuido_para", "data_contato", "observacoes",
]


# ──────────────────────────────────────────────────────────────
#  UTILITÁRIOS
# ──────────────────────────────────────────────────────────────
def _pausa(mn=1.0, mx=2.5):
    time.sleep(random.uniform(mn, mx))


def _txt(locator):
    try:
        if locator.count() > 0:
            return (locator.first.inner_text() or "").strip()
    except Exception:
        pass
    return ""


def _attr(locator, attr):
    try:
        if locator.count() > 0:
            return (locator.first.get_attribute(attr) or "").strip()
    except Exception:
        pass
    return ""


def _whatsapp(tel):
    if not tel:
        return ""
    nums = re.sub(r"\D", "", tel)
    if len(nums) < 8:
        return ""
    if not (nums.startswith("55") and len(nums) >= 12):
        nums = ("55" + nums[1:]) if nums.startswith("0") else ("55" + nums)
    return f"https://wa.me/{nums}"


# ──────────────────────────────────────────────────────────────
#  ETAPA 1 — Google Maps
# ──────────────────────────────────────────────────────────────
def _rolar_feed(page, max_itens):
    feed = page.locator(SEL["feed"])
    if feed.count() == 0:
        return
    estagnado = 0
    ultimo = -1
    while True:
        total = page.locator(SEL["cards"]).count()
        if total >= max_itens:
            break
        if total == ultimo:
            estagnado += 1
            if estagnado >= 3:
                break
        else:
            estagnado = 0
        ultimo = total
        feed.first.evaluate("el => el.scrollBy(0, el.scrollHeight)")
        _pausa(0.8, 1.5)


def _ficha(page):
    tel = _txt(page.locator(SEL["telefone"]))
    p = {
        "nome":      _txt(page.locator(SEL["nome"])),
        "categoria": _txt(page.locator(SEL["categoria"])),
        "avaliacao": _txt(page.locator(SEL["rating"])),
        "reviews":   _txt(page.locator(SEL["reviews"])),
        "endereco":  _txt(page.locator(SEL["endereco"])),
        "telefone":  tel,
        "whatsapp":  _whatsapp(tel),
        "site":      _attr(page.locator(SEL["site"]), "href"),
        "emails": "", "instagram": "", "facebook": "", "responsavel": "",
    }
    m = re.search(r"[\d.,]+", p["reviews"])
    p["reviews"] = m.group(0) if m else ""
    return p


def _raspar(page, termo, quantidade, log_fn):
    log_fn(f"[BUSCA] {termo}\n")
    url = "https://www.google.com/maps/search/" + termo.replace(" ", "+")
    page.goto(url, timeout=60_000)
    _pausa()

    try:
        btn = page.locator(SEL["cookies"])
        if btn.count() > 0:
            btn.first.click(timeout=4000)
            _pausa()
    except Exception:
        pass

    try:
        page.wait_for_selector(SEL["feed"], timeout=15_000)
    except PWTimeout:
        log_fn("! Lista não carregou (captcha?). Tente novamente.\n")
        return []

    _rolar_feed(page, quantidade)

    cards = page.locator(SEL["cards"])
    total = min(cards.count(), quantidade)
    log_fn(f"→ {total} empresas encontradas. Abrindo fichas...\n")

    out = []
    for i in range(total):
        try:
            cards.nth(i).click(timeout=8000)
            _pausa()
            page.wait_for_selector(SEL["nome"], timeout=8000)
            d = _ficha(page)
            if d["nome"]:
                out.append(d)
                wpp = "✓ wpp" if d["whatsapp"] else ""
                log_fn(f"  {i+1:>3}. {d['nome'][:45]}  {d['telefone'] or '—'}  {wpp}\n")
        except Exception as e:
            log_fn(f"  {i+1:>3}. (erro: {type(e).__name__})\n")
    return out


# ──────────────────────────────────────────────────────────────
#  ETAPA 2 — Dados do site
# ──────────────────────────────────────────────────────────────
def _site(url):
    res = {"emails": "", "instagram": "", "facebook": "", "responsavel": ""}
    if not url:
        return res

    hdrs = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }
    emails_s = set()
    ig_s = set()
    fb_s = set()
    resp_s = set()
    base = url if url.endswith("/") else url + "/"

    for sub in PAGINAS_CONTATO:
        try:
            r = http.get(urljoin(base, sub), headers=hdrs, timeout=10)
            if r.status_code != 200:
                continue
            txt = r.text

            for m in EMAIL_RE.findall(txt):
                low = m.lower()
                if not any(j in low for j in EMAIL_LIXO):
                    emails_s.add(low)

            for h in INSTAGRAM_RE.findall(txt):
                h2 = h.rstrip("/").lower()
                if h2 not in INSTAGRAM_LIXO and len(h2) >= 2:
                    ig_s.add(f"https://instagram.com/{h2}")

            for s in FACEBOOK_RE.findall(txt):
                s2 = s.rstrip("/").lower()
                if s2 not in FACEBOOK_LIXO and len(s2) >= 3:
                    fb_s.add(f"https://facebook.com/{s2}")

            for n in RESPONSAVEL_RE.findall(txt):
                resp_s.add(n.strip())

        except Exception:
            continue

        time.sleep(random.uniform(0.4, 0.9))
        if sub == "" and emails_s and (ig_s or fb_s):
            break

    res["emails"]      = "; ".join(sorted(emails_s))
    res["instagram"]   = "; ".join(sorted(ig_s))
    res["facebook"]    = "; ".join(sorted(fb_s))
    res["responsavel"] = "; ".join(sorted(resp_s))
    return res


# ──────────────────────────────────────────────────────────────
#  FUNÇÃO PRINCIPAL — chamada pelo servidor Flask
# ──────────────────────────────────────────────────────────────
def executar_busca(termo, quantidade, extrair_dados, log_fn=print):
    """
    Executa a busca completa e retorna lista de dicts (leads).
    """
    leads = []

    with sync_playwright() as pw:
        nav = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--single-process",           # 1 processo só → menos RAM
                "--no-zygote",                # sem processo zygote
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-breakpad",
                "--disable-client-side-phishing-detection",
                "--disable-default-apps",
                "--disable-hang-monitor",
                "--disable-popup-blocking",
                "--disable-renderer-backgrounding",
                "--disable-sync",
                "--metrics-recording-only",
                "--mute-audio",
                "--no-first-run",
                "--safebrowsing-disable-auto-update",
                "--disable-features=site-per-process,TranslateUI",
            ],
        )
        try:
            page = nav.new_page(locale="pt-BR")
            page.set_default_timeout(15_000)
            leads = _raspar(page, termo, quantidade, log_fn)
        finally:
            nav.close()

    log_fn(f"\n[TOTAL] {len(leads)} empresas coletadas.\n")

    if extrair_dados and leads:
        log_fn("[ETAPA 2] Buscando e-mail, Instagram e Facebook nos sites...\n")
        for i, lead in enumerate(leads, 1):
            if lead.get("site"):
                dados = _site(lead["site"])
                lead.update(dados)
                partes = []
                if dados["emails"]:    partes.append("📧 e-mail")
                if dados["instagram"]: partes.append("📷 instagram")
                if dados["facebook"]:  partes.append("👍 facebook")
                log_fn(f"  {i:>3}/{len(leads)}  {lead['nome'][:40]}  {'  '.join(partes) or '—'}\n")

    hoje = date.today().strftime("%d/%m/%Y")
    for lead in leads:
        lead["data"] = hoje

    return leads
