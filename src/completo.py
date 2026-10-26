"""Rodada com todas as seções do 2º turno.

Guarda os arquivos de cada urna em dados/urnas (~95 GB) para novas análises sem
baixar de novo, grava uma linha por seção em saida/secoes.csv e retoma de onde parou.

Uso: python -E -s src/completo.py [conexoes]
     python -E -s src/completo.py local   # relê só o cache, em vários processos
"""

import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from amostra import SAIDA, UFS, processar, secoes

CSV = SAIDA / "secoes.csv"
COLUNAS = ["uf", "mun", "zona", "secao", "abertura", "fuso", "votos", "tardios", "ultimo",
           "lula", "flavio", "branco", "nulo", "por_hora", "pos17_min", "sem_log", "log_ajustado", "erro"]


def linha(r: dict) -> dict:
    bu = r.pop("bu", {})
    return {**r, "lula": bu.get("13", 0), "flavio": bu.get("22", 0),
            "branco": bu.get("branco", 0), "nulo": bu.get("nulo", 0)}


def tentar(secao):
    try:
        return processar(secao, guardar=True)
    except Exception as erro:
        uf, mu, zo, se = secao
        return {"uf": uf, "mun": mu, "zona": zo, "secao": se, "erro": str(erro)[:200]}


def main() -> None:
    local = len(sys.argv) > 1 and sys.argv[1] == "local"
    conexoes = 16 if local or len(sys.argv) < 2 else int(sys.argv[1])
    with ThreadPoolExecutor(16) as pool:
        todas = [s for lista in pool.map(secoes, UFS) for s in lista]

    feitas = set()
    if CSV.exists():
        with CSV.open() as f:
            feitas = {(r["uf"], r["mun"], r["zona"], r["secao"]) for r in csv.DictReader(f) if not r["erro"]}
    pendentes = [s for s in todas if s not in feitas]
    print(f"{len(todas)} seções; {len(feitas)} já feitas; {len(pendentes)} pendentes", flush=True)

    SAIDA.mkdir(exist_ok=True)
    novo = not CSV.exists()
    inicio, feitos, erros = time.time(), 0, 0
    # baixando, o gargalo é a rede (threads); relendo o cache, é a CPU (processos)
    pool = ProcessPoolExecutor(os.cpu_count()) if local else ThreadPoolExecutor(conexoes)
    with CSV.open("a", newline="") as f, pool:
        escritor = csv.DictWriter(f, COLUNAS)
        if novo:
            escritor.writeheader()
        for r in pool.map(tentar, pendentes, chunksize=64 if local else 1):
            escritor.writerow(linha(r))
            feitos += 1
            erros += "erro" in r
            if feitos % 2000 == 0:
                f.flush()
                ritmo = feitos / (time.time() - inicio)
                falta = (len(pendentes) - feitos) / ritmo / 3600
                print(f"  {feitos}/{len(pendentes)}  {ritmo:.0f}/s  erros {erros}  faltam ~{falta:.1f} h",
                      flush=True)
    print("fim", flush=True)


if __name__ == "__main__":
    main()
