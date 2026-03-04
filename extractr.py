import pdfplumber
import pandas as pd
import re
from decimal import Decimal, InvalidOperation

PDF_PATH = "1001 a 1012 Provisao Ferias 012026.pdf"
OUTPUT_CSV = "provisao_ferias.csv"

def to_decimal(valor):
    if not valor:
        return Decimal("0")
    valor = valor.replace(".", "").replace(",", ".")
    try:
        return Decimal(valor)
    except InvalidOperation:
        return Decimal("0")

def extrair_colunas_saldo(linha):
    """
    Extrai valores numéricos da linha 'Saldo Atual'
    Retorna lista padronizada:
    [dias, valor, adicionais, total_ferias, inss, fgts, tot_encargos, total_geral]
    """
    numeros = re.findall(r'-?\d+[.,]?\d*', linha)
    if len(numeros) < 8:
        return None

    return [
        to_decimal(numeros[0]),  # dias
        to_decimal(numeros[1]),  # valor
        to_decimal(numeros[2]),  # adicionais 1/3
        to_decimal(numeros[3]),  # total ferias
        to_decimal(numeros[4]),  # inss
        to_decimal(numeros[5]),  # fgts
        to_decimal(numeros[6]),  # tot encargos
        to_decimal(numeros[7])   # total geral
    ]

def somar_blocos(bloco1, bloco2):
    return [a + b for a, b in zip(bloco1, bloco2)]

colaboradores = {}

with pdfplumber.open(PDF_PATH) as pdf:
    for page in pdf.pages:
        texto = page.extract_text()
        if not texto:
            continue

        linhas = texto.split("\n")
        mat_atual = None
        nome_atual = None
        secao = None

        dados = {
            "TOTAL": None,
            "VENCIDAS": None,
            "A VENCER": None
        }

        for linha in linhas:

            # Captura matrícula e nome
            mat_nome = re.search(r'(\d{6})\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ ]+)', linha)
            if mat_nome:
                mat_atual = mat_nome.group(1)
                nome_atual = mat_nome.group(2).strip()
                if mat_atual not in colaboradores:
                    colaboradores[mat_atual] = {
                        "MAT": mat_atual,
                        "NOME": nome_atual,
                        "TOTAL": None,
                        "VENCIDAS": None,
                        "A VENCER": None
                    }

            # Detecta seção
            if "TOTAL" in linha:
                secao = "TOTAL"
            elif "VENCIDAS" in linha:
                secao = "VENCIDAS"
            elif "A VENCER" in linha:
                secao = "A VENCER"

            # Captura linha Saldo Atual
            if "Saldo" in linha and "Atual" in linha and mat_atual:
                colunas = extrair_colunas_saldo(linha)
                if colunas:
                    colaboradores[mat_atual][secao] = colunas

# Consolidação final
resultado = []

for mat, dados in colaboradores.items():

    total = dados["TOTAL"]
    vencidas = dados["VENCIDAS"]
    avencer = dados["A VENCER"]

    if total:
        final = total
    elif vencidas and avencer:
        final = somar_blocos(vencidas, avencer)
    elif vencidas:
        final = vencidas
    elif avencer:
        final = avencer
    else:
        continue

    resultado.append([
        dados["MAT"],
        dados["NOME"],
        float(final[0]),
        float(final[1]),
        float(final[2]),
        float(final[3]),
        float(final[4]),
        float(final[5]),
        float(final[6]),
        float(final[7])
    ])

# Criar DataFrame
df = pd.DataFrame(resultado, columns=[
    "MAT",
    "NOME",
    "DIAS DE DIREITO",
    "VALOR",
    "ADICIONAIS 1/3 CONSTIT",
    "TOTAL FERIAS",
    "INSS",
    "FGTS",
    "TOT.ENCARGOS",
    "TOTAL GERAL"
])

# Exportar CSV com separador ;
df.to_csv(OUTPUT_CSV, sep=";", index=False, decimal=",")

print("Arquivo provisao_ferias.csv gerado com sucesso.")
