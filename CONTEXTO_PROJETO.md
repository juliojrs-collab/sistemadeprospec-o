# Contexto do Projeto — Sistema de Captura de Leads (Google Maps)

> Cole este arquivo na primeira mensagem de uma nova sessão no Claude Code
> para dar todo o contexto do que já foi decidido e construído.

## Objetivo
Sistema de prospecção que captura contatos de **empresas locais** a partir do
Google, com restrição de **custo zero** (sem API paga).

## Decisões já tomadas
- **Fonte:** scraping do **Google Maps** (não a API Places, que é paga).
  - Trade-off aceito conscientemente: fere os Termos de Uso do Google, pode
    quebrar quando o layout muda, exige pausas pra não tomar bloqueio de IP.
- **Funil de 2 etapas:**
  1. Google Maps → nome, categoria, avaliação, nº de reviews, telefone,
     endereço, site.
  2. Visita o site de cada empresa → extrai e-mails (o Maps não fornece e-mail).
- **Stack:** Python + Playwright (Chromium) para o Maps; `requests` + regex
  para a extração de e-mails.
- **Saída:** CSV em UTF-8 com BOM (abre certinho no Excel) / importável em CRM.

## Estado atual
- Script único pronto e com sintaxe validada: `captura_leads.py` (~312 linhas).
- Ainda **NÃO foi testado contra o Google de verdade** — o teste real roda na
  máquina do usuário (o ambiente do Claude não acessa google.com).
- Estrutura do código:
  - Bloco `CONFIG` no topo (buscas, limites, pausas, headless, arquivo de saída).
  - Bloco `SEL` (seletores do Maps) **isolado de propósito** — é onde consertar
    quando o layout do Google mudar.
  - `raspar_busca()` → Etapa 1 (Maps).
  - `extrair_emails_do_site()` → Etapa 2 (e-mails).
  - `main()` faz orquestração + dedup por (nome, telefone).

## Como rodar
```bash
pip install playwright requests
playwright install chromium
python captura_leads.py
```

## Plano de teste combinado (próximo passo)
Rodar um teste mínimo isolando a Etapa 1:
- Apenas **1 busca** (nicho + cidade reais).
- `"max_por_busca": 5`
- `"extrair_emails": False`
- `"headless": False` (ver o navegador, resolver cookies/captcha na mão).

Depois reportar: log do terminal + qualquer mensagem de erro completa.

## Pontos que provavelmente precisarão de ajuste
1. **Tela de consentimento de cookies** do Google (varia por região; pode travar
   o carregamento da lista). Seletor em `SEL["aceitar_cookies"]`.
2. **Seletores da ficha** caso venham campos vazios (nome, telefone, site etc.).
   Todos concentrados no bloco `SEL`.

## Melhorias já mapeadas (backlog, ainda não implementadas)
- Filtro por avaliação mínima (só pegar empresas acima de nota X).
- Captura de WhatsApp a partir dos sites.
- Exportação direta pro Google Sheets (em vez de CSV).
