"""Confere os resultados do dijkstra.exe contra a NetworkX (18 instancias x 4 configs)."""
import os
import random
import subprocess
import sys

import networkx as nx

CONFIGS = [
    ("binario",   "todos"),
    ("binario",   "alcance"),
    ("fibonacci", "todos"),
    ("fibonacci", "alcance"),
]

RAIOS   = [1, 2, 4, 6, 8, 10]
NS_SINT = [10000, 20000, 50000]
KS      = [2, 4, 8, 16]

DIR_BELEM = os.path.join("instancias", "belem")
DIR_SINT  = os.path.join("dados", "sinteticos")
DIR_CONF  = os.path.join("dados", "conferencia")
CSV       = os.path.join(DIR_CONF, "medicoes.csv")
DIST_TMP  = os.path.join(DIR_CONF, "dist.txt")
DIJKSTRA  = os.path.join("build", "dijkstra.exe")


def listar_instancias():
    """Retorna lista de caminhos na ordem da spec: Belem por raio, sinteticas por n e k."""
    inst = []
    for r in RAIOS:
        inst.append(os.path.join(DIR_BELEM, f"belem_r{r}km.txt"))
    for n in NS_SINT:
        for k in KS:
            inst.append(os.path.join(DIR_SINT, f"sint_n{n}_g{k}.txt"))
    return inst


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


def main():
    instancias = listar_instancias()

    faltando = [arq for arq in instancias if not os.path.exists(arq)]
    if faltando:
        for arq in faltando:
            print(f"Erro: instancia nao encontrada: {arq}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(DIJKSTRA):
        print(f"Erro: {DIJKSTRA} nao encontrado. Compile com .\\compilar.ps1",
              file=sys.stderr)
        sys.exit(1)

    os.makedirs(DIR_CONF, exist_ok=True)

    rng = random.Random(2026)
    falhas = []
    total = len(instancias)

    for i, arq in enumerate(instancias, 1):
        G, n = carregar_nx(arq)
        orig = rng.randrange(n)
        print(f"[{i}/{total}] {os.path.basename(arq)} n={n} origem={orig}")

        nx_ref = dict(nx.single_source_dijkstra_path_length(G, orig, weight="weight"))

        for fila, variante in CONFIGS:
            cmd = [
                DIJKSTRA,
                "--grafo",       arq,
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
                print(f"Erro ao rodar dijkstra.exe ({arq} {fila}/{variante}):",
                      file=sys.stderr)
                print(res.stderr.strip(), file=sys.stderr)
                sys.exit(1)

            dij = ler_dist(DIST_TMP)

            for v in range(n):
                a = dij.get(v, float("inf"))
                b = nx_ref.get(v, float("inf"))

                if b == float("inf"):
                    falhas.append((arq, fila, variante, v, a, b))
                    continue

                if abs(a - b) > 1e-9 * max(1.0, abs(b)):
                    falhas.append((arq, fila, variante, v, a, b))

    if falhas:
        for arq, fila, variante, v, obtido, esperado in falhas:
            print(
                f"FALHA: {arq} fila={fila} variante={variante} "
                f"v={v} obtido={obtido} esperado={esperado}"
            )
        sys.exit(1)

    print("CONFERENCIA INSTANCIAS OK (18 instancias x 4 configuracoes)")
    sys.exit(0)


if __name__ == "__main__":
    main()
