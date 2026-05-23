# Sistema de Prospecção — Captura de Leads via Google Maps

Raspa o **Google Maps** para coletar contatos de empresas locais e, opcionalmente,
extrai e-mails dos sites de cada empresa. Saída em CSV pronto para Excel / CRM.

## Como funciona

```
ETAPA 1  Google Maps (Playwright/Chromium)
         → nome · categoria · avaliação · nº reviews · telefone · endereço · site

ETAPA 2  Visita o site de cada empresa (requests + regex)
         → e-mails de contato

SAÍDA    leads.csv  (UTF-8 com BOM — abre certinho no Excel)
```

## Instalação (uma vez)

```bash
pip install -r requirements.txt
playwright install chromium
```

## Configuração

Edite o bloco **`CONFIG`** no topo do `captura_leads.py`:

| Chave | Padrão | O que faz |
|---|---|---|
| `buscas` | lista de strings | Termos de busca no Maps (`"nicho cidade"`) |
| `max_por_busca` | `40` | Limite de empresas por busca |
| `extrair_emails` | `True` | Visitar sites para pescar e-mails |
| `headless` | `False` | `False` = navegador visível (recomendado na 1ª vez) |
| `saida_csv` | `"leads.csv"` | Nome do arquivo de saída |
| `pausa_min/max` | `1.2 / 3.0` | Intervalo (s) entre ações — evita bloqueio |

Se os seletores do Maps pararem de funcionar, ajuste o bloco **`SEL`** (também no topo do script).

## Uso rápido

```bash
python captura_leads.py
```

### Teste mínimo recomendado

```python
# Editar CONFIG temporariamente:
"buscas": ["clinicas odontologicas em Curitiba PR"],
"max_por_busca": 5,
"extrair_emails": False,
"headless": False,
```

## Backlog / melhorias mapeadas

- [ ] Filtro por avaliação mínima (só empresas acima de nota X)
- [ ] Captura de WhatsApp a partir dos sites
- [ ] Exportação direta pro Google Sheets

## Avisos

- Scraping do Google Maps **fere os Termos de Uso** do Google. Use com bom senso
  e volume moderado.
- Os seletores (`SEL`) podem quebrar quando o Google atualiza o layout.
- Rode com `headless: False` na primeira vez para resolver tela de
  consentimento/captcha manualmente.
