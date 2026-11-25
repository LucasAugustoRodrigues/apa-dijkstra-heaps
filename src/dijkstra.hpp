#pragma once
#include "grafo.hpp"
#include "contadores.hpp"
#include <vector>
#include <limits>

enum class Variante { Todos, AoAlcancar };

struct Resultado {
    std::vector<double> dist;
    std::vector<int>    pred;
    int alcancados = 0;
};

template <class Fila>
Resultado dijkstra(const Grafo& g, int s, Variante var, Contadores& c) {
    const double INF = std::numeric_limits<double>::infinity();

    Resultado r;
    r.dist.assign(g.n, INF);
    r.pred.assign(g.n, -1);
    r.dist[s] = 0.0;

    Fila fila(g.n, c);

    if (var == Variante::Todos) {
        // Insere todos os vertices: s com 0, demais com INF
        for (int v = 0; v < g.n; ++v)
            fila.insert(v, r.dist[v]);

        while (!fila.vazia() && fila.min_chave() < INF) {
            int u = fila.extract_min();
            r.alcancados++;
            for (std::size_t i = g.inicio[static_cast<std::size_t>(u)];
                 i < g.inicio[static_cast<std::size_t>(u) + 1]; ++i) {
                int    v  = g.destino[i];
                double w  = g.peso[i];
                double nd = r.dist[u] + w;
                if (nd < r.dist[v]) {
                    r.dist[v] = nd;
                    r.pred[v] = u;
                    fila.decrease_key(v, nd);
                }
            }
        }
    } else {
        // AoAlcancar: insere apenas s; insere os demais ao alcanca-los
        fila.insert(s, 0.0);

        while (!fila.vazia()) {
            int u = fila.extract_min();
            r.alcancados++;
            for (std::size_t i = g.inicio[static_cast<std::size_t>(u)];
                 i < g.inicio[static_cast<std::size_t>(u) + 1]; ++i) {
                int    v  = g.destino[i];
                double w  = g.peso[i];
                double nd = r.dist[u] + w;
                if (nd < r.dist[v]) {
                    r.dist[v] = nd;
                    r.pred[v] = u;
                    if (fila.contem(v))
                        fila.decrease_key(v, nd);
                    else
                        fila.insert(v, nd);
                }
            }
        }
    }

    return r;
}
