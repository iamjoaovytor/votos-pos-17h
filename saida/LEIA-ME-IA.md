# Dados: votos depois das 17h no 2º turno presidencial de 2026

Este arquivo descreve os dados desta pasta para quem for analisá-los, pessoa ou IA. Leia antes de calcular.

## Contexto

- Eleição: 2º turno para presidente, 25/10/2026. Candidatos: Lula (número 13) e Flávio (número 22).
- A votação vai das 8h às 17h de Brasília no país inteiro. Quem está na fila às 17h ainda vota. No exterior, a votação segue o horário local.
- Fonte: arquivos públicos de cada urna no site do TSE, https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221
  - **boletim de urna**: votos por candidato na seção;
  - **log da urna**: registro de cada voto computado, com data e hora ao segundo, sem dizer em quem foi o voto.
- **Não existe dado sobre em quem votou quem votou depois das 17h.** O voto é secreto. Qualquer número sobre isso é hipótese, e precisa ser dito como hipótese.

## Arquivos

### `municipios.csv`: uma linha por município (5.717 linhas, 430 KB)

Para ler direto. Separador vírgula, UTF-8, ponto como separador decimal.

| Coluna | Tipo | Significado |
|---|---|---|
| `uf` | texto | sigla da UF; `ZZ` é o exterior (nesse caso, `municipio` é a cidade no exterior) |
| `municipio` | texto | nome do município |
| `codigo_tse` | texto | código do município no TSE (não é o código do IBGE) |
| `secoes` | inteiro | seções com urna própria e boletim lido |
| `comparecimento` | inteiro | votos no boletim de urna: Lula + Flávio + brancos + nulos |
| `votos_lula`, `votos_flavio`, `votos_brancos`, `votos_nulos` | inteiro | votos no boletim de urna |
| `votos_com_horario_no_log` | inteiro | votos encontrados no log da urna; pode ser menor que `comparecimento` (veja "Lacunas") |
| `votos_depois_das_17h` | inteiro | votos computados às 17h00min00s de Brasília ou depois |
| `pct_votos_depois_das_17h` | decimal | `votos_depois_das_17h / votos_com_horario_no_log × 100` |
| `votos_das_17h00_as_17h04` | inteiro | votos de 17h00min00s a 17h04min59s de Brasília |
| `votos_depois_das_18h` | inteiro | votos às 18h de Brasília ou depois |
| `ultimo_voto_hora_local` | HH:MM:SS | hora do último voto **no relógio da urna** (hora local, não de Brasília) |

### `secoes.csv.gz`: uma linha por seção (499.248 linhas, 13 MB comprimido, 120 MB aberto)

Para analisar com código. CSV comprimido com gzip; em Python: `pd.read_csv("secoes.csv.gz", dtype=str)`. Leia como texto e converta as colunas numéricas, porque `mun`, `zona` e `secao` têm zeros à esquerda.

| Coluna | Significado |
|---|---|
| `uf` | sigla minúscula da UF; `zz` é o exterior |
| `mun`, `zona`, `secao` | código do município no TSE, zona e seção; juntos identificam a seção |
| `lula`, `flavio`, `branco`, `nulo` | votos no boletim de urna |
| `votos` | votos encontrados no log da urna |
| `tardios` | votos depois das 17h de Brasília (no exterior, 17h locais) |
| `abertura` | HH:MM em que a urna ficou pronta para votar, no relógio da urna |
| `ultimo` | HH:MM:SS do último voto, no relógio da urna |
| `fuso` | horas a somar a Brasília para chegar ao relógio da urna: 0, −1, −2 ou +1 (Noronha). Hora de Brasília = hora da urna − `fuso` |
| `por_hora` | 24 inteiros separados por espaço: votos em cada hora de Brasília, da 0h à 23h. Soma = `votos` |
| `pos17_min` | 61 inteiros separados por espaço: posição 0 a 59 = votos em cada minuto de 17h00 a 17h59 de Brasília; posição 60 = 18h ou depois. Soma = `tardios` |
| `sem_log` | vazio se há log. `True`: o TSE publicou a seção sem log. `sa`: seção do exterior apurada pelo Sistema de Apuração, sem log de votação. Nesses casos `votos`, `tardios` e os horários ficam vazios |
| `log_ajustado` | `True` quando o pacote trazia o log de uma urna de outra seção, que foi descartado |
| `erro` | preenchido em 41 seções do exterior que não foram instaladas (sem votos); as outras colunas ficam vazias ou zeradas |

No exterior, as horas são locais e `fuso` é 0, com duas exceções: uma urna em Lisboa e outra em Barcelona têm `fuso` 1. O horário de verão europeu acabou na madrugada de 25/10/2026, e o relógio delas ficou uma hora adiantado (abriram às "9h", que eram 8h locais). O corte das 17h foi ajustado para elas.

### `resultado.json`

Os números finais: totais, conferência com o TSE e os cenários.

## Totais para conferir a leitura

Se a sua soma não bater com estes números, a leitura está errada:

- seções: 499.248 linhas em `secoes.csv.gz`, das quais 41 com `erro`;
- votos Lula: 64.256.232; votos Flávio: 59.826.041 (iguais ao resultado oficial do TSE);
- comparecimento no boletim (Lula + Flávio + brancos + nulos): 128.236.074;
- votos com horário no log: 128.234.735;
- votos depois das 17h: 34.716, sendo 34.330 no Brasil e 386 no exterior (`uf` = `zz`); desses, 29.291 até 17h04min59s e 1.993 às 18h ou depois.

## Lacunas conhecidas

- 1.339 votos (0,001%) não têm horário: 31 seções sem log (`sem_log` preenchido) e 6 seções com menos votos no log que no boletim. Os votos estão nos totais por candidato, mas não dá para saber se foram antes ou depois das 17h.
- Nenhuma seção tem mais votos no log que no boletim.

## Cenários já calculados

Votos válidos = Lula + Flávio. Seja T = 34.716, o número de votos depois das 17h.

- **Pior caso** (sem suposição): todo eleitor depois das 17h tinha votado no Lula e passa ao Flávio. Lula − T, Flávio + T. Resultado: Lula 51,76%, vantagem de 4.360.759.
- **Estimado**: em cada seção, os votos depois das 17h tinham a mesma divisão do resto da seção (`tardios × lula / votos` para o Lula, idem para o Flávio).
- Para o Flávio virar, 2.215.096 eleitores teriam de trocar de lado (vantagem ÷ 2, arredondado para cima).

## Cuidados ao concluir

- Correlação entre votar tarde e o resultado de um município não mostra em quem os eleitores tardios votaram.
- Horário do relógio da urna é hora local. Para comparar entre UFs, use hora de Brasília (`por_hora`, `pos17_min`, `tardios` já estão em Brasília).
