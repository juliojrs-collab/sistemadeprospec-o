# Sistema de Captura de Leads — Google Maps

Página web para buscar empresas locais no Google Maps e exportar os contatos em Excel (CSV).

## O que o sistema faz

1. Você acessa a página pelo link
2. Escolhe: **tipo de negócio**, **cidade**, **estado** e **bairro** (opcional)
3. Clica em **Gerar Relatório**
4. O sistema busca no Google Maps e extrai: nome, telefone, WhatsApp, e-mail, Instagram, Facebook, endereço, site e responsável
5. Você clica em **Baixar Excel (CSV)**

---

## Como colocar no ar (Render — gratuito)

### Pré-requisitos
- Conta no [GitHub](https://github.com) (gratuito)
- Conta no [Render](https://render.com) (gratuito)

### Passo 1 — Enviar o código pro GitHub

1. Acesse [github.com](https://github.com) e crie um repositório novo (pode ser privado)
2. Faça upload de todos os arquivos desta pasta para o repositório

### Passo 2 — Criar o serviço no Render

1. Acesse [render.com](https://render.com) e faça login
2. Clique em **New → Web Service**
3. Conecte seu repositório do GitHub
4. Preencha:
   - **Name:** captura-leads (ou qualquer nome)
   - **Build Command:** `pip install -r requirements.txt && playwright install chromium && playwright install-deps chromium`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 300`
5. Clique em **Create Web Service**
6. Aguarde o deploy (5–10 minutos na primeira vez)
7. Render fornece um link público — ex.: `https://captura-leads.onrender.com`

---

## Como testar localmente (Windows)

```bash
pip install -r requirements.txt
playwright install chromium
python app.py
```

Abra o Chrome em: `http://localhost:5000`

---

## Arquivos do projeto

| Arquivo | O que é |
|---|---|
| `app.py` | Servidor Flask — gerencia as buscas e rotas |
| `scraper.py` | Lógica de scraping do Google Maps e dos sites |
| `templates/index.html` | A página web |
| `requirements.txt` | Dependências Python |
| `Procfile` | Configuração para o servidor online |
| `render.yaml` | Deploy automático no Render |

---

## Colunas do CSV gerado

| Coluna | De onde vem |
|---|---|
| Data | Data da captura |
| Nome | Google Maps |
| Categoria | Google Maps |
| Telefone | Google Maps |
| WhatsApp | Gerado do telefone (link direto) |
| E-mail | Site da empresa |
| Instagram | Site da empresa |
| Facebook | Site da empresa |
| Responsável | Site da empresa (quando disponível) |
| Endereço | Google Maps |
| Site | Google Maps |
| status / atribuido_para / data_contato / observacoes | Em branco — para a equipe preencher |
