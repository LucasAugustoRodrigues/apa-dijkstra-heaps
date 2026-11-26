"""Extrai os 6 recortes da malha viaria de Belem a partir do OpenStreetMap."""
import sys
import os
import csv
import datetime
import networkx as nx
import osmnx as ox

RAIOS = [1, 2, 4, 6, 8, 10]
QUERY_CENTRO = "Praca da Republica, Belem, Para, Brasil"
QUERY_GEOCODE = "Praça da República, Belém, Pará, Brasil"
DIR_INSTANCIAS = os.path.join("instancias", "belem")
DIR_DADOS = os.path.join("dados", "belem")
DIR_CACHE = os.path.join("dados", "cache_osmnx")


def parse_args():
    centro_arg = None
    baixar_de_novo = False
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--baixar-de-novo":
            baixar_de_novo = True
        elif arg == "--centro" and i + 1 < len(sys.argv):
            centro_arg = sys.argv[i + 1]
            i += 1
        i += 1
    return centro_arg, baixar_de_novo


def obter_centro(centro_arg, baixar_de_novo, arq_centro):
    if centro_arg:
        partes = centro_arg.split(",")
        return float(partes[0]), float(partes[1])

    if not baixar_de_novo and os.path.exists(arq_centro):
        with open(arq_centro, "r") as f:
            linha = f.readline().strip()
        lat_c, lon_c = map(float, linha.split(","))
        print(f"Centro carregado de {arq_centro}: {lat_c:.7f},{lon_c:.7f}")
        return lat_c, lon_c

    print("Geocodificando centro...")
    lat_c, lon_c = ox.geocode(QUERY_GEOCODE)
    os.makedirs(os.path.dirname(arq_centro), exist_ok=True)
    with open(arq_centro, "w", newline="\n") as f:
        f.write(f"{lat_c:.7f},{lon_c:.7f}\n")
    print(f"Centro salvo em {arq_centro}: {lat_c:.7f},{lon_c:.7f}")
    return lat_c, lon_c


def obter_base(baixar_de_novo, lat_c, lon_c, arq_base):
    if not baixar_de_novo and os.path.exists(arq_base):
        print(f"Carregando base de {arq_base}...")
        return ox.load_graphml(arq_base)

    print("Baixando malha de Belem (pode demorar alguns minutos)...")
    G = ox.graph_from_point(
        (lat_c, lon_c), dist=10000, dist_type="bbox",
        network_type="drive", simplify=True, retain_all=True
    )
    os.makedirs(os.path.dirname(arq_base), exist_ok=True)
    ox.save_graphml(G, arq_base)
    print(f"Base salva em {arq_base} ({G.number_of_nodes()} nos, {G.number_of_edges()} arcos)")
    return G


def extrair_recorte(G_base, lat_c, lon_c, raio_km):
    dist_max = 1000.0 * raio_km

    nos_raio = [
        v for v, nd in G_base.nodes(data=True)
        if ox.distance.great_circle(lat_c, lon_c, float(nd["y"]), float(nd["x"])) <= dist_max
    ]

    sub = G_base.subgraph(nos_raio)
    sccs = list(nx.strongly_connected_components(sub))
    if not sccs:
        print(f"Erro: nenhuma SCC encontrada para r={raio_km}km", file=sys.stderr)
        sys.exit(1)
    maior_scc = max(sccs, key=len)
    G_scc = sub.subgraph(maior_scc)

    # Arcos sem lacos; entre paralelos, fica o mais curto
    arcos_min = {}
    for u, v, _key, ed in G_scc.edges(data=True, keys=True):
        if u == v:
            continue
        peso = float(ed["length"])
        if (u, v) not in arcos_min or peso < arcos_min[(u, v)]:
            arcos_min[(u, v)] = peso

    # Renumerar vertices em ordem crescente do id OSM
    nos_sorted = sorted(maior_scc)
    mapa_id = {osm_id: idx for idx, osm_id in enumerate(nos_sorted)}
    n = len(nos_sorted)

    # Arcos em ordem crescente de (u_novo, v_novo)
    arcos_sorted = sorted(
        ((mapa_id[u], mapa_id[v], w) for (u, v), w in arcos_min.items()),
        key=lambda a: (a[0], a[1])
    )
    m = len(arcos_sorted)

    return n, m, arcos_sorted


def gravar_recorte(arq_saida, n, m, arcos):
    with open(arq_saida, "w", newline="\n") as f:
        f.write(f"{n} {m}\n")
        for u, v, w in arcos:
            f.write(f"{u} {v} {repr(w)}\n")


def main():
    centro_arg, baixar_de_novo = parse_args()

    ox.settings.cache_folder = DIR_CACHE
    ox.settings.use_cache = True

    os.makedirs(DIR_INSTANCIAS, exist_ok=True)
    os.makedirs(DIR_DADOS, exist_ok=True)
    os.makedirs(DIR_CACHE, exist_ok=True)

    arq_centro = os.path.join(DIR_DADOS, "centro.txt")
    arq_base = os.path.join(DIR_DADOS, "belem_base.graphml")

    try:
        lat_c, lon_c = obter_centro(centro_arg, baixar_de_novo, arq_centro)
        G_base = obter_base(baixar_de_novo, lat_c, lon_c, arq_base)
    except Exception as e:
        print(f"Erro ao obter dados do OSM: {e}", file=sys.stderr)
        sys.exit(1)

    mtime = os.path.getmtime(arq_base)
    data_base = datetime.date.fromtimestamp(mtime).strftime("%Y-%m-%d")
    osmnx_versao = ox.__version__

    linhas_resumo = []

    for r in RAIOS:
        print(f"Processando r={r}km...")
        n, m, arcos = extrair_recorte(G_base, lat_c, lon_c, r)
        nome = f"belem_r{r}km.txt"
        arq_saida = os.path.join(DIR_INSTANCIAS, nome)
        gravar_recorte(arq_saida, n, m, arcos)
        m_por_n = m / n
        print(f"  r={r}km: n={n} m={m} m/n={m_por_n:.4f} -> {arq_saida}")
        linhas_resumo.append((nome, r, n, m, m_por_n))

    # Verificar que n e m crescem com o raio
    for i in range(1, len(linhas_resumo)):
        _, r_ant, n_ant, m_ant, _ = linhas_resumo[i - 1]
        _, r_cur, n_cur, m_cur, _ = linhas_resumo[i]
        if n_cur <= n_ant or m_cur <= m_ant:
            print(f"Aviso: n ou m nao cresceu do raio {r_ant}km para {r_cur}km", file=sys.stderr)

    # Gravar resumo.csv
    resumo_arq = os.path.join(DIR_INSTANCIAS, "resumo.csv")
    cabecalho = ["instancia", "raio_km", "n", "m", "m_por_n",
                 "centro_lat", "centro_lon", "data_base", "osmnx_versao"]
    with open(resumo_arq, "w", newline="\n") as f:
        w = csv.writer(f)
        w.writerow(cabecalho)
        for nome, r, n, m, m_por_n in linhas_resumo:
            w.writerow([nome, r, n, m, f"{m_por_n:.4f}",
                        f"{lat_c:.7f}", f"{lon_c:.7f}", data_base, osmnx_versao])

    # Imprimir tabela
    print(f"\n{'instancia':<22} {'raio_km':>7} {'n':>8} {'m':>9} {'m/n':>8}")
    for nome, r, n, m, m_por_n in linhas_resumo:
        print(f"{nome:<22} {r:>7} {n:>8} {m:>9} {m_por_n:>8.4f}")

    print("\nBELEM OK (6 recortes)")


if __name__ == "__main__":
    main()
