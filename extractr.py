name: Extrator de Ferias v2
on: [workflow_dispatch]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4 # Versão estável do checkout

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11' # Versão moderna e estável

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run script
        run: python extrair_ferias.py

      - name: Upload result
        uses: actions/upload-artifact@v4
        with:
          name: relatorio-final
          path: provisao_ferias.csv
