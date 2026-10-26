# Votos depois das 17h — 2º turno presidencial 2026

Quantos eleitores votaram depois das 17h no 2º turno de 25/10/2026, e o resultado mudaria se todos eles tivessem votado no Flávio?

**Não mudaria.** Foram 34.716 votos depois das 17h (0,027% do comparecimento): 34.330 no Brasil e 386 no exterior. Mesmo no pior caso possível para o Lula, em que todos esses eleitores tivessem votado nele e passassem a votar no Flávio, o Lula venceria com 51,76% dos votos válidos, por 4.360.759 votos de diferença.

| Cenário | Lula (13) | Flávio (22) | Vantagem do Lula |
|---|---|---|---|
| Resultado oficial | 51,79% | 48,21% | 4.430.191 |
| Todos os votos pós-17h para o Flávio, **pior caso** | 51,76% | 48,24% | 4.360.759 |
| Todos os votos pós-17h para o Flávio, estimado | 51,77% | 48,23% | 4.392.505 |
| Sem os votos pós-17h, estimado | 51,78% | 48,22% | 4.427.221 |

Para virar, 2.215.096 eleitores do Lula teriam de ter votado no Flávio: cerca de 64 vezes o número de pessoas que votaram depois das 17h.

E quase todos os votos depois das 17h foram nos primeiros minutos: 84% até 17h05 e 88% até 17h10. É a fila de quem já estava na seção às 17h, que por lei tem direito de votar. Depois das 18h foram 1.993 votos no país inteiro.

## 🤖 Analise os dados com uma IA

Não precisa saber programar. Baixe os arquivos abaixo, envie para o ChatGPT, o Claude, o Gemini ou outra IA e faça perguntas.

| Arquivo | O que tem | Para quê |
|---|---|---|
| [`saida/LEIA-ME-IA.md`](saida/LEIA-ME-IA.md) | dicionário dos dados: cada coluna, os fusos, as lacunas e os totais esperados | **envie sempre junto**, para a IA entender os dados e conferir a própria leitura |
| [`saida/municipios.csv`](saida/municipios.csv) | uma linha por município (5.717 linhas, 430 KB) | a IA lê direto |
| [`saida/secoes.csv.gz`](saida/secoes.csv.gz) | uma linha por seção (499.248 linhas, 13 MB), com votos por hora e por minuto depois das 17h | a IA analisa rodando código (Python) |

Perguntas para começar:

- "Confira se os totais batem com os do LEIA-ME e refaça o pior caso."
- "Quais municípios tiveram a maior porcentagem de votos depois das 17h?"
- "Faça um gráfico de votos por minuto depois das 17h, por região."
- "Em que estados a fila acabou mais tarde?"

Lembre que nenhum arquivo diz em quem votaram os eleitores depois das 17h, porque o voto é secreto. Se a IA afirmar isso, ela está supondo.

## O que se sabe e o que não se sabe

Cada urna publica, no site do TSE, dois arquivos que importam aqui:

- o **boletim de urna**: quantos votos cada candidato teve naquela seção;
- o **log da urna**: um diário do que a urna fez no dia, com data e hora, ao segundo. Cada voto aparece como uma linha `O voto do eleitor foi computado`.

Com isso:

- **A hora de cada voto se sabe.** A contagem de votos depois das 17h é exata.
- **Em quem cada eleitor votou não se sabe.** O voto é secreto: o log mostra só que alguém votou, e o arquivo com os votos (o RDV) é embaralhado e não tem horário. Por isso os cenários são hipóteses, não afirmações sobre como esses eleitores votaram.
  - **Pior caso:** não depende de suposição nenhuma. Cada eleitor depois das 17h tira 1 voto do Lula e dá 1 ao Flávio, então a vantagem cai 2 votos por eleitor.
  - **Estimado:** supõe que quem votou depois das 17h votou como o resto da própria seção.

## Confira uma seção você mesmo

### Sem instalar nada

Os arquivos são públicos e abrem no navegador. Exemplo com a seção 372, zona 4, de Fernando de Noronha (PE):

1. Abra o índice da seção:
   https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221/dados/pe/30015/0004/0372/p003221-pe-m30015-z0004-s0372-aux.json
   Ele traz um `hash` (um código longo) e os nomes dos arquivos da urna.
2. Baixe o log juntando a pasta da seção, o hash e o nome do arquivo que termina em `-log.jez`:
   `https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221/dados/pe/30015/0004/0372/<hash>/<nome>-log.jez`
3. O `.jez` é um arquivo compactado. Troque a extensão para `.zip`, abra e leia o `logd.dat` num editor de texto.
4. Procure as linhas `O voto do eleitor foi computado` do dia 25/10/2026. Em Noronha o relógio da urna está uma hora à frente de Brasília, então 17h de Brasília aparece como 18h.

Para outra seção, troque a UF, o código do município, a zona e a seção no endereço. O código do município está em `saida/municipios.csv`, na coluna `codigo_tse`.

### Com um comando

Com o [Python](https://www.python.org/downloads/) 3.11 ou mais recente instalado, baixe este repositório e rode, na pasta dele:

```bash
python3 -E -s src/conferir.py pe "Fernando de Noronha" 4 372
```

```
FERNANDO DE NORONHA (PE), zona 0004, seção 0372
Boletim de urna: Lula 136 · Flávio 83 · brancos 2 · nulos 2
Log da urna: 223 votos computados, abertura às 09:04 (hora local)
Votos depois das 17h de Brasília: 3
  18:11:44 local (17:11:44 em Brasília)
  19:28:30 local (18:28:30 em Brasília)
  19:49:09 local (18:49:09 em Brasília)
```

Zona e seção estão no título de eleitor ou no app e-Título. O município pode ir pelo nome.

## Como a conta foi feita

1. **Seções.** A lista sai da configuração de cada UF no site do TSE. Seções agregadas, cujos eleitores votam na urna de outra seção, ficam de fora: são 499.248 seções com urna própria.
2. **Votos por candidato.** Saem do boletim de urna, na parte da eleição para presidente.
3. **Hora de cada voto.** Cada linha `O voto do eleitor foi computado` do log é um voto. A linha "Voto confirmado" não serve: se a urna reinicia entre a confirmação e a gravação, aquele voto se perde e o eleitor vota de novo.
4. **Troca de urna.** Quando uma urna é substituída, o pacote traz também o log da anterior, e os votos dos dois são somados. Linhas repetidas entre os dois contam uma vez só. Num caso, o pacote trazia o log de uma urna de outra seção; ficou a combinação de logs que bate exatamente com o boletim.
5. **Corte das 17h de Brasília.** A votação vai das 8h às 17h de Brasília no país inteiro, mas o relógio de cada urna está na hora local. O fuso sai da hora em que a urna ficou pronta para votar, limitado aos fusos possíveis na UF. Fernando de Noronha é +1. No exterior, a votação segue o horário local, e o corte é às 17h locais.
6. **Conferência.** Em cada seção, o número de votos no log é comparado com o boletim. A soma de todos os boletins é comparada com o resultado oficial do TSE.

## Conferência

- **A soma dos boletins bate exatamente com o resultado oficial do TSE:** Lula 64.256.232 e Flávio 59.826.041.
- **Seções lidas: 499.207 de 499.248.** As outras 41 são seções no exterior que não foram instaladas e não tiveram votos.
- **Seções sem log de votação: 31.** São 2 publicadas pelo TSE sem log e 29 no exterior apuradas pelo Sistema de Apuração (SA). Os votos delas entram nos totais, mas sem horário.
- **Seções com menos votos no log que no boletim: 6.** Ou a urna gravou o voto mas reiniciou antes de escrever a linha do log, ou abriu tarde e parte da votação foi em outra urna ou em cédula. Nenhuma seção tem mais votos no log que no boletim.

Ao todo, 1.339 votos (0,001%) não têm horário. Mesmo contando todos eles como depois das 17h no pior caso, a vantagem do Lula seria de 4.358.081 votos.

## Refazer tudo do zero

```bash
python3 -E -s src/completo.py 16     # baixa todas as seções (~90 GB, algumas horas; retoma se parar)
python3 -E -s src/resultado.py       # calcula os cenários e gera resultado.json e municipios.csv
```

O `16` é o número de downloads em paralelo. Com mais que isso, o servidor do TSE começa a recusar (erro 429). `python3 -E -s src/amostra.py 3000` faz uma amostra aleatória de 3.000 seções em poucos minutos.

Código:

- `src/conferir.py`: confere uma seção direto no site do TSE.
- `src/amostra.py`: lê o boletim de urna e o log, e faz amostras aleatórias.
- `src/completo.py`: baixa e lê todas as seções, com retomada.
- `src/resultado.py`: soma tudo, calcula os cenários e gera os arquivos de `saida/`.

## Fonte

Dados públicos do TSE: https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221 (pleito 3221 é o 2º turno).

- lista de seções de cada UF: `config/<uf>/<uf>-p003221-cs.json`;
- índice de cada seção: `dados/<uf>/<município>/<zona>/<seção>/p003221-<uf>-m<município>-z<zona>-s<seção>-aux.json`, com o hash e os nomes dos arquivos;
- boletim e log: `dados/<uf>/<município>/<zona>/<seção>/<hash>/<nome do arquivo>`.
