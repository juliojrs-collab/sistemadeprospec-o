# =================================================================
#  CONFIGURACAO DO SISTEMA DE CAPTURA DE LEADS
# =================================================================
#
#  Como editar este arquivo:
#  1. Clique com o botao direito no arquivo
#  2. Selecione "Abrir com" > "Bloco de Notas"
#  3. Faca as alteracoes desejadas
#  4. Salve: Ctrl + S
#
# =================================================================


# -----------------------------------------------------------------
#  SUAS BUSCAS NO GOOGLE MAPS
#
#  Formato: "tipo de negocio em Cidade UF"
#  Cada linha entre aspas e uma busca separada.
#  Para adicionar mais buscas: copie uma linha e cole abaixo.
#  Para remover uma busca: coloque um # na frente da linha.
# -----------------------------------------------------------------
BUSCAS = [
    "clinicas odontologicas em Curitiba PR",
    "academias em Curitiba PR",
    "restaurantes em Curitiba PR",
]


# -----------------------------------------------------------------
#  QUANTAS EMPRESAS COLETAR POR BUSCA
#
#  Quanto maior o numero, mais tempo demora.
#  Recomendado: entre 20 e 50.
# -----------------------------------------------------------------
MAX_POR_BUSCA = 40


# -----------------------------------------------------------------
#  BUSCAR E-MAIL, INSTAGRAM E FACEBOOK NOS SITES?
#
#  True  = Sim  (mais lento, mas traz muito mais dados)
#  False = Nao  (mais rapido, coleta so os dados do Maps)
# -----------------------------------------------------------------
EXTRAIR_DADOS_SITE = True


# -----------------------------------------------------------------
#  NOME DO ARQUIVO DE SAIDA
#
#  O arquivo sera salvo nesta mesma pasta.
#  Troque o nome se quiser separar por campanha, ex.: "leads_maio.csv"
# -----------------------------------------------------------------
SAIDA_CSV = "leads.csv"
