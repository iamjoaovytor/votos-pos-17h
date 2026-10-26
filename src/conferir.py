"""Confere uma seção direto no site do TSE: votos no boletim e cada voto depois das 17h.

Uso: python3 -E -s src/conferir.py <uf> <município> <zona> <seção>
     python3 -E -s src/conferir.py sp "São Paulo" 1 15
O município pode ser o nome ou o código do TSE.
"""

import json
import sys
import unicodedata
from datetime import datetime, timedelta

from amostra import BASE, PLEITO, VOTO, baixar, ler_bu, ler_log, textos_log


def sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().upper()


def achar_municipio(uf: str, municipio: str) -> tuple[str, str]:
    cfg = json.loads(baixar(f"{BASE}/config/{uf}/{uf}-p{PLEITO}-cs.json"))
    for abr in cfg["abr"]:
        for mu in abr["mu"]:
            if municipio.lstrip("0") == mu["cd"].lstrip("0") or sem_acento(municipio) == sem_acento(mu["nm"]):
                return mu["cd"], mu["nm"]
    sys.exit(f"Município {municipio!r} não encontrado em {uf.upper()}.")


def main() -> None:
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    uf = sys.argv[1].lower()
    mu, nome = achar_municipio(uf, sys.argv[2])
    zo, se = sys.argv[3].zfill(4), sys.argv[4].zfill(4)
    pasta = f"{BASE}/dados/{uf}/{mu}/{zo}/{se}"
    try:
        aux = json.loads(baixar(f"{pasta}/p{PLEITO}-{uf}-m{mu}-z{zo}-s{se}-aux.json"))
    except RuntimeError:
        sys.exit(f"Zona {zo}, seção {se} não encontrada em {nome}. Confira os números no título de eleitor.")
    hashes = [h for h in aux.get("hashes", []) if h.get("st") in ("Totalizado", "Recebido")]
    if not hashes:
        sys.exit(f"{nome}, zona {zo}, seção {se}: sem arquivos de urna ({aux.get('st')}).")
    h = hashes[-1]
    arqs = {a["tp"]: a["nm"] for a in h["arq"]}

    bu = ler_bu(baixar(f"{pasta}/{h['hash']}/{arqs.get('bu') or arqs['busa']}"))
    print(f"{nome} ({uf.upper()}), zona {zo}, seção {se}")
    print(f"Boletim de urna: Lula {bu.get('13', 0)} · Flávio {bu.get('22', 0)} · "
          f"brancos {bu.get('branco', 0)} · nulos {bu.get('nulo', 0)}")
    if "log" not in arqs:
        print("O TSE não publicou log de votação desta seção.")
        return

    dados = baixar(f"{pasta}/{h['hash']}/{arqs['log']}")
    log = ler_log(dados, uf, mu, sum(bu.values()))
    print(f"Log da urna: {log['votos']} votos computados, abertura às {log['abertura']} (hora local)")
    corte = datetime(2026, 10, 25, 17 + log["fuso"])
    # linhas repetidas entre o log principal e o de uma urna substituída contam uma vez
    tardios = sorted(linha.split("\t")[0] for linha in {
        linha
        for texto in textos_log(dados)
        for linha in texto.splitlines()
        if linha.startswith("25/10/2026") and linha.split("\t")[4:5] == [VOTO]
        and datetime.strptime(linha.split("\t")[0], "%d/%m/%Y %H:%M:%S") >= corte
    })
    exterior = uf == "zz"  # no exterior, o corte é às 17h locais
    print(f"Votos depois das 17h {'locais' if exterior else 'de Brasília'}: {log['tardios']}")
    for t in tardios:
        local = datetime.strptime(t, "%d/%m/%Y %H:%M:%S")
        brasilia = (local - timedelta(hours=log["fuso"])).strftime("%H:%M:%S")
        print(f"  {local:%H:%M:%S} local" + (f" ({brasilia} em Brasília)" if log["fuso"] and not exterior else ""))


if __name__ == "__main__":
    main()
