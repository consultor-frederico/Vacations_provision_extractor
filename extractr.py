import pypdf
import re
import csv

# Configurações
PDF_PATH = "1001 a 1012 Provisao Ferias 012026.pdf"
OUTPUT_CSV = "provisao_ferias.csv"

def limpar_valor(v):
    """Converte o formato brasileiro (1.234,56) para float puro."""
    if not v or v.strip() in ["-", ""]: return 0.0
    res = v.replace(".", "").replace(",", ".")
    if "(" in res: # Trata negativos (100,00)
        res = "-" + res.replace("(", "").replace(")", "")
    try: return float(res)
    except: return 0.0

def processar_e_salvar(colab, writer):
    """Aplica a regra de hierarquia e grava no CSV."""
    if not colab or not colab['MAT']: return

    # Regra: TOTAL > (VENCIDAS + A VENCER)
    if colab["TOTAL"]:
        dados = colab["TOTAL"]
    elif colab["VENCIDAS"] and colab["A VENCER"]:
        dados = [x + y for x, y in zip(colab["VENCIDAS"], colab["A VENCER"])]
    elif colab["VENCIDAS"]:
        dados = colab["VENCIDAS"]
    elif colab["A VENCER"]:
        dados = colab["A VENCER"]
    else: return

    # Prepara a linha formatada
    linha_formatada = [colab["MAT"], colab["NOME"]] + [f"{x:.2f}".replace(".", ",") for x in dados]
    writer.writerow(linha_formatada)

# --- INÍCIO DO PROCESSO ---
print(f"Iniciando processamento de {PDF_PATH}...")

with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8-sig') as f_out:
    writer = csv.writer(f_out, delimiter=';')
    writer.writerow(["MAT", "NOME", "DIAS DE DIREITO", "VALOR", "ADICIONAIS 1/3 CONSTIT", "TOTAL FERIAS", "INSS", "FGTS", "TOT.ENCARGOS", "TOTAL GERAL"])

    colab_atual = {"MAT": None, "NOME": "", "TOTAL": None, "VENCIDAS": None, "A VENCER": None}
    secao_ativa = None

    reader = pypdf.PdfReader(PDF_PATH)
    total_paginas = len(reader.pages)

    for i, pagina in enumerate(reader.pages):
        texto = pagina.extract_text()
        if not texto: continue

        for linha in texto.split("\n"):
            # 1. Identifica novo colaborador
            if "MAT:" in linha and "NOME:" in linha:
                if colab_atual["MAT"]: 
                    processar_e_salvar(colab_atual, writer)
                
                m = re.search(r'MAT:\s*(\w+)', linha)
                n = re.search(r'NOME:\s*(.*)', linha)
                colab_atual = {
                    "MAT": m.group(1) if m else None,
                    "NOME": n.group(1).strip() if n else "",
                    "TOTAL": None, "VENCIDAS": None, "A VENCER": None
                }
                continue

            # 2. Define a seção
            if "TOTAL" in linha and "FERIAS" not in linha: secao_ativa = "TOTAL"
            elif "VENCIDAS" in linha or "VENOIDAS" in linha: secao_ativa = "VENCIDAS"
            elif "A VENCER" in linha: secao_ativa = "A VENCER"

            # 3. Captura o Saldo Atual
            if "Saldo" in linha and "Atual" in linha:
                # Busca valores no formato 0,00 ou 1.234,56 ou (100,00)
                valores_str = re.findall(r'\(?\d+(?:\.\d{3})*,\d{2}\)?', linha)
                if len(valores_str) >= 8:
                    # Se houver 9 valores, somamos o 3º e 4º (Adicionais + 1/3)
                    v = [limpar_valor(x) for x in valores_str]
                    if len(v) >= 9:
                        final_v = [v[0], v[1], v[2]+v[3], v[4], v[5], v[6], v[7], v[8]]
                    else:
                        final_v = v
                    colab_atual[secao_ativa] = final_v

        # Feedback a cada 50 páginas
        if (i + 1) % 50 == 0:
            print(f"Progresso: {i + 1} / {total_paginas} páginas processadas...")

    # Salva o último do arquivo
    processar_e_salvar(colab_atual, writer)

print(f"Finalizado! O arquivo {OUTPUT_CSV} foi gerado com sucesso.")
