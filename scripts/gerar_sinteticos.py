"""Gera as 24 instancias sinteticas do experimento."""
import sys
import os
import subprocess
import csv

NS = [10000, 20000, 50000, 100000, 200000, 500000]
KS = [2, 4, 8, 16]
SEMENTE = 2026
DIR_SAIDA = os.path.join("dados", "sinteticos")


def main():
    refazer = "--refazer" in sys.argv

    os.makedirs(DIR_SAIDA, exist_ok=True)

    gerador = os.path.join("build", "gerador.exe")
    if not os.path.exists(gerador):
        print(f"Erro: {gerador} nao encontrado. Compile com .\\compilar.ps1", file=sys.stderr)
        sys.exit(1)

    instancias = []

    for n in NS:
        for k in KS:
            m = k * n
            nome = f"sint_n{n}_g{k}.txt"
            arq = os.path.join(DIR_SAIDA, nome)

            # Pula se arquivo valido ja existe (e --refazer nao foi pedido)
            if not refazer and os.path.exists(arq):
                try:
                    with open(arq, "r", newline="") as f:
                        primeira = f.readline().rstrip("\r\n")
                    if primeira == f"{n} {m}":
                        instancias.append((nome, n, m, k, os.path.getsize(arq)))
                        continue
                except Exception:
                    pass  # arquivo corrompido, regera

            cmd = [gerador, "--n", str(n), "--grau", str(k),
                   "--semente", str(SEMENTE), "--saida", arq]
            try:
                ret = subprocess.run(cmd)
            except OSError as e:
                print(f"Erro ao executar gerador: {e}", file=sys.stderr)
                sys.exit(1)

            if ret.returncode != 0:
                print(f"Erro: gerador.exe falhou para n={n} k={k} (codigo {ret.returncode})",
                      file=sys.stderr)
                sys.exit(1)

            instancias.append((nome, n, m, k, os.path.getsize(arq)))

    # Grava resumo
    resumo = os.path.join(DIR_SAIDA, "resumo.csv")
    with open(resumo, "w", newline="\n") as f:
        w = csv.writer(f)
        w.writerow(["instancia", "n", "m", "grau", "semente", "bytes"])
        for nome, n, m, k, tamanho in instancias:
            w.writerow([nome, n, m, k, SEMENTE, tamanho])

    print("SINTETICOS OK (24 instancias)")


if __name__ == "__main__":
    main()
