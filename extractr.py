import pdfplumber
import pandas as pd
import re
import csv
from decimal import Decimal, InvalidOperation

PDF_PATH = "1001 a 1012 Provisao Ferias 012026.pdf"
OUTPUT_CSV = "provisao_ferias.csv"

def to_decimal(valor):
    if not valor or valor.strip() in ["-", ""]: return Decimal("0")
    limpo = valor.replace(".", "").replace(",", ".")
    if "(" in limpo:
        limpo = "-" + limpo.replace("(", "").replace(")", "")
    try:
        return Decimal(limpo)
    except:
        return Decimal("0")

def extrair_valores_saldo(linha):
    # Captura valores como 1.234,56 ou (123,45)
    numeros = re.findall(r'\(?\d+[.,]\d+\)?', linha)
    if len(numeros) >= 9:
        return [
            to_decimal(numeros[0]), # Dias
            to_decimal(numeros[1]), # Valor
            to_decimal(numeros[2]) + to_decimal(numeros[3]), # Adic + 1/3
            to_decimal(numeros[4]), # Total Ferias
            to_decimal(numeros[5]), # INSS
            to_decimal(numeros[6]), # FGTS
            to_decimal(numeros[7]), # Tot Enc
            to_decimal(numeros[8])  # Total Geral
        ]
    return None

def salvar_colaborador(dados, writer):
    if not dados or not dados['MAT']: return
    
    # Lógica de Hierarquia
    if dados["TOTAL"]: final = dados["TOTAL"]
    elif dados["VENCIDAS"] and dados["A VENCER"]:
        final = [x + y for x, y in zip(dados["VENCIDAS"], dados["A VENCER"])]
    elif dados["VENCIDAS"]: final = dados["VENCIDAS"]
    elif dados["A VENCER"]: final = dados["A VENCER"]
    else: return

    writer.writerow([
        dados["MAT"], dados["NOME"], 
        str(final[0]).replace('.', ','), str(final[1]).replace('.', ','),
        str(final[2]).replace('.', ','), str(final[3]).replace('.', ','),
        str(final[4]).replace('.', ','), str(final[5]).replace('.', ','),
        str(final[6]).replace('.', ','), str(final[7]).replace('.', ',')
    ])

# --- INÍCIO DO PROCESSAMENTO ---
print("Iniciando extração em tempo real...")

with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f, delimiter=';')
    writer.writerow(["MAT", "NOME", "DIAS DE DIREITO", "VALOR", "ADICIONAIS 1/3 CONSTIT", "TOTAL FERIAS", "INSS", "FGTS", "TOT.ENCARGOS", "TOTAL GERAL"])

    colab_atual = {"MAT": None, "NOME": "", "TOTAL": None, "VENCIDAS": None, "A VENCER": None}
    secao = None

    with pdfplumber.open(PDF_PATH) as pdf:
        for i, pagina in enumerate(pdf.pages):
            texto = pagina.extract_text()
            if not texto: continue
            
            linhas = texto.split('\n')
            for j, linha in enumerate(linhas):
                
                # Detecta Novo Colaborador (MAT: 000000)
                if "MAT:" in linha:
                    # Antes de começar o novo, salva o anterior se existir
                    if colab_atual["MAT"]:
                        salvar_colaborador(colab_atual, writer)
                    
                    # Reinicia objeto
                    mat_m = re.search(r'MAT:\s*(\w+)', linha)
                    nome_m = re.search(r'NOME:\s*(.*)', linha)
                    
                    colab_atual = {
                        "MAT": mat_m.group(1) if mat_m else None,
                        "NOME": nome_m.group(1).strip() if nome_m else "",
                        "TOTAL": None, "VENCIDAS": None, "A VENCER": None
                    }
                    
                    # Tenta pegar o resto do nome na linha de baixo (se não tiver CC: ou DT.BASE)
                    if j + 1 < len(linhas) and "CC:" not in linhas[j+1] and "DT.BASE" not in linhas[j+1]:
                        # Pega apenas a parte do texto que não são etiquetas
                        nome_extra = re.sub(r'(FILIAL:|CC:|MAT:|DT.BASE:).*', '', linhas[j+1]).strip()
                        if nome_extra:
                            colab_atual["NOME"] += " " + nome_extra

                # Define Seção
                if "TOTAL" in linha and "FERIAS" not in linha: secao = "TOTAL"
                elif "VENCIDAS" in linha or "VENOIDAS" in linha: secao = "VENCIDAS"
                elif "A VENCER" in linha: secao = "A VENCER"

                # Pega Saldo
                if "Saldo" in linha and "Atual" in linha:
                    valores = extrair_valores_saldo(linha)
                    if valores: colab_atual[secao] = valores

            # Feedback de progresso
            if (i + 1) % 50 == 0:
                print(f"Página {i+1} processada...")

        # Salva o último colaborador do arquivo
        salvar_colaborador(colab_atual, writer)

print(f"Concluído! Arquivo {OUTPUT_CSV} gerado com sucesso.")
