"""Confere os resultados do dijkstra.exe contra a NetworkX (21 grafos x 4 configs)."""
import os
import random
import subprocess
import sys

import networkx as nx

RNG      = random.Random(2026)
DIR_NX   = os.path.join("dados", "teste_nx")
CLRS     = os.path.join("testes", "grafos", "clrs.txt")
CSV      = os.path.join(DIR_NX, "medicoes.csv")
DIJKSTRA = os.path.join("build", "dijkstra.exe")
DIST_TMP = os.path.join(DIR_NX, "dist_tmp.txt")

CONFIGS = [
    ("binario",   "todos"),
    ("binario",   "alcance"),
    ("fibonacci", "todos"),
    ("fibonacci", "alcance"),
]

os.makedirs(DIR_NX, exist_ok=True)


def salvar_grafo(caminho, n, arcos):
    with open(caminho, "w") as f:
        f.write(f"{n} {len(arcos)}\n")
        for u, v, w in arcos:
            f.write(f"{u} {v} {w}\n")


def carregar_nx(caminho):
    G = nx.MultiDiGraph()
    with open(caminho) as f:
        n, _ = map(int, f.readline().split())
        G.add_nodes_from(range(n))
        for linha in f:
            partes = linha.split()
            if len(partes) < 3:
                continue
            u, v, w = int(partes[0]), int(partes[1]), float(partes[2])
            G.add_edge(u, v, weight=w)
    return G, n


def ler_dist(caminho):
    dist = {}
    with open(caminho) as f:
        for linha in f:
            partes = linha.split()
            if len(partes) < 2:
                continue
            v = int(partes[0])
            dist[v] = float("inf") if partes[1] == "inf" else float(partes[1])
    return dist


# ------------------------------------------------------------------ gera grafos

graph_infos = []  # (caminho, n)

for i in range(20):
    n = RNG.randint(2, 500)
    m = RNG.randint(0, 5 * n)
    arcos = []
    for _ in range(m):
        u = RNG.randint(0, n - 1)
        v = RNG.randint(0, n - 1)
        if i < 15:                           # inteiros 0-100
            w = RNG.randint(0, 100)
        else:                                # reais com 3 casas decimais
            w = round(RNG.uniform(0, 100), 3)
        arcos.append((u, v, w))
    caminho = os.path.join(DIR_NX, f"g{i}.txt")
    salvar_grafo(caminho, n, arcos)
    graph_infos.append((caminho, n))

# Adiciona clrs.txt (n = 6)
with open(CLRS) as f:
    n_clrs = int(f.readline().split()[0])
graph_infos.append((CLRS, n_clrs))

# ------------------------------------------------------------------ confere

falhas = []

for grafo_path, n in graph_infos:
    orig   = RNG.randint(0, n - 1)
    G, _   = carregar_nx(grafo_path)
    nx_ref = dict(nx.single_source_dijkstra_path_length(G, orig, weight="weight"))

    for fila, variante in CONFIGS:
        cmd = [
            DIJKSTRA,
            "--grafo",       grafo_path,
            "--fila",        fila,
            "--variante",    variante,
            "--origem",      str(orig),
            "--repeticoes",  "1",
            "--aquecimento", "0",
            "--csv",         CSV,
            "--distancias",  DIST_TMP,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Erro ao rodar dijkstra.exe ({grafo_path} {fila}/{variante}):")
            print(res.stderr.strip())
            sys.exit(1)

        dij = ler_dist(DIST_TMP)

        for v in range(n):
            a = dij.get(v, float("inf"))
            if v in nx_ref:
                b = nx_ref[v]
                if abs(a - b) > 1e-9 * max(1.0, abs(b)):
                    falhas.append((grafo_path, fila, variante, v, a, b))
            else:
                if a != float("inf"):
                    falhas.append((grafo_path, fila, variante, v, a, float("inf")))

# ------------------------------------------------------------------ resultado

if falhas:
    for grafo_path, fila, variante, v, obtido, esperado in falhas:
        print(
            f"FALHA: {grafo_path} fila={fila} variante={variante} "
            f"v={v} obtido={obtido} esperado={esperado}"
        )
    sys.exit(1)

print("CONFERENCIA NETWORKX OK (21 grafos x 4 configuracoes)")
sys.exit(0)
