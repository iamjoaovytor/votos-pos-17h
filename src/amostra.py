"""Leitura do boletim de urna e do log da urna, e uma amostra aleatória de seções.

Para cada seção, baixa o boletim de urna (votos por candidato) e o log da urna
(hora de cada voto) do site de resultados do TSE e conta os votos depois das 17h.

Uso: python -E -s src/amostra.py [n_secoes] [semente]
"""

import io
import json
import random
import socket
import sys
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from itertools import combinations
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "dados" / "urnas"
SAIDA = RAIZ / "saida"

BASE = "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221"
PLEITO = "003221"
ELEICAO = 6258
UFS = "ac al am ap ba ce df es go ma mg ms mt pa pb pe pi pr rj rn ro rr rs sc se sp to zz".split()
# "Computado" é o registro do voto gravado. "Voto confirmado" não serve: se a urna reinicia
# entre os dois, o voto se perde e o eleitor vota de novo.
VOTO = "O voto do eleitor foi computado"
ABERTURA = "Urna pronta para receber votos"
# Fusos possíveis em relação a Brasília, por UF; Fernando de Noronha (PE, município 30015) é +1.
FUSOS = {"ac": (-2,), "am": (-2, -1), "mt": (-1,), "ms": (-1,), "ro": (-1,), "rr": (-1,)}
NORONHA = "30015"

# A conexão com o TSE às vezes trava em IPv6; força IPv4.
_getaddrinfo = socket.getaddrinfo
socket.getaddrinfo = lambda *a, **k: [r for r in _getaddrinfo(*a, **k) if r[0] == socket.AF_INET]


def baixar(url: str, destino: Path | None = None) -> bytes:
    if destino and destino.exists() and destino.stat().st_size > 0:
        return destino.read_bytes()
    for tentativa in range(8):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                dados = r.read()
            if destino:
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(dados)
            return dados
        except Exception as erro:
            codigo = getattr(erro, "code", None)
            if tentativa == 7 or codigo == 404:
                raise RuntimeError(f"falhou {url}: {erro}") from erro
            # 429: o TSE está limitando; espera bem mais antes de tentar de novo
            time.sleep((15 if codigo == 429 else 1) * 2 ** min(tentativa, 4) * random.uniform(0.5, 1.5))


def secoes(uf: str) -> list[tuple[str, str, str, str]]:
    url = f"{BASE}/config/{uf}/{uf}-p{PLEITO}-cs.json"
    cfg = json.loads(baixar(url, CACHE / "config" / f"{uf}.json"))
    return [
        (uf, mu["cd"], zo["cd"], se["ns"])
        for abr in cfg["abr"]
        for mu in abr["mu"]
        for zo in mu["zon"]
        for se in zo["sec"]
        if "nsp" not in se  # seção agregada: os votos estão na urna da seção principal
    ]


# --- boletim de urna (DER, lido sem o esquema ASN.1) ---

def der(buf: bytes, i: int = 0, fim: int | None = None):
    """Itera (tag, construído, conteúdo) de uma sequência DER."""
    fim = len(buf) if fim is None else fim
    while i < fim:
        tag = buf[i]
        i += 1
        if tag & 0x1F == 0x1F:
            while buf[i] & 0x80:
                i += 1
            i += 1
        n = buf[i]
        i += 1
        if n & 0x80:
            k = n & 0x7F
            n = int.from_bytes(buf[i : i + k], "big")
            i += k
        yield tag, bool(tag & 0x20), buf[i : i + n]
        i += n


def inteiro(b: bytes) -> int:
    return int.from_bytes(b, "big", signed=True)


def votos_votaveis(no: bytes, votos: dict[str, int]) -> None:
    """Acha SEQUENCE {[1] tipoVoto, [2] quantidade, [3] {partido, código, ...}}."""
    for tag, cons, conteudo in der(no):
        if not cons:
            continue
        filhos = list(der(conteudo))
        tags = [t for t, _, _ in filhos]
        if tags[:2] == [0x81, 0x82]:
            tipo, qtd = inteiro(filhos[0][2]), inteiro(filhos[1][2])
            if tipo == 1 and len(filhos) > 2 and filhos[2][0] == 0xA3:
                codigo = inteiro(list(der(filhos[2][2]))[1][2])
                chave = str(codigo)
            else:
                chave = {2: "branco", 3: "nulo"}.get(tipo, f"tipo{tipo}")
            votos[chave] = votos.get(chave, 0) + qtd
        else:
            votos_votaveis(conteudo, votos)


def ler_bu(dados: bytes) -> dict[str, int]:
    envelope = list(der(list(der(dados))[0][2]))
    interno = next(c for t, _, c in envelope if t == 0x04)
    votos: dict[str, int] = {}

    def procurar(no: bytes) -> None:
        for tag, cons, conteudo in der(no):
            if not cons:
                continue
            filhos = list(der(conteudo))
            if filhos and filhos[0][0] == 0x02 and inteiro(filhos[0][2]) == ELEICAO:
                votos_votaveis(conteudo, votos)
            else:
                procurar(conteudo)

    procurar(list(der(interno))[0][2])
    return votos


# --- log da urna ---

def textos_log(dados: bytes) -> list[str]:
    """logd.dat da urna e, se houve troca de urna, os logs aninhados das anteriores."""
    textos = []
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        for nome in z.namelist():
            conteudo = z.read(nome)
            if nome.endswith(".jez"):
                textos += textos_log(conteudo)
            else:
                textos.append(conteudo.decode("latin-1"))
    return textos


def ler_log(dados: bytes, uf: str, mun: str = "", comparecimento: int | None = None) -> dict:
    # Um registro por arquivo de log: (aberturas, horários dos votos).
    registros, vistas = [], set()
    for texto in textos_log(dados):
        aberturas, votos = [], []
        for linha in texto.splitlines():
            # o log de uma urna substituída às vezes repete linhas do log principal
            if not linha.startswith("25/10/2026") or linha in vistas:
                continue
            vistas.add(linha)
            campos = linha.split("\t")
            if len(campos) < 5:
                continue
            if campos[4] == ABERTURA:
                aberturas.append(datetime.strptime(campos[0], "%d/%m/%Y %H:%M:%S"))
            elif campos[4] == VOTO:
                votos.append(datetime.strptime(campos[0], "%d/%m/%Y %H:%M:%S"))
        if aberturas or votos:
            registros.append((aberturas, votos))
    # Às vezes o pacote traz o log de uma urna que não é desta seção. Se a soma não bate
    # com o boletim, fica a combinação de logs que bate exatamente.
    ajustado = False
    if comparecimento is not None and sum(len(v) for _, v in registros) != comparecimento:
        for n in range(len(registros) - 1, 0, -1):
            certo = next((c for c in combinations(registros, n)
                          if sum(len(v) for _, v in c) == comparecimento), None)
            if certo:
                registros, ajustado = list(certo), True
                break
    abertura = min((a for ab, _ in registros for a in ab), default=None)
    horas = [h for _, v in registros for h in v]
    # Abertura oficial é 8h de Brasília; o fuso sai da hora em que a urna ficou pronta,
    # limitado aos fusos da UF (urna aberta com atraso não pode empurrar o corte).
    # No exterior (zz) a votação segue o horário local, então o corte é 17h local.
    possiveis = (1,) if mun == NORONHA else FUSOS.get(uf, (0,))
    if abertura is None:
        if uf == "zz" or len(possiveis) > 1:
            return {"abertura": None, "votos": len(horas), "tardios": 0}
        fuso = possiveis[0]
    else:
        fuso = abertura.hour - 8
        if uf != "zz":
            fuso = max((f for f in possiveis if f <= fuso), default=possiveis[0])
    corte = datetime(2026, 10, 25, 17 + fuso)
    tardios = sum(h >= corte for h in horas)
    # Votos por hora (horário de Brasília, 0..23) e, depois das 17h, por minuto (0..59, 60 = 18h ou mais).
    por_hora = [0] * 24
    pos17_min = [0] * 61
    for h in horas:
        por_hora[(h.hour - fuso) % 24] += 1
        if h >= corte:
            pos17_min[min(int((h - corte).total_seconds() // 60), 60)] += 1
    return {
        "abertura": abertura.strftime("%H:%M") if abertura else None,
        "fuso": fuso,
        "votos": len(horas),
        "tardios": tardios,
        "ultimo": max(horas).strftime("%H:%M:%S") if horas else None,
        "por_hora": " ".join(map(str, por_hora)),
        "pos17_min": " ".join(map(str, pos17_min)),
        "log_ajustado": ajustado,
    }


def processar(secao: tuple[str, str, str, str], guardar: bool = True) -> dict:
    """Lê uma seção; com guardar=True os arquivos da urna ficam em dados/urnas para reuso."""
    uf, mu, zo, se = secao
    pasta = f"{BASE}/dados/{uf}/{mu}/{zo}/{se}"
    nome = f"p{PLEITO}-{uf}-m{mu}-z{zo}-s{se}"
    pasta_local = CACHE / uf / mu / zo / se

    def local(arquivo: str) -> Path | None:
        return pasta_local / arquivo if guardar else None

    aux = json.loads(baixar(f"{pasta}/{nome}-aux.json", local("aux.json")))
    hashes = [h for h in aux.get("hashes", []) if h.get("st") in ("Totalizado", "Recebido")]
    base = {"uf": uf, "mun": mu, "zona": zo, "secao": se}
    if not hashes:
        return {**base, "erro": f"sem arquivos ({aux.get('st')})"}
    h = hashes[-1]
    arqs = {a["tp"]: a["nm"] for a in h["arq"]}
    if "bu" not in arqs and "busa" not in arqs:
        return {**base, "erro": f"faltam arquivos {sorted(arqs)}"}
    if "bu" not in arqs:
        # seção apurada pelo Sistema de Apuração (SA): o boletim existe, mas não há log de votação
        bu = ler_bu(baixar(f"{pasta}/{h['hash']}/{arqs['busa']}", local("busa.dat")))
        return {**base, "bu": bu, "sem_log": "sa"}
    bu = ler_bu(baixar(f"{pasta}/{h['hash']}/{arqs['bu']}", local("bu.dat")))
    if "log" not in arqs:
        # o TSE publicou a seção sem log: os votos contam no total, mas sem horário
        return {**base, "bu": bu, "sem_log": True}
    log = ler_log(baixar(f"{pasta}/{h['hash']}/{arqs['log']}", local("log.jez")), uf, mu, sum(bu.values()))
    return {**base, **log, "bu": bu}


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    semente = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
    with ThreadPoolExecutor(16) as pool:
        todas = [s for lista in pool.map(secoes, UFS) for s in lista]
    print(f"{len(todas)} seções no 2º turno; sorteando {n}", flush=True)
    amostra = random.Random(semente).sample(todas, n)

    resultados, feitos = [], 0
    with ThreadPoolExecutor(24) as pool:
        for r in pool.map(lambda s: _seguro(s), amostra):
            resultados.append(r)
            feitos += 1
            if feitos % 200 == 0:
                print(f"  {feitos}/{n}", flush=True)

    SAIDA.mkdir(exist_ok=True)
    (SAIDA / f"amostra_{n}_{semente}.json").write_text(
        json.dumps({"total_secoes": len(todas), "secoes": resultados}, ensure_ascii=False)
    )
    resumir(resultados, len(todas))


def _seguro(secao):
    try:
        return processar(secao)
    except Exception as erro:
        uf, mu, zo, se = secao
        return {"uf": uf, "mun": mu, "zona": zo, "secao": se, "erro": str(erro)}


def resumir(resultados: list[dict], total_secoes: int) -> None:
    ok = [r for r in resultados if "erro" not in r and r.get("abertura")]
    falhas = len(resultados) - len(ok)
    tot = {"13": 0, "22": 0}
    sem = {"13": 0.0, "22": 0.0}
    votos = tardios = divergentes = 0
    for r in ok:
        comparecimento = sum(r["bu"].values())
        if comparecimento != r["votos"]:
            divergentes += 1
        votos += r["votos"]
        tardios += r["tardios"]
        fracao = r["tardios"] / r["votos"] if r["votos"] else 0
        for c in tot:
            v = r["bu"].get(c, 0)
            tot[c] += v
            sem[c] += v * (1 - fracao)

    def pct(d):
        validos = d["13"] + d["22"]
        return 100 * d["13"] / validos, 100 * d["22"] / validos

    l, f = pct(tot)
    ls, fs = pct(sem)
    print()
    print(f"seções válidas: {len(ok)} (falhas: {falhas}; log≠BU: {divergentes})")
    print(f"votos na amostra: {votos:,}; depois das 17h: {tardios:,} ({100*tardios/votos:.2f}%)")
    print(f"seções com voto depois das 17h: {sum(r['tardios'] > 0 for r in ok)}")
    print(f"amostra com todos:      Lula {l:.2f}%  Flávio {f:.2f}%")
    print(f"amostra sem pós-17h:    Lula {ls:.2f}%  Flávio {fs:.2f}%")
    print(f"diferença:              Lula {ls-l:+.3f} pp")
    por_uf = {}
    for r in ok:
        u = por_uf.setdefault(r["uf"], [0, 0])
        u[0] += r["votos"]
        u[1] += r["tardios"]
    print("\npós-17h por UF (amostra):")
    for uf, (v, t) in sorted(por_uf.items(), key=lambda x: -x[1][1] / max(x[1][0], 1)):
        print(f"  {uf}: {100*t/v:5.2f}% de {v:,}")


if __name__ == "__main__":
    main()
