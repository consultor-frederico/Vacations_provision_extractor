import pypdf
import re
import csv
import os

# O script vai procurar o arquivo automaticamente para evitar erro de digitação
def localizar_arquivo():
    arquivos = os.listdir('.')
    for f in arquivos:
        if f.startswith("1001") and f.endswith(".pdf"):
            return f
    return None

def formatar_valor(v):
    if not v: return 0.0
    res = v.strip().replace(".", "").replace(",", ".")
    if "(" in res:
        res = "-" + res.replace("(", "").replace(")", "")
    try:
        return float(res)
    except:
        return 0.0

def gravar_no_csv(dados, writer):
    if not dados or not dados['MAT']: return
    alvo = dados["TOTAL"] or dados["VENCIDAS"] or dados["A VENCER"]
    if not alvo and (dados["VENCIDAS"] and dados["A VENCER"]):
        alvo = [x + y for x, y in zip(dados["VENCIDAS"], dados["A VENCER"])]
    if alvo:
        linha = [dados["MAT"], dados["NOME"]] + [f"{x:.2f}".replace(".", ",") for x in alvo]
        writer.writerow(linha)

print("--- DIAGNÓSTICO DE AMBIENTE ---")
pdf_encontrado = localizar_arquivo()
if not pdf_encontrado:
    print(f"ERRO: Nenhum arquivo PDF começando com '1001' foi encontrado na pasta raiz.")
    print(f"Arquivos presentes: {os.listdir('.')}")
    exit(1)
else:
    print(f"Sucesso! Arquivo localizado: {pdf_encontrado}")

with open("provisao_ferias.csv", 'w', newline='', encoding='utf-8-sig') as f_out:
    writer = csv.writer(f_out, delimiter=';')
    writer.writerow(["MAT", "NOME", "DIAS", "VALOR", "ADIC_1_3", "TOTAL_FERIAS", "INSS", "FGTS", "ENCARGOS", "GERAL"])

    colab = {"MAT": None, "NOME": "", "TOTAL": None, "VENCIDAS": None, "A VENCER": None}
    secao = None

    reader = pypdf.PdfReader(pdf_encontrado)
    for i, pagina in enumerate(reader.pages):
        texto = pagina.extract_text()
        if not texto: continue

        for linha in texto.split("\n"):
            if "MAT:" in linha and "NOME:" in linha:
                gravar_no_csv(colab, writer)
                m = re.search(r'MAT:\s*(\w+)', linha)
                n = re.search(r'NOME:\s*(.*)', linha)
                colab = {"MAT": m.group(1) if m else None, "NOME": n.group(1).strip() if n else "", 
                         "TOTAL": None, "VENCIDAS": None, "A VENCER": None}
            
            if "TOTAL" in linha and "FERIAS" not in linha: secao = "TOTAL"
            elif "VENCIDAS" in linha: secao = "VENCIDAS"
            elif "A VENCER" in linha: secao = "A VENCER"

            if "Saldo" in linha and "Atual" in linha:
                nums = re.findall(r'\(?\d+(?:\.\d{3})*,\d{2}\)?', linha)
                if len(nums) >= 8:
                    v = [formatar_valor(x) for x in nums]
                    colab[secao] = [v[0], v[1], v[2]+v[3], v[4], v[5], v[6], v[7], v[8]] if len(v) >= 9 else v

        if (i + 1) % 50 == 0:
            print(f"Páginas processadas: {i+1}/{len(reader.pages)}")

    gravar_no_csv(colab, writer)
