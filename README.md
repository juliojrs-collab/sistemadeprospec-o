# Sistema de Captura de Leads — Google Maps

Busca empresas no Google Maps e monta uma planilha com:
**nome · telefone · link do WhatsApp · endereço · e-mail · Instagram · Facebook · responsável**
— pronta pra abrir no Excel ou importar no CRM.

---

## Como usar (passo a passo)

### 🔷 Passo 0 — Baixar os arquivos

Baixe esta pasta completa para o seu computador.
Todos os arquivos precisam estar na **mesma pasta**.

---

### 🔷 Passo 1 — Instalar (só na primeira vez)

Clique duas vezes no arquivo:

```
PASSO_1_INSTALAR.bat
```

Uma janela preta vai abrir e instalar tudo automaticamente.

> ⚠️ **Se aparecer "Python não encontrado":**
> O instalador vai abrir o site do Python automaticamente.
> Baixe e instale o Python, mas **ATENÇÃO**: durante a instalação,
> marque a opção **"Add Python to PATH"** antes de clicar em Install.
> Depois rode o `PASSO_1_INSTALAR.bat` novamente.

---

### 🔷 Passo 2 — Configurar suas buscas

Abra o arquivo `configuracao.py` com o **Bloco de Notas**:

1. Clique com o botão **direito** no arquivo `configuracao.py`
2. Selecione **"Abrir com"** → **"Bloco de Notas"**
3. Edite a lista de buscas:

```python
BUSCAS = [
    "clinicas odontologicas em Curitiba PR",
    "academias em Sao Paulo SP",
    "saloes de beleza em Belo Horizonte MG",
]
```

4. Salve com **Ctrl + S** e feche o Bloco de Notas.

> **Dicas:**
> - Use o formato `"tipo de negócio em Cidade UF"`
> - Você pode ter quantas buscas quiser — uma por linha
> - Para desativar uma busca sem apagar, coloque `#` na frente

---

### 🔷 Passo 3 — Rodar

Clique duas vezes no arquivo:

```
PASSO_2_RODAR.bat
```

O **navegador vai abrir automaticamente** e você vai ver ele trabalhando.
Não feche o navegador nem a janela preta — espere terminar.

> ⚠️ **Se aparecer uma tela de "Aceitar cookies" do Google:**
> Clique em **Aceitar** manualmente. O sistema continua sozinho depois.

---

### 🔷 Passo 4 — Acessar os leads

Quando terminar, o arquivo **`leads.csv`** vai aparecer nesta mesma pasta.

- **Excel:** clique duas vezes para abrir
- **Google Sheets:** vá em Arquivo → Importar → selecione o arquivo

---

## O que vem na planilha

| Coluna | O que é |
|---|---|
| `nome` | Nome da empresa |
| `categoria` | Tipo de negócio (ex.: Dentista, Academia) |
| `telefone` | Telefone do Google Maps |
| `whatsapp` | Link direto — clique e já abre a conversa |
| `endereco` | Endereço completo |
| `site` | Site da empresa |
| `instagram` | Perfil do Instagram (quando encontrado) |
| `facebook` | Página do Facebook (quando encontrado) |
| `emails` | E-mail(s) de contato (quando encontrado) |
| `responsavel` | Nome do dono/responsável (quando encontrado) |
| `status` | **Preencha sua equipe:** Abordado / Interessado / Fechado… |
| `atribuido_para` | **Preencha sua equipe:** nome do vendedor responsável |
| `data_contato` | **Preencha sua equipe:** data do contato |
| `observacoes` | **Preencha sua equipe:** notas livres |

---

## Dúvidas frequentes

**O navegador abriu mas não encontrou nenhuma empresa.**
→ O Google pode ter pedido um captcha. Resolva manualmente na janela do
  navegador e o sistema continua sozinho.

**Alguns campos vieram em branco (e-mail, Instagram, etc.).**
→ Nem toda empresa tem site ou redes sociais. O sistema captura o que existir.

**Quero buscar mais empresas.**
→ Edite `MAX_POR_BUSCA` no arquivo `configuracao.py` (padrão: 40).

**Quero salvar numa planilha diferente sem perder a anterior.**
→ Edite `SAIDA_CSV` no arquivo `configuracao.py`,
  ex.: `SAIDA_CSV = "leads_junho.csv"`
