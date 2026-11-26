"""Analise do CSV dos experimentos: tabelas, ajuste das curvas e graficos.

Uso:
    python analisar.py <medicoes.csv> --saida <pasta> [--marca "TEXTO"]

Le o CSV do rodar_experimentos.py (15 colunas) e grava na pasta de saida:
  resumo.csv        media e desvio por instancia, fila e variante
  razoes.csv        Fibonacci / binario por instancia e variante
  ajustes.csv       c1 (n+m)log2 n e c2 (m + n log2 n) ajustados ao tempo,
                    com R2 e o expoente empirico (inclinacao log-log)
  tab_*.tex         tabelas prontas para o LaTeX (virgula decimal, booktabs)
  fig_*.pdf/.png    graficos (PDF para o artigo, PNG para conferir)
Nenhum numero e arredondado antes das contas; o arredondamento so acontece
na hora de escrever as tabelas.
"""
import argparse
import math
import os
import re
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CABECALHO = ("instancia,n,m,fila,variante,repeticao,origem,tempo_ms,insert,"
             "extract_min,decrease_key,comparacoes,alcancados,bytes_fila_pico,"
             "pico_processo_bytes").split(",")

# Cores (paleta validada: azul e laranja passam em daltonismo; o laranja
# fica abaixo de 3:1 no fundo branco, por isso toda serie tem rotulo direto
# ou legenda, e marcador e tracejado diferentes)
COR = {"binario": "#257de0", "fibonacci": "#f47230"}
NOME_FILA = {"binario": "Heap binário", "fibonacci": "Heap de Fibonacci"}
NOME_VAR = {"todos": "todos no início", "alcance": "ao alcançar"}
TRACO = {"todos": "-", "alcance": "--"}
MARCA = {("binario", "todos"): "o", ("binario", "alcance"): "s",
         ("fibonacci", "todos"): "^", ("fibonacci", "alcance"): "D"}
TINTA = "#333333"
TINTA2 = "#777777"
GRADE = "#e6e6e6"


def estilo():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9,
        "axes.edgecolor": TINTA2, "axes.labelcolor": TINTA,
        "xtick.color": TINTA2, "ytick.color": TINTA2,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRADE, "grid.linewidth": 0.6,
        "legend.frameon": False, "lines.linewidth": 2, "lines.markersize": 5,
        "savefig.bbox": "tight", "savefig.dpi": 200,
    })


def virgula(x, casas=2):
    """Numero com virgula decimal e ponto de milhar (padrao do artigo)."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "--"
    s = f"{x:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def familia(inst):
    if inst.startswith("belem_"):
        return "belem"
    if inst.startswith("sint_"):
        return "sint"
    return "outra"


def grau(inst):
    m = re.search(r"_g(\d+)$", inst)
    return int(m.group(1)) if m else np.nan


def raio(inst):
    m = re.search(r"_r(\d+)km$", inst)
    return int(m.group(1)) if m else np.nan


def ler(caminho):
    df = pd.read_csv(caminho)
    if list(df.columns) != CABECALHO:
        sys.exit(f"cabecalho inesperado em {caminho}: {list(df.columns)}")
    df["familia"] = df["instancia"].map(familia)
    df["grau"] = df["instancia"].map(grau)
    df["raio_km"] = df["instancia"].map(raio)
    return df


def resumir(df):
    g = df.groupby(["familia", "instancia", "grau", "raio_km", "n", "m",
                    "fila", "variante"], dropna=False)
    r = g.agg(reps=("tempo_ms", "size"),
              tempo_med=("tempo_ms", "mean"), tempo_dp=("tempo_ms", "std"),
              comparacoes_med=("comparacoes", "mean"),
              insert_med=("insert", "mean"),
              extract_min_med=("extract_min", "mean"),
              dk_med=("decrease_key", "mean"), dk_dp=("decrease_key", "std"),
              bytes_fila_pico_med=("bytes_fila_pico", "mean"),
              pico_processo_med=("pico_processo_bytes", "mean")).reset_index()
    r["m_por_n"] = r["m"] / r["n"]
    r["tempo_cv"] = r["tempo_dp"] / r["tempo_med"]
    r["dk_por_m"] = r["dk_med"] / r["m"]
    r["log2n"] = np.log2(r["n"])
    r["f1"] = (r["n"] + r["m"]) * r["log2n"]       # (n+m) log n
    r["f2"] = r["m"] + r["n"] * r["log2n"]         # m + n log n
    r["ns_por_f1"] = r["tempo_med"] * 1e6 / r["f1"]
    r["ns_por_f2"] = r["tempo_med"] * 1e6 / r["f2"]
    return r.sort_values(["familia", "grau", "raio_km", "n", "fila", "variante"])


def razoes(r):
    chave = ["familia", "instancia", "grau", "raio_km", "n", "m", "variante"]
    b = r[r.fila == "binario"].set_index(chave)
    f = r[r.fila == "fibonacci"].set_index(chave)
    out = pd.DataFrame({
        "tempo_fib_sobre_bin": f["tempo_med"] / b["tempo_med"],
        "comparacoes_fib_sobre_bin": f["comparacoes_med"] / b["comparacoes_med"],
        "bytes_fib_sobre_bin": f["bytes_fila_pico_med"] / b["bytes_fila_pico_med"],
        "dk_por_m_bin": b["dk_por_m"], "dk_por_m_fib": f["dk_por_m"],
    }).reset_index()
    return out.sort_values(["familia", "grau", "raio_km", "n", "variante"])


def ajustar(r):
    """Minimos quadrados pela origem: t = c * f. R2 em relacao a media.
    Tambem o expoente empirico: inclinacao de log t contra log n."""
    linhas = []
    grupos = [("belem", None)] + [("sint", k) for k in sorted(r["grau"].dropna().unique())]
    for fam, k in grupos:
        sub = r[r.familia == fam] if k is None else r[(r.familia == fam) & (r.grau == k)]
        if sub.empty:
            continue
        for (fila, var), s in sub.groupby(["fila", "variante"]):
            s = s.sort_values("n")
            t = s["tempo_med"].to_numpy()
            item = {"grupo": fam if k is None else f"sint_g{int(k)}",
                    "fila": fila, "variante": var, "pontos": len(s)}
            for nome in ("f1", "f2"):
                x = s[nome].to_numpy()
                c = float(np.dot(x, t) / np.dot(x, x))
                pred = c * x
                ss_res = float(np.sum((t - pred) ** 2))
                ss_tot = float(np.sum((t - t.mean()) ** 2))
                item[f"c_{nome}_ns"] = c * 1e6
                item[f"r2_{nome}"] = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
                item[f"erro_rel_max_{nome}"] = float(np.max(np.abs(t - pred) / t))
            if len(s) >= 2:
                a, _ = np.polyfit(np.log(s["n"]), np.log(t), 1)
                item["expoente_n"] = float(a)
            linhas.append(item)
    return pd.DataFrame(linhas)


# ------------------------------------------------------------------ graficos

def marca_dagua(fig, marca):
    if marca:
        fig.text(0.5, 0.5, marca, fontsize=26, color="#cc0000", alpha=0.25,
                 ha="center", va="center", rotation=20)


def limpar_menores(fig):
    """Sem rotulo nas marcas menores dos eixos log (eles se sobrepoem)."""
    from matplotlib.ticker import NullFormatter
    for ax in fig.axes:
        if ax.get_xscale() == "log":
            ax.xaxis.set_minor_formatter(NullFormatter())
        if ax.get_yscale() == "log":
            ax.yaxis.set_minor_formatter(NullFormatter())


def salvar(fig, pasta, nome, marca):
    limpar_menores(fig)
    marca_dagua(fig, marca)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(pasta, f"{nome}.{ext}"))
    plt.close(fig)


def series_tempo(ax, sub, xcol="n", rotular=True):
    for fila in ("binario", "fibonacci"):
        for var in ("todos", "alcance"):
            s = sub[(sub.fila == fila) & (sub.variante == var)].sort_values(xcol)
            if s.empty:
                continue
            ax.errorbar(s[xcol], s["tempo_med"], yerr=s["tempo_dp"],
                        color=COR[fila], ls=TRACO[var], marker=MARCA[(fila, var)],
                        capsize=2, elinewidth=0.8,
                        label=f"{NOME_FILA[fila]}, {NOME_VAR[var]}")


def fig_tempo_belem(r, pasta, marca):
    sub = r[r.familia == "belem"]
    if sub.empty:
        return
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    series_tempo(ax, sub)
    ax.set_xscale("log")
    ax.set_yscale("log")
    for i, (_, s) in enumerate(sub[(sub.fila == "binario") & (sub.variante == "todos")]
                               .sort_values("n").iterrows()):
        ax.annotate(f"{int(s.raio_km)} km", (s.n, 0.03 + 0.05 * (i % 2)),
                    xycoords=("data", "axes fraction"),
                    ha="center", fontsize=7, color=TINTA2)
    ax.set_xlabel("n (vértices)")
    ax.set_ylabel("tempo do Dijkstra (ms)")
    ax.set_title("Malha de Belém: tempo × n (média ± desvio, 10 origens)",
                 fontsize=9, color=TINTA, loc="left")
    ax.legend(fontsize=7.5, loc="upper left")
    salvar(fig, pasta, "fig_tempo_belem", marca)


def fig_tempo_sint(r, pasta, marca):
    sub = r[r.familia == "sint"]
    if sub.empty:
        return
    graus = sorted(sub["grau"].dropna().unique())
    fig, axs = plt.subplots(1, len(graus), figsize=(2.3 * len(graus), 2.9),
                            sharey=True)
    axs = np.atleast_1d(axs)
    for ax, k in zip(axs, graus):
        series_tempo(ax, sub[sub.grau == k])
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(f"m/n = {int(k)}", fontsize=9, color=TINTA, loc="left")
        ax.set_xlabel("n")
    axs[0].set_ylabel("tempo (ms)")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, ncol=4, fontsize=7.5, loc="upper center",
               bbox_to_anchor=(0.5, 1.08))
    salvar(fig, pasta, "fig_tempo_sinteticos", marca)


def fig_ajuste(r, aj, pasta, marca):
    """Tempo medido dividido pelo modelo ajustado (c * f). Se o modelo
    explica o crescimento, os pontos ficam em torno de 1 e sem tendencia;
    uma subida com n mostra o que o modelo nao captura (ex.: cache)."""
    grupos = [("belem", None, "Belém", "belem")] + [
        ("sint", k, f"sintético m/n = {int(k)}", f"sint_g{int(k)}")
        for k in sorted(r["grau"].dropna().unique())]
    grupos = [g for g in grupos if not aj[aj.grupo == g[3]].empty]
    fig, axs = plt.subplots(2, len(grupos), figsize=(2.3 * len(grupos), 4.6),
                            sharey=True, squeeze=False)
    for j, (fam, k, titulo, chave) in enumerate(grupos):
        sub = r[r.familia == fam] if k is None else r[(r.familia == fam) & (r.grau == k)]
        for i, (col, nome) in enumerate((("f1", "c1 (n+m) log n"),
                                         ("f2", "c2 (m + n log n)"))):
            ax = axs[i, j]
            for fila in ("binario", "fibonacci"):
                for var in ("todos", "alcance"):
                    s = sub[(sub.fila == fila) & (sub.variante == var)].sort_values("n")
                    a = aj[(aj.grupo == chave) & (aj.fila == fila) & (aj.variante == var)]
                    if s.empty or a.empty:
                        continue
                    c = a[f"c_{col}_ns"].iloc[0] / 1e6
                    ax.plot(s["n"], s["tempo_med"] / (c * s[col]), color=COR[fila],
                            ls=TRACO[var], marker=MARCA[(fila, var)],
                            label=f"{NOME_FILA[fila]}, {NOME_VAR[var]}")
            ax.axhline(1, color=TINTA2, lw=0.8)
            ax.set_xscale("log")
            if i == 0:
                ax.set_title(titulo, fontsize=9, color=TINTA, loc="left")
            if j == 0:
                ax.set_ylabel(f"medido / ajustado\n{nome}")
            if i == 1:
                ax.set_xlabel("n")
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, l, ncol=4, fontsize=7.5, loc="upper center",
               bbox_to_anchor=(0.5, 1.05))
    salvar(fig, pasta, "fig_ajuste_razao", marca)


def espalhar(valores, gap):
    """Afasta rotulos que ficariam colados (posicoes em unidades do eixo)."""
    ordem = sorted(range(len(valores)), key=lambda i: valores[i])
    pos = list(valores)
    for a, b in zip(ordem, ordem[1:]):
        if pos[b] - pos[a] < gap:
            pos[b] = pos[a] + gap
    return pos


RAMPA_GRAU = {2: "#84b9f3", 4: "#338ced", 8: "#1b64be", 16: "#0e3d7e"}


def fig_dk(r, pasta, marca):
    """DecreaseKey / m (heap binario; o Fibonacci da quase o mesmo, ver razoes.csv)."""
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
    for ax, var in zip(axs, ("todos", "alcance")):
        fins = []
        sub = r[(r.familia == "belem") & (r.fila == "binario") & (r.variante == var)]
        if not sub.empty:
            s = sub.sort_values("n")
            ax.plot(s["n"], s["dk_por_m"], color=TINTA, marker="o", label="Belém")
            fins.append((s["n"].iloc[-1], s["dk_por_m"].iloc[-1], "Belém"))
        sub = r[(r.familia == "sint") & (r.fila == "binario") & (r.variante == var)]
        for k, s in sub.groupby("grau"):
            s = s.sort_values("n")
            ax.plot(s["n"], s["dk_por_m"], color=RAMPA_GRAU.get(int(k), COR["binario"]),
                    marker=".", label=f"sintético m/n = {int(k)}")
            fins.append((s["n"].iloc[-1], s["dk_por_m"].iloc[-1], f"m/n={int(k)}"))
        ax.set_xscale("log")
        ax.set_title(f"variante {NOME_VAR[var]}", fontsize=9, color=TINTA, loc="left")
        ax.set_xlabel("n")
        ax.set_ylim(bottom=0)
    axs[0].set_ylabel("DecreaseKey / m")
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, ncol=5, fontsize=7.5, loc="upper center",
               bbox_to_anchor=(0.5, 1.07))
    salvar(fig, pasta, "fig_decreasekey_por_m", marca)


def fig_memoria(r, pasta, marca):
    fig, axs = plt.subplots(1, 2, figsize=(7, 2.9), sharey=True)
    for ax, var in zip(axs, ("todos", "alcance")):
        for fila in ("binario", "fibonacci"):
            for fam, mk in (("belem", "o"), ("sint", ".")):
                s = r[(r.familia == fam) & (r.fila == fila) & (r.variante == var)]
                if s.empty:
                    continue
                s = s.groupby("n", as_index=False)["bytes_fila_pico_med"].max()
                ax.plot(s["n"], s["bytes_fila_pico_med"] / 2**20, color=COR[fila],
                        ls="-" if fam == "belem" else ":", marker=mk,
                        label=f"{NOME_FILA[fila]} ({'Belém' if fam == 'belem' else 'sintéticos'})")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(f"variante {NOME_VAR[var]}", fontsize=9, color=TINTA, loc="left")
        ax.set_xlabel("n")
    axs[0].set_ylabel("pico de bytes da fila (MiB)")
    axs[0].legend(fontsize=7, loc="upper left")
    salvar(fig, pasta, "fig_memoria_fila", marca)


# ------------------------------------------------------------------ tabelas

def tab_belem(r, rz, pasta):
    b = r[r.familia == "belem"]
    if b.empty:
        return
    linhas = []
    for inst, s in b.groupby("instancia", sort=False):
        s0 = s.iloc[0]
        def t(f, v):
            x = s[(s.fila == f) & (s.variante == v)]
            return f"{virgula(x.tempo_med.iloc[0])} $\\pm$ {virgula(x.tempo_dp.iloc[0])}"
        rr = rz[(rz.instancia == inst)]
        linhas.append(
            f"{int(s0.raio_km)} & {virgula(s0.n, 0)} & {virgula(s0.m, 0)} & "
            f"{virgula(s0.m_por_n)} & {t('binario', 'alcance')} & {t('fibonacci', 'alcance')} & "
            f"{virgula(rr[rr.variante == 'alcance'].tempo_fib_sobre_bin.iloc[0])} & "
            f"{virgula(rr[rr.variante == 'todos'].tempo_fib_sobre_bin.iloc[0])} & "
            f"{virgula(rr[rr.variante == 'alcance'].dk_por_m_bin.iloc[0], 3)} \\\\")
    cab = ("\\begin{tabular}{rrrrrrrrr}\n\\toprule\n"
           "Raio (km) & $n$ & $m$ & $m/n$ & Binário (ms) & Fibonacci (ms) & "
           "F/B alc. & F/B todos & DK$/m$ \\\\\n\\midrule\n")
    with open(os.path.join(pasta, "tab_belem.tex"), "w", encoding="utf-8") as f:
        f.write(cab + "\n".join(linhas) + "\n\\bottomrule\n\\end{tabular}\n")


def tab_ajustes(aj, pasta):
    if aj.empty:
        return
    linhas = []
    for _, a in aj.iterrows():
        linhas.append(
            f"{a.grupo.replace('_', ' ')} & {NOME_FILA[a.fila]} & {NOME_VAR[a.variante]} & "
            f"{virgula(a.c_f1_ns, 3)} & {virgula(a.r2_f1, 3)} & "
            f"{virgula(a.c_f2_ns, 3)} & {virgula(a.r2_f2, 3)} & "
            f"{virgula(a.get('expoente_n', float('nan')), 2)} \\\\")
    cab = ("\\begin{tabular}{lllrrrrr}\n\\toprule\n"
           "Instâncias & Fila & Variante & $c_1$ (ns) & $R^2$ & $c_2$ (ns) & $R^2$ & "
           "expoente \\\\\n\\midrule\n")
    with open(os.path.join(pasta, "tab_ajustes.tex"), "w", encoding="utf-8") as f:
        f.write(cab + "\n".join(linhas) + "\n\\bottomrule\n\\end{tabular}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--marca", default="")
    a = ap.parse_args()
    os.makedirs(a.saida, exist_ok=True)
    estilo()
    df = ler(a.csv)
    r = resumir(df)
    rz = razoes(r)
    aj = ajustar(r)
    r.to_csv(os.path.join(a.saida, "resumo.csv"), index=False)
    rz.to_csv(os.path.join(a.saida, "razoes.csv"), index=False)
    aj.to_csv(os.path.join(a.saida, "ajustes.csv"), index=False)
    fig_tempo_belem(r, a.saida, a.marca)
    fig_tempo_sint(r, a.saida, a.marca)
    fig_ajuste(r, aj, a.saida, a.marca)
    fig_dk(r, a.saida, a.marca)
    fig_memoria(r, a.saida, a.marca)
    tab_belem(r, rz, a.saida)
    tab_ajustes(aj, a.saida)
    print(f"ANALISE OK ({df.instancia.nunique()} instancias, {len(df)} linhas) -> {a.saida}")


if __name__ == "__main__":
    main()
