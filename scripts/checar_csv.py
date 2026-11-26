"""Checa a integridade de um CSV de medicoes do Dijkstra."""
import csv
import sys
import os

HEADER_ESPERADO = (
    "instancia,n,m,fila,variante,repeticao,origem,tempo_ms,"
    "insert,extract_min,decrease_key,comparacoes,alcancados,"
    "bytes_fila_pico,pico_processo_bytes"
)
CONFIGS_ESPERADAS = {
    ("binario", "todos"), ("binario", "alcance"),
    ("fibonacci", "todos"), ("fibonacci", "alcance"),
}
MAX_FALHAS = 50


def checar(fonte, repeticoes):
    """fonte: iteravel de strings. Retorna lista de descricoes de falhas (ate MAX_FALHAS)."""
    falhas = []
    reader = csv.reader(fonte)

    try:
        cabecalho_row = next(reader)
    except StopIteration:
        return ["arquivo vazio"]

    if ",".join(cabecalho_row) != HEADER_ESPERADO:
        return [f"cabecalho incorreto: {','.join(cabecalho_row)}"]

    # Coleta todas as linhas
    # por_instancia: inst -> lista de dicts
    por_instancia = {}
    num_linhas = 0

    for row in reader:
        if len(row) != 15:
            falhas.append(f"linha {num_linhas + 2}: {len(row)} colunas (esperado 15)")
            num_linhas += 1
            if len(falhas) >= MAX_FALHAS:
                return falhas
            continue

        try:
            d = {
                "inst":           row[0],
                "n":              int(row[1]),
                "m":              int(row[2]),
                "fila":           row[3],
                "variante":       row[4],
                "rep":            int(row[5]),
                "orig":           int(row[6]),
                "tempo_ms":       float(row[7]),
                "insert":         int(row[8]),
                "extract_min":    int(row[9]),
                "decrease_key":   int(row[10]),
                "alcancados":     int(row[12]),
                "bytes_fila_pico":int(row[13]),
            }
        except (ValueError, IndexError) as e:
            falhas.append(f"linha {num_linhas + 2}: parse error: {e}")
            num_linhas += 1
            if len(falhas) >= MAX_FALHAS:
                return falhas
            continue

        por_instancia.setdefault(d["inst"], []).append(d)
        num_linhas += 1

    # Verifica cada instancia
    for inst, rows in por_instancia.items():
        if len(falhas) >= MAX_FALHAS:
            break

        # n e m consistentes
        ns = {r["n"] for r in rows}
        ms = {r["m"] for r in rows}
        if len(ns) > 1:
            falhas.append(f"{inst}: n inconsistente {ns}")
        if len(ms) > 1:
            falhas.append(f"{inst}: m inconsistente {ms}")
        n = rows[0]["n"]
        m = rows[0]["m"]

        # 4 configuracoes presentes
        configs_encontradas = {(r["fila"], r["variante"]) for r in rows}
        for c in sorted(CONFIGS_ESPERADAS - configs_encontradas):
            falhas.append(f"{inst}: configuracao ausente {c[0]}/{c[1]}")

        # Por configuracao: R linhas com repeticao 1..R
        por_config = {}
        for r in rows:
            por_config.setdefault((r["fila"], r["variante"]), []).append(r)

        for (fila, variante), cfg_rows in sorted(por_config.items()):
            reps = sorted(r["rep"] for r in cfg_rows)
            if reps != list(range(1, repeticoes + 1)):
                falhas.append(
                    f"{inst} {fila}/{variante}: repeticoes {reps} != {list(range(1, repeticoes+1))}"
                )
                if len(falhas) >= MAX_FALHAS:
                    break

            for r in cfg_rows:
                if len(falhas) >= MAX_FALHAS:
                    break

                # check 3: origem em [0, n)
                if not (0 <= r["orig"] < n):
                    falhas.append(
                        f"{inst} {fila}/{variante} rep={r['rep']}: "
                        f"origem={r['orig']} fora [0,{n-1}]"
                    )

                # check 4: extract_min == alcancados == n
                if r["extract_min"] != n:
                    falhas.append(
                        f"{inst} {fila}/{variante} rep={r['rep']}: "
                        f"extract_min={r['extract_min']} != n={n}"
                    )
                if r["alcancados"] != n:
                    falhas.append(
                        f"{inst} {fila}/{variante} rep={r['rep']}: "
                        f"alcancados={r['alcancados']} != n={n}"
                    )

                # check 5: decrease_key <= m; insert
                if r["decrease_key"] > m:
                    falhas.append(
                        f"{inst} {fila}/{variante} rep={r['rep']}: "
                        f"decrease_key={r['decrease_key']} > m={m}"
                    )
                if variante == "todos" and r["insert"] != n:
                    falhas.append(
                        f"{inst} {fila}/{variante} rep={r['rep']}: "
                        f"insert={r['insert']} != n={n}"
                    )
                if variante == "alcance" and r["insert"] != r["alcancados"]:
                    falhas.append(
                        f"{inst} {fila}/{variante} rep={r['rep']}: "
                        f"insert={r['insert']} != alcancados={r['alcancados']}"
                    )

                # check 6
                if r["tempo_ms"] <= 0:
                    falhas.append(
                        f"{inst} {fila}/{variante} rep={r['rep']}: tempo_ms={r['tempo_ms']} <= 0"
                    )
                if r["bytes_fila_pico"] <= 0:
                    falhas.append(
                        f"{inst} {fila}/{variante} rep={r['rep']}: "
                        f"bytes_fila_pico={r['bytes_fila_pico']} <= 0"
                    )

        if len(falhas) >= MAX_FALHAS:
            break

        # check 3: origem igual entre configuracoes para mesma (inst, rep)
        for rep in range(1, repeticoes + 1):
            origens_rep = {
                (r["fila"], r["variante"]): r["orig"]
                for r in rows if r["rep"] == rep
            }
            vals = set(origens_rep.values())
            if len(vals) > 1:
                falhas.append(
                    f"{inst} rep={rep}: origem diferente entre configuracoes: {origens_rep}"
                )
            if len(falhas) >= MAX_FALHAS:
                break

    return falhas[:MAX_FALHAS]


# ------------------------------------------------------------------ autoteste

HEADER = HEADER_ESPERADO
CONFIGS_AUTO = [
    ("binario", "todos"), ("binario", "alcance"),
    ("fibonacci", "todos"), ("fibonacci", "alcance"),
]
REPS_AUTO = 3
INST_AUTO = [
    ("inst_a", 10, 20, [0, 1, 2]),
    ("inst_b", 15, 30, [3, 4, 5]),
]


def construir_csv_auto(defeito=None):
    linhas = [HEADER]
    for inst, n, m, origens in INST_AUTO:
        for fila, variante in CONFIGS_AUTO:
            for idx, rep in enumerate(range(1, REPS_AUTO + 1)):
                orig = origens[idx]
                alcancados = n
                insert = n

                if defeito == 1:
                    # defeito: falta repeticao 2 de (inst_a, binario, todos)
                    if inst == "inst_a" and fila == "binario" and variante == "todos" and rep == 2:
                        continue

                if defeito == 2:
                    # defeito: alcancados != n em (inst_a, binario, todos, rep=1)
                    if inst == "inst_a" and fila == "binario" and variante == "todos" and rep == 1:
                        alcancados = n - 1

                if defeito == 3:
                    # defeito: origem diferente em (inst_a, fibonacci, todos, rep=1)
                    if inst == "inst_a" and fila == "fibonacci" and variante == "todos" and rep == 1:
                        orig = (origens[0] + 5) % n

                linhas.append(
                    f"{inst},{n},{m},{fila},{variante},{rep},{orig},"
                    f"1.5,{insert},{n},5,0,{alcancados},800,1000"
                )
    return "\n".join(linhas) + "\n"


def autoteste():
    passou = True

    # CSV valido deve passar
    linhas_ok = construir_csv_auto().splitlines()
    falhas_ok = checar(linhas_ok, REPS_AUTO)
    if falhas_ok:
        print(f"AUTOTESTE FALHOU: CSV valido nao passou: {falhas_ok}")
        passou = False

    # 3 defeitos devem ser detectados
    for num_defeito in (1, 2, 3):
        linhas_def = construir_csv_auto(defeito=num_defeito).splitlines()
        falhas_def = checar(linhas_def, REPS_AUTO)
        if not falhas_def:
            print(f"AUTOTESTE FALHOU: defeito {num_defeito} nao foi detectado")
            passou = False

    if not passou:
        sys.exit(1)

    print("AUTOTESTE OK (3 defeitos detectados)")
    sys.exit(0)


# ------------------------------------------------------------------ main

def main():
    if "--autoteste" in sys.argv:
        autoteste()

    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print(f"Uso: {sys.argv[0]} <csv> [--repeticoes N]", file=sys.stderr)
        sys.exit(1)

    arq_csv = args[0]
    repeticoes = 10
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--repeticoes" and i < len(sys.argv):
            repeticoes = int(sys.argv[i])

    if not os.path.exists(arq_csv):
        print(f"Erro: arquivo nao encontrado: {arq_csv}", file=sys.stderr)
        sys.exit(1)

    with open(arq_csv, newline="") as f:
        falhas = checar(f, repeticoes)

    if falhas:
        for desc in falhas:
            print(f"FALHA: {desc}")
        sys.exit(1)

    # Contar linhas e instancias para o relatorio
    with open(arq_csv, newline="") as f:
        reader = csv.reader(f)
        next(reader)  # pula cabecalho
        instancias_vistas = set()
        num_linhas = 0
        for row in reader:
            if row:
                instancias_vistas.add(row[0])
                num_linhas += 1

    print(f"CSV OK ({num_linhas} linhas, {len(instancias_vistas)} instancias)")
    sys.exit(0)


if __name__ == "__main__":
    main()
