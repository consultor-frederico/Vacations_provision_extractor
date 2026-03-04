import pdfplumber
import pandas as pd
import re
from decimal import Decimal, InvalidOperation

PDF_PATH = "1001 a 1012 Provisao Ferias 012026.pdf"
OUTPUT_CSV = "provisao_ferias.csv"

def to_decimal(valor):
    if not valor or valor.strip() == "-":
        return Decimal("0")
    # Remove pontos de milhar e ajusta decimal
    limpo = valor.replace(".", "").replace(",", ".")
    # Trata valores negativos entre parênteses: (100,00) -> -100.00
    if "(" in limpo:
        limpo = "-" + limpo.replace("(", "").replace(")", "")
    try:
        return Decimal(limpo)
    except InvalidOperation:
        return Decimal("0")

def extrair_colunas_saldo(linha):
    """
    Extrai valores numéricos da linha 'Saldo Atual'.
    O SIGA costuma ter 9 colunas numéricas nesta linha.
    """
    # Busca números formatados, inclusive negativos entre parênteses
    numeros = re.findall(r'\(?\d+[.,]\d+\)?', linha)
    
    if len(numeros) >= 9:
        return [
            to_decimal(numeros[0]),  # Dias
            to_decimal(numeros[1]),  # Valor
            to_decimal(numeros[2]) + to_decimal(numeros[3]), # Soma Adicionais + 1/3 Constit
            to_decimal(numeros[4]),  # Total Ferias
            to_decimal(numeros[5]),  # INSS
            to_decimal(numeros[6]),  # FGTS
            to_decimal(numeros[7]),  # Tot Encargos
            to_decimal(numeros[8])   # Total Geral
        ]
    return None

def somar_blocos(b1, b2):
    return [x + y for x, y in zip(b1, b2)]

colaboradores = {}

with pdfplumber.open(PDF_PATH) as pdf:
    for page in pdf.pages:
        texto = page.extract_text()
        if not texto: continue

        linhas = texto.split("\n")
        mat_atual = None
        nome_atual = None
        secao = None

        for linha in linhas:
            # Captura Matrícula (alfanumérica) e Nome após MAT: e NOME:
            mat_match = re.search(r'MAT:\s*(\w+)', linha)
            nome_match = re.search(r'NOME:\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ\s]+)', linha)
            
            if mat_match and nome_match:
                mat_atual = mat_match.group(1)
                nome_atual = nome_match.group(1).strip()
                if mat_atual not in colaboradores:
                    colaboradores[mat_atual] = {
                        "MAT": mat_atual, "NOME": nome_atual,
                        "TOTAL": None, "VENCIDAS": None, "A VENCER": None
                    }

            # Identificação de seção (Evita confundir com TOTAL FERIAS)
            if "TOTAL" in linha and "FERIAS" not in linha and "GERAL" not in linha:
                secao = "TOTAL"
            elif "VENCIDAS" in linha or "VENOIDAS" in linha:
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
for mat, d in colaboradores.items():
    if d["TOTAL"]: final = d["TOTAL"]
    elif d["VENCIDAS"] and d["A VENCER"]: final = somar_blocos(d["VENCIDAS"], d["A VENCER"])
    elif d["VENCIDAS"]: final = d["VENCIDAS"]
    elif d["A VENCER"]: final = d["A VENCER"]
    else: continue

    resultado.append([d["MAT"], d["NOME"]] + [float(x) for x in final])

df = pd.DataFrame(resultado, columns=[
    "MAT", "NOME", "DIAS DE DIREITO", "VALOR", "ADICIONAIS 1/3 CONSTIT",
    "TOTAL FERIAS", "INSS", "FGTS", "TOT.ENCARGOS", "TOTAL GERAL"
])

df.to_csv(OUTPUT_CSV, sep=";", index=False, decimal=",", encoding="utf-8-sig")
print(f"Sucesso! {len(df)} colaboradores processados.")
