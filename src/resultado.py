"""Consolida saida/secoes.csv, calcula os cenários e gera saida/municipios.csv.

Uso: python -E -s src/resultado.py
"""

import csv
import gzip
import json
from collections import defaultdict

from amostra import BASE, CACHE, PLEITO, SAIDA, UFS, baixar

# Resultado oficial do TSE (divulgação final, 25/10/2026 23:27)
OFICIAL = {"lula": 64_256_232, "flavio": 59_826_041}


def carregar() -> list[dict]:
    por_secao = {}
    # secoes.csv sai de completo.py; o repositório traz a versão comprimida
    csv_ = SAIDA / "secoes.csv"
    with (csv_.open() if csv_.exists() else gzip.open(SAIDA / "secoes.csv.gz", "rt")) as f:
        for r in csv.DictReader(f):
            chave = (r["uf"], r["mun"], r["zona"], r["secao"])
            # na retomada, uma seção que falhou pode aparecer de novo; vale a que deu certo
            if chave not in por_secao or por_secao[chave]["erro"]:
                por_secao[chave] = r
    for r in por_secao.values():
        for c in ("votos", "tardios", "lula", "flavio", "branco", "nulo"):
            r[c] = int(r[c] or 0)
    return list(por_secao.values())


def percentuais(lula: float, flavio: float) -> dict:
    validos = lula + flavio
    return {"lula": lula, "flavio": flavio, "lula_pct": 100 * lula / validos,
            "flavio_pct": 100 * flavio / validos, "margem": lula - flavio}


def nomes_municipios() -> dict[tuple[str, str], str]:
    nomes = {}
    for uf in UFS:
        cfg = json.loads(baixar(f"{BASE}/config/{uf}/{uf}-p{PLEITO}-cs.json", CACHE / "config" / f"{uf}.json"))
        nomes |= {(uf, mu["cd"]): mu["nm"] for abr in cfg["abr"] for mu in abr["mu"]}
    return nomes


def municipios(ok: list[dict]) -> None:
    """Uma linha por município, com nomes de coluna que se explicam: pequeno o bastante para uma IA."""
    nomes = nomes_municipios()
    soma = defaultdict(lambda: defaultdict(int))
    ultimo = {}
    for r in ok:
        chave = (r["uf"], r["mun"])
        m = soma[chave]
        minutos = [int(x) for x in r["pos17_min"].split()] if r["pos17_min"] else [0] * 61
        m["secoes"] += 1
        m["comparecimento"] += r["lula"] + r["flavio"] + r["branco"] + r["nulo"]
        m["votos_lula"] += r["lula"]
        m["votos_flavio"] += r["flavio"]
        m["votos_brancos"] += r["branco"]
        m["votos_nulos"] += r["nulo"]
        m["votos_com_horario_no_log"] += r["votos"]
        m["votos_depois_das_17h"] += r["tardios"]
        m["votos_das_17h00_as_17h04"] += sum(minutos[:5])
        m["votos_depois_das_18h"] += minutos[60]
        if r["ultimo"]:
            ultimo[chave] = max(ultimo.get(chave, ""), r["ultimo"])
    with (SAIDA / "municipios.csv").open("w", newline="") as f:
        campos = ["uf", "municipio", "codigo_tse", "secoes", "comparecimento", "votos_lula", "votos_flavio",
                  "votos_brancos", "votos_nulos", "votos_com_horario_no_log", "votos_depois_das_17h",
                  "pct_votos_depois_das_17h", "votos_das_17h00_as_17h04", "votos_depois_das_18h",
                  "ultimo_voto_hora_local"]
        escritor = csv.DictWriter(f, campos)
        escritor.writeheader()
        for (uf, mu), m in sorted(soma.items(), key=lambda x: (x[0][0], nomes.get(x[0], ""))):
            pct = 100 * m["votos_depois_das_17h"] / m["votos_com_horario_no_log"] if m["votos_com_horario_no_log"] else 0
            escritor.writerow({"uf": uf.upper(), "municipio": nomes.get((uf, mu), ""), "codigo_tse": mu, **m,
                               "pct_votos_depois_das_17h": f"{pct:.3f}", "ultimo_voto_hora_local": ultimo.get((uf, mu), "")})


def main() -> None:
    secoes = carregar()
    ok = [r for r in secoes if not r["erro"]]
    sem_log = [r for r in ok if r.get("sem_log")]
    com_log = [r for r in ok if not r.get("sem_log")]
    sem_horario = [r for r in com_log if not r["fuso"]]
    lula = sum(r["lula"] for r in ok)
    flavio = sum(r["flavio"] for r in ok)
    votos = sum(r["votos"] for r in ok)
    tardios = sum(r["tardios"] for r in ok)
    comparecimento = sum(r["lula"] + r["flavio"] + r["branco"] + r["nulo"] for r in ok)

    # Estimativa: quem votou tarde votou como o resto da própria seção.
    tardios_lula = sum(r["lula"] * r["tardios"] / r["votos"] for r in ok if r["votos"])
    tardios_flavio = sum(r["flavio"] * r["tardios"] / r["votos"] for r in ok if r["votos"])

    por_uf = defaultdict(lambda: [0, 0])
    for r in ok:
        por_uf[r["uf"]][0] += r["votos"]
        por_uf[r["uf"]][1] += r["tardios"]

    resultado = {
        "secoes": {
            "total": len(secoes), "lidas": len(ok), "falhas": len(secoes) - len(ok),
            "publicadas_sem_log": [f"{r['uf']}/{r['mun']}/{r['zona']}/{r['secao']}" for r in sem_log if r["sem_log"] != "sa"],
            "apuradas_pelo_sa_sem_log": sum(r["sem_log"] == "sa" for r in sem_log),
            "nao_instaladas": sum(r["erro"].startswith("sem arquivos") for r in secoes),
            "sem_horario_de_abertura": len(sem_horario),
            "log_com_menos_votos_que_bu": sum(r["votos"] < r["lula"] + r["flavio"] + r["branco"] + r["nulo"] for r in com_log),
            "log_com_mais_votos_que_bu": sum(r["votos"] > r["lula"] + r["flavio"] + r["branco"] + r["nulo"] for r in com_log),
            "log_de_outra_urna_descartado": sum(r.get("log_ajustado") == "True" for r in com_log),
            "com_voto_pos_17h": sum(r["tardios"] > 0 for r in ok),
        },
        "votos": {
            "comparecimento_bu": comparecimento, "votos_no_log": votos, "pos_17h": tardios,
            "pos_17h_pct": 100 * tardios / votos, "ultimo_voto": max(r["ultimo"] for r in ok if r["ultimo"]),
        },
        "conferencia_oficial": {
            "lula_bu": lula, "lula_tse": OFICIAL["lula"],
            "flavio_bu": flavio, "flavio_tse": OFICIAL["flavio"],
        },
        "cenarios": {
            "real": percentuais(lula, flavio),
            # Pior caso sem suposição nenhuma: todo voto pós-17h era do Lula e passa ao Flávio.
            "pior_caso_todos_pos17h_do_lula_para_flavio": percentuais(lula - tardios, flavio + tardios),
            # Estimativa: tira dos dois na proporção da seção e dá todos ao Flávio.
            "estimado_todos_pos17h_para_flavio": percentuais(lula - tardios_lula, flavio - tardios_flavio + tardios),
            "estimado_sem_votos_pos17h": percentuais(lula - tardios_lula, flavio - tardios_flavio),
        },
        "votos_que_flavio_precisaria_para_virar": (lula - flavio) // 2 + 1,
        "por_uf": {uf: {"votos": v, "pos_17h": t, "pct": 100 * t / v}
                   for uf, (v, t) in sorted(por_uf.items(), key=lambda x: -x[1][1] / max(x[1][0], 1))},
    }
    municipios(ok)
    (SAIDA / "resultado.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in resultado.items() if k != "por_uf"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
