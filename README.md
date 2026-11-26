# Heap binário ou heap de Fibonacci no algoritmo de Dijkstra?

Código do artigo da disciplina Análise e Projeto de Algoritmos (CESUPA, 2026): o Dijkstra implementado em C++20 com heap binário e com heap de Fibonacci, comparados em tempo, operações da fila e memória na malha viária de Belém (OpenStreetMap) e em grafos sintéticos.

**Autores:** Lucas Augusto e Bernardo Lins
**Professor:** Isaac Souza Elgrably

## Requisitos

- **C++:** g++ 11 ou mais novo com suporte a C++20, no PATH. Usado nos experimentos: g++ 16.2.0 do MSYS2 UCRT64 (`C:\msys64\ucrt64\bin` no PATH).
- **Python:** 3.10 ou mais novo. Usado nos experimentos: 3.13.7.
- **Pacotes Python:** `networkx` (3.7) e `osmnx` (2.1.2). Para instalar:

```powershell
python -m pip install networkx osmnx
```

## Como compilar

Na raiz do repositório:

```powershell
.\compilar.ps1
```

Gera três executáveis em `build\`: `testes.exe`, `dijkstra.exe` e `gerador.exe`.

## Como gerar as instâncias

**Grafos sintéticos** (ficam em `dados\sinteticos\`, fora do controle de versão; saem iguais em qualquer máquina com a mesma semente):

```powershell
python scripts\gerar_sinteticos.py
```

Gera 24 instâncias: cada grafo tem um ciclo hamiltoniano mais arcos aleatórios, pesos inteiros de 1 a 1000, semente 2026.

**Malha de Belém** (requer internet na primeira execução; os arquivos gerados ficam versionados em `instancias\belem\`):

```powershell
python scripts\extrair_belem.py
```

Baixa a rede viária do OpenStreetMap centrada na Praça da República, recorta em raios de 1 a 10 km, mantém apenas a maior componente fortemente conexa e, entre arcos paralelos, o mais curto. A data do download e o centro estão em `instancias\belem\resumo.csv`. Os recortes ficam versionados porque o OpenStreetMap muda com o tempo.

Dados de mapa © colaboradores do OpenStreetMap, licença ODbL.

## Como rodar os testes de corretude

```powershell
.\build\testes.exe
```

Verifica a corretude do heap binário, do heap de Fibonacci e do Dijkstra em grafos pequenos com resposta conhecida.

```powershell
python testes\conferir_networkx.py
```

Confere o `dijkstra.exe` contra a NetworkX em 21 grafos gerados aleatoriamente (inteiros e reais, grafos conexos e desconexos).

```powershell
python testes\conferir_instancias.py
```

Confere o `dijkstra.exe` contra a NetworkX nas 18 instâncias do experimento (6 recortes de Belém e 12 sintéticas com até 50 000 vértices). Executar após gerar as instâncias.

## Como rodar os experimentos

```powershell
python scripts\rodar_experimentos.py
```

Roda o `dijkstra.exe` nas 30 instâncias (6 de Belém e 24 sintéticas) nas 4 combinações de fila e variante, com 10 repetições cada, e grava os resultados em `resultados\medicoes.csv`. Registra o ambiente de execução em `resultados\medicoes_ambiente.txt`.

```powershell
python scripts\checar_csv.py resultados\medicoes.csv
```

Verifica a integridade do CSV gerado.

**Dica de medição:** mantenha o notebook na tomada, no modo de energia "melhor desempenho", com outros programas fechados.

### Colunas do CSV

| Coluna                  | Significado                                                                                                                                                                                                                                                                                |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `instancia`           | Nome da instância (nome do arquivo sem extensão)                                                                                                                                                                                                                                         |
| `n`                   | Número de vértices do grafo                                                                                                                                                                                                                                                              |
| `m`                   | Número de arcos do grafo                                                                                                                                                                                                                                                                  |
| `fila`                | Tipo de fila de prioridade: `binario` ou `fibonacci`                                                                                                                                                                                                                                   |
| `variante`            | Quando os vértices entram na fila: `todos` insere todos no início (a origem com 0, os outros com infinito), e o primeiro alcance de um vértice conta como `decrease_key`; `alcance` insere cada vértice só quando ele é alcançado, e o primeiro alcance conta como `insert` |
| `repeticao`           | Número da repetição (1 a R)                                                                                                                                                                                                                                                             |
| `origem`              | Vértice de origem desta repetição                                                                                                                                                                                                                                                       |
| `tempo_ms`            | Tempo só do Dijkstra, em milissegundos (a leitura do grafo fica fora da medição)                                                                                                                                                                                                        |
| `insert`              | Número de inserções na fila                                                                                                                                                                                                                                                             |
| `extract_min`         | Número de extrações do mínimo                                                                                                                                                                                                                                                          |
| `decrease_key`        | Número de decrementos de chave                                                                                                                                                                                                                                                            |
| `comparacoes`         | Número de comparações realizadas pela fila                                                                                                                                                                                                                                              |
| `alcancados`          | Número de vértices alcançados a partir da origem                                                                                                                                                                                                                                        |
| `bytes_fila_pico`     | Pico de memória da própria fila em bytes, contado dentro da estrutura                                                                                                                                                                                                                    |
| `pico_processo_bytes` | Pico de memória do processo inteiro em bytes, inclui a leitura do grafo (use `bytes_fila_pico` para comparar as filas)                                                                                                                                                                  |

## Análise dos resultados

Depois de rodar os experimentos, gere as tabelas, os ajustes de curva e as figuras do artigo:

    python scripts\analisar.py resultados\medicoes.csv --saida resultados\analise

O script lê `resultados/medicoes.csv` e grava em `resultados/analise/`: `resumo.csv`, `razoes.csv`, `ajustes.csv`, as tabelas em LaTeX (`tab_belem.tex`, `tab_ajustes.tex`) e as figuras em PDF e PNG. O `medicoes.csv` da rodada usada no artigo (26/11/2026) está versionado, com o ambiente em `resultados/medicoes_ambiente.txt`.

## Ambiente dos experimentos do artigo

- **Máquina:** notebook Acer TravelMate P214-55
- **Processador:** Intel Core i7-1355U (13ª geração, 1,70 GHz)
- **Memória:** 16 GB RAM (3200 MT/s)
- **Sistema operacional:** Windows 11, 64 bits
- **Compilador:** g++ 16.2.0 (MSYS2 UCRT64), flags `-std=c++20 -O2 -Wall -Wextra -pedantic -static`, sem `-march=native`
- **Protocolo:** 10 repetições por configuração, mais 1 de aquecimento descartada; origens sorteadas com `mt19937_64` e semente 2026, iguais para as duas filas e as duas variantes

## Estrutura do repositório

| Pasta           | Conteúdo                                                                                                                                                |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/`        | Código-fonte C++: grafo (CSR), heaps, Dijkstra, contadores e programa principal                                                                         |
| `testes/`     | Testes de corretude em C++ e scripts de conferência com a NetworkX                                                                                      |
| `scripts/`    | Scripts Python para gerar instâncias, rodar experimentos, checar e analisar os resultados                                                               |
| `instancias/` | Recortes versionados da malha de Belém                                                                                                                  |
| `dados/`      | Instâncias sintéticas e arquivos gerados pelos scripts (não versionado)                                                                               |
| `resultados/` | Medições da rodada do artigo (`medicoes.csv` e `medicoes_ambiente.txt`) e saídas da análise em `analise/`; novas rodadas não são versionadas |

## Uso de ferramentas de IA

O uso de ferramentas de IA neste trabalho está descrito na Declaração de uso de ferramentas de IA do artigo. Todos os resultados vêm dos programas deste repositório e foram conferidos pelos testes descritos acima.
