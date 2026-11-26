"""Roda os experimentos do Dijkstra em todas as instancias e grava um CSV."""
import filecmp
import os
import platform
import subprocess
import sys
import time

RAIOS    = [1, 2, 4, 6, 8, 10]
KS       = [2, 4, 8, 16]
NS_SINT  = [10000, 20000, 50000, 100000, 200000, 500000]

DIR_BELEM = os.path.join("instancias", "belem")
DIR_SINT  = os.path.join("dados", "sinteticos")
DIR_DIST  = os.path.join("dados", "dist")
DIJKSTRA  = os.path.join("build", "dijkstra.exe")

CONFIGS = [
    ("binario",   "todos"),
    ("binario",   "alcance"),
    ("fibonacci", "todos"),
    ("fibonacci", "alcance"),
]


def parse_args():
    saida      = os.path.join("resultados", "medicoes.csv")
    filtros    = []
    repeticoes = 10
    semente    = 2026
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--saida" and i + 1 < len(sys.argv):
            saida = sys.argv[i + 1]; i += 2
        elif arg == "--so" and i + 1 < len(sys.argv):
            filtros.append(sys.argv[i + 1]); i += 2
        elif arg == "--repeticoes" and i + 1 < len(sys.argv):
            repeticoes = int(sys.argv[i + 1]); i += 2
        elif arg == "--semente" and i + 1 < len(sys.argv):
            semente = int(sys.argv[i + 1]); i += 2
        else:
            i += 1
    return saida, filtros, repeticoes, semente


def listar_todas():
    """Belem por raio crescente, sinteticas por k e depois n crescentes."""
    inst = []
    for r in RAIOS:
        inst.append(os.path.join(DIR_BELEM, f"belem_r{r}km.txt"))
    for k in KS:
        for n in NS_SINT:
            inst.append(os.path.join(DIR_SINT, f"sint_n{n}_g{k}.txt"))
    return inst


def ler_cabecalho(arq):
    with open(arq) as f:
        partes = f.readline().split()
        return int(partes[0]), int(partes[1])


def gravar_ambiente(arq_ambiente, repeticoes, semente):
    import datetime
    linhas = [
        f"data_hora: {datetime.datetime.now().isoformat()}",
        f"plataforma: {platform.platform()}",
        f"processador: {platform.processor()}",
        f"python: {sys.version}",
    ]
    try:
        res = subprocess.run(["g++", "--version"], capture_output=True, text=True)
        linhas.append(f"g++: {res.stdout.splitlines()[0] if res.stdout else 'n/a'}")
    except Exception:
        linhas.append("g++: n/a")
    try:
        import networkx as nx
        linhas.append(f"networkx: {nx.__version__}")
    except ImportError:
        linhas.append("networkx: n/a")
    try:
        import osmnx as ox
        linhas.append(f"osmnx: {ox.__version__}")
    except ImportError:
        linhas.append("osmnx: n/a")
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"],
                             capture_output=True, text=True)
        git_hash = res.stdout.strip() if res.returncode == 0 else "sem git"
    except Exception:
        git_hash = "sem git"
    linhas.append(f"git_commit: {git_hash}")
    linhas.append(f"comando: {' '.join(sys.argv)}")
    with open(arq_ambiente, "w", newline="\n") as f:
        f.write("\n".join(linhas) + "\n")


def main():
    saida, filtros, repeticoes, semente = parse_args()

    if os.path.exists(saida):
        print(f"Erro: {saida} ja existe; apague ou use outra --saida", file=sys.stderr)
        sys.exit(1)

    todas = listar_todas()

    # Verificar que as pastas-fonte nao estao vazias
    belem_ok = any(os.path.exists(a) for a in todas if "belem" in a)
    sint_ok  = any(os.path.exists(a) for a in todas if "sint"  in a)
    if not belem_ok:
        print("Erro: pasta instancias/belem/ vazia ou inexistente", file=sys.stderr)
        sys.exit(1)
    if not sint_ok:
        print("Erro: pasta dados/sinteticos/ vazia ou inexistente", file=sys.stderr)
        sys.exit(1)

    # Aplicar filtros
    if filtros:
        instancias = [a for a in todas
                      if any(f in os.path.basename(a) for f in filtros)]
    else:
        instancias = todas

    faltando = [a for a in instancias if not os.path.exists(a)]
    if faltando:
        for a in faltando:
            print(f"Erro: instancia nao encontrada: {a}", file=sys.stderr)
        sys.exit(1)

    if not instancias:
        print("Erro: nenhuma instancia selecionada pelos filtros", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(DIJKSTRA):
        print(f"Erro: {DIJKSTRA} nao encontrado. Compile com .\\compilar.ps1",
              file=sys.stderr)
        sys.exit(1)

    # Criar pastas de saida
    saida_dir = os.path.dirname(saida)
    if saida_dir:
        os.makedirs(saida_dir, exist_ok=True)
    os.makedirs(DIR_DIST, exist_ok=True)

    # Arquivo de ambiente (antes de medir)
    base_sem_ext  = os.path.splitext(saida)[0]
    arq_ambiente  = base_sem_ext + "_ambiente.txt"
    gravar_ambiente(arq_ambiente, repeticoes, semente)

    N = len(instancias)

    for i, arq in enumerate(instancias, 1):
        n, m = ler_cabecalho(arq)
        nome_base = os.path.splitext(os.path.basename(arq))[0]
        t0 = time.perf_counter()

        arqs_dist = []
        for fila, variante in CONFIGS:
            arq_dist = os.path.join(DIR_DIST, f"{nome_base}_{fila}_{variante}.txt")
            arqs_dist.append(arq_dist)
            cmd = [
                DIJKSTRA,
                "--grafo",       arq,
                "--fila",        fila,
                "--variante",    variante,
                "--repeticoes",  str(repeticoes),
                "--aquecimento", "1",
                "--semente",     str(semente),
                "--csv",         saida,
                "--distancias",  arq_dist,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"Erro: dijkstra.exe falhou para {nome_base} {fila}/{variante}",
                      file=sys.stderr)
                print(res.stderr.strip(), file=sys.stderr)
                sys.exit(1)

        # Verificar que os 4 arquivos de distancias sao identicos
        for j in range(1, len(arqs_dist)):
            if not filecmp.cmp(arqs_dist[0], arqs_dist[j], shallow=False):
                print(f"Erro: distancias divergem em {nome_base}: "
                      f"{arqs_dist[0]} != {arqs_dist[j]}", file=sys.stderr)
                sys.exit(1)

        t1 = time.perf_counter()
        print(f"[{i}/{N}] {nome_base} (n={n}, m={m}) em {t1 - t0:.1f} s")

    print(f"EXPERIMENTOS OK ({N} instancias x 4 configuracoes x {repeticoes} repeticoes) -> {saida}")


if __name__ == "__main__":
    main()
