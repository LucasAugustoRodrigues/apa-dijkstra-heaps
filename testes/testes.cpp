#include "grafo.hpp"
#include "heap_binario.hpp"
#include "heap_fibonacci.hpp"
#include "dijkstra.hpp"
#include <iostream>
#include <string>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <random>
#include <vector>
#include <set>
#include <algorithm>
#include <cmath>
#include <array>

// ------------------------------------------------------------------ utilidades

static void falhou(const std::string& nome, const std::string& msg) {
    std::cerr << "[FALHA] " << nome << ": " << msg << "\n";
    std::exit(1);
}

static void criar_arquivo(const std::string& caminho, const std::string& conteudo) {
    std::filesystem::create_directories(
        std::filesystem::path(caminho).parent_path());
    std::ofstream f(caminho);
    f << conteudo;
}

// ------------------------------------------------------------------ testes T1

static void teste_ler_grafo_clrs() {
    const std::string nome = "ler_grafo_clrs";

    Grafo g = ler_grafo("testes/grafos/clrs.txt");

    if (g.n != 6)
        falhou(nome, "n esperado 6, obtido " + std::to_string(g.n));
    if (g.m != 11)
        falhou(nome, "m esperado 11, obtido " + std::to_string(g.m));

    std::size_t ini = g.inicio[3];
    std::size_t fim = g.inicio[4];
    if (fim - ini != 3)
        falhou(nome, "vertice 3 deve ter 3 arcos, tem " + std::to_string(fim - ini));

    struct Esperado { int v; double w; };
    Esperado esperados[3] = {{1, 3.0}, {2, 9.0}, {4, 2.0}};
    for (int i = 0; i < 3; ++i) {
        int v = g.destino[ini + static_cast<std::size_t>(i)];
        double w = g.peso[ini + static_cast<std::size_t>(i)];
        if (v != esperados[i].v || w != esperados[i].w)
            falhou(nome, "arco " + std::to_string(i) + " de 3: esperado ("
                + std::to_string(esperados[i].v) + ", " + std::to_string(esperados[i].w)
                + "), obtido (" + std::to_string(v) + ", " + std::to_string(w) + ")");
    }
}

static void teste_ler_grafo_invalido() {
    const std::string nome = "ler_grafo_invalido";

    criar_arquivo("dados/teste_tmp/invalido.txt",
        "6 1\n0 7 1.0\n");

    bool lancou = false;
    try {
        ler_grafo("dados/teste_tmp/invalido.txt");
    } catch (const std::runtime_error&) {
        lancou = true;
    }
    if (!lancou)
        falhou(nome, "deveria lancar std::runtime_error para vertice fora de [0, n-1]");
}

// ------------------------------------------------------------------ testes T2

static void teste_heap_binario_aleatorio() {
    const std::string nome = "heap_binario_aleatorio";
    const int N = 500;
    const int OPS = 20000;

    Contadores c;
    HeapBinario heap(N, c);

    // estado local
    std::vector<double> chave_de(N, -1.0); // chave atual (valida so se na_fila[v])
    std::vector<bool> na_fila(N, false);
    std::vector<int> em_fila;
    std::vector<int> fora_fila;
    fora_fila.reserve(N);
    for (int i = 0; i < N; ++i) fora_fila.push_back(i);

    // referencia
    std::multiset<std::pair<double, int>> ref;

    std::mt19937_64 rng(2026);
    uint64_t cnt_insert = 0, cnt_extract = 0, cnt_decrease = 0;

    for (int ops = 0; ops < OPS; ++ops) {
        // Monta lista de operacoes disponiveis
        std::vector<int> avail;
        if (!fora_fila.empty()) avail.push_back(0); // insert
        if (!em_fila.empty())   { avail.push_back(1); avail.push_back(2); } // extract, decrease

        int tipo = avail[static_cast<std::size_t>(rng() % avail.size())];

        if (tipo == 0) {
            // insert: escolhe vertice fora da fila
            std::size_t idx = rng() % fora_fila.size();
            int v = fora_fila[idx];
            fora_fila[idx] = fora_fila.back();
            fora_fila.pop_back();

            double chave = static_cast<double>(rng() % 1001);
            heap.insert(v, chave);
            chave_de[v] = chave;
            na_fila[v] = true;
            em_fila.push_back(v);
            ref.insert({chave, v});
            ++cnt_insert;

        } else if (tipo == 1) {
            // extract_min
            double min_ref = ref.begin()->first;
            int v = heap.extract_min();
            if (chave_de[v] != min_ref)
                falhou(nome, "extract_min retornou vertice com chave " +
                    std::to_string(chave_de[v]) + ", minimo esperado " +
                    std::to_string(min_ref));

            ref.erase(ref.find({chave_de[v], v}));
            na_fila[v] = false;
            auto it = std::find(em_fila.begin(), em_fila.end(), v);
            *it = em_fila.back();
            em_fila.pop_back();
            fora_fila.push_back(v);
            chave_de[v] = -1.0;
            ++cnt_extract;

        } else {
            // decrease_key: escolhe vertice na fila, nova chave <= atual
            std::size_t idx = rng() % em_fila.size();
            int v = em_fila[idx];
            double old_chave = chave_de[v];
            double nova = static_cast<double>(
                rng() % (static_cast<uint64_t>(old_chave) + 1));

            ref.erase(ref.find({old_chave, v}));
            heap.decrease_key(v, nova);
            chave_de[v] = nova;
            ref.insert({nova, v});
            ++cnt_decrease;
        }
    }

    // verifica contadores
    if (c.insert != cnt_insert)
        falhou(nome, "contador insert: esperado " + std::to_string(cnt_insert) +
            ", obtido " + std::to_string(c.insert));
    if (c.extract_min != cnt_extract)
        falhou(nome, "contador extract_min: esperado " + std::to_string(cnt_extract) +
            ", obtido " + std::to_string(c.extract_min));
    if (c.decrease_key != cnt_decrease)
        falhou(nome, "contador decrease_key: esperado " + std::to_string(cnt_decrease) +
            ", obtido " + std::to_string(c.decrease_key));
}

// ------------------------------------------------------------------ testes T3

// Mesmo cenario aleatorio da T2, porem com verificar() a cada 100 operacoes
static void teste_heap_fibonacci_aleatorio() {
    const std::string nome = "heap_fibonacci_aleatorio";
    const int N = 500;
    const int OPS = 20000;

    Contadores c;
    HeapFibonacci heap(N, c);

    std::vector<double> chave_de(N, -1.0);
    std::vector<int> em_fila, fora_fila;
    fora_fila.reserve(N);
    for (int i = 0; i < N; ++i) fora_fila.push_back(i);

    std::multiset<std::pair<double, int>> ref;
    std::mt19937_64 rng(2026);
    uint64_t cnt_insert = 0, cnt_extract = 0, cnt_decrease = 0;

    for (int ops = 0; ops < OPS; ++ops) {
        std::vector<int> avail;
        if (!fora_fila.empty()) avail.push_back(0);
        if (!em_fila.empty())   { avail.push_back(1); avail.push_back(2); }

        int tipo = avail[static_cast<std::size_t>(rng() % avail.size())];

        if (tipo == 0) {
            std::size_t idx = rng() % fora_fila.size();
            int v = fora_fila[idx];
            fora_fila[idx] = fora_fila.back();
            fora_fila.pop_back();
            double chave = static_cast<double>(rng() % 1001);
            heap.insert(v, chave);
            chave_de[v] = chave;
            em_fila.push_back(v);
            ref.insert({chave, v});
            ++cnt_insert;

        } else if (tipo == 1) {
            double min_ref = ref.begin()->first;
            int v = heap.extract_min();
            if (chave_de[v] != min_ref)
                falhou(nome, "extract_min retornou vertice com chave " +
                    std::to_string(chave_de[v]) + ", minimo esperado " +
                    std::to_string(min_ref));
            ref.erase(ref.find({chave_de[v], v}));
            auto it = std::find(em_fila.begin(), em_fila.end(), v);
            *it = em_fila.back();
            em_fila.pop_back();
            fora_fila.push_back(v);
            chave_de[v] = -1.0;
            ++cnt_extract;

        } else {
            std::size_t idx = rng() % em_fila.size();
            int v = em_fila[idx];
            double old_chave = chave_de[v];
            double nova = static_cast<double>(
                rng() % (static_cast<uint64_t>(old_chave) + 1));
            ref.erase(ref.find({old_chave, v}));
            heap.decrease_key(v, nova);
            chave_de[v] = nova;
            ref.insert({nova, v});
            ++cnt_decrease;
        }

        if ((ops + 1) % 100 == 0 && !heap.vazia())
            if (!heap.verificar())
                falhou(nome, "verificar falhou na operacao " + std::to_string(ops + 1));
    }

    if (c.insert != cnt_insert)
        falhou(nome, "contador insert: esperado " + std::to_string(cnt_insert) +
            ", obtido " + std::to_string(c.insert));
    if (c.extract_min != cnt_extract)
        falhou(nome, "contador extract_min: esperado " + std::to_string(cnt_extract) +
            ", obtido " + std::to_string(c.extract_min));
    if (c.decrease_key != cnt_decrease)
        falhou(nome, "contador decrease_key: esperado " + std::to_string(cnt_decrease) +
            ", obtido " + std::to_string(c.decrease_key));
}

// Teste que forca corte em cascata:
// Insere 20 chaves, extract_min para consolidar, depois decrease_key em dois
// filhos do mesmo no nao-raiz (vertice 5 tem filhos 6 e 7 apos consolidacao)
static void teste_heap_fibonacci_corte_cascata() {
    const std::string nome = "heap_fibonacci_corte_cascata";
    const int N = 30;

    Contadores c;
    HeapFibonacci heap(N, c);
    std::multiset<std::pair<double, int>> ref;
    std::vector<double> chave_de(N, -1.0);

    for (int i = 0; i < 20; ++i) {
        heap.insert(i, static_cast<double>(i));
        ref.insert({static_cast<double>(i), i});
        chave_de[i] = static_cast<double>(i);
    }

    if (!heap.verificar())
        falhou(nome, "verificar falhou apos insercoes");

    // extract_min para consolidar (remove vertice 0, chave 0.0)
    {
        double min_ref = ref.begin()->first;
        int v = heap.extract_min();
        if (chave_de[v] != min_ref)
            falhou(nome, "extract_min: chave errada apos insercoes");
        ref.erase(ref.find({chave_de[v], v}));
        chave_de[v] = -1.0;
    }

    if (!heap.verificar())
        falhou(nome, "verificar falhou apos extract_min");

    // Vertice 5 (chave 5) e nao-raiz com filhos 6 e 7 apos consolidacao.
    // decrease_key(6, 0.5): corta vertice 6 de 5, marca vertice 5
    ref.erase(ref.find({chave_de[6], 6}));
    heap.decrease_key(6, 0.5);
    chave_de[6] = 0.5;
    ref.insert({0.5, 6});

    if (!heap.verificar())
        falhou(nome, "verificar falhou apos decrease_key(6, 0.5)");

    // decrease_key(7, 0.5): corta vertice 7 de 5; como 5 ja esta marcado,
    // dispara corte em cascata e 5 vai para lista de raizes
    ref.erase(ref.find({chave_de[7], 7}));
    heap.decrease_key(7, 0.5);
    chave_de[7] = 0.5;
    ref.insert({0.5, 7});

    if (!heap.verificar())
        falhou(nome, "verificar falhou apos corte em cascata (decrease_key 7)");

    if (heap.min_chave() != 0.5)
        falhou(nome, "min_chave esperado 0.5, obtido " +
            std::to_string(heap.min_chave()));

    // Extrai tudo e confere com multiset
    while (!heap.vazia()) {
        double min_ref = ref.begin()->first;
        int v = heap.extract_min();
        if (chave_de[v] != min_ref)
            falhou(nome, "extract_min na verificacao final: chave " +
                std::to_string(chave_de[v]) + " != min_ref " +
                std::to_string(min_ref));
        ref.erase(ref.find({chave_de[v], v}));
        chave_de[v] = -1.0;
    }

    if (!ref.empty())
        falhou(nome, "multiset nao esvaziou junto com o heap");
}

// ------------------------------------------------------------------ helpers T4

// Dijkstra ingenuo O(n^2) com vetor de visitados - usado como referencia
static Resultado dijkstra_ingenuo(const Grafo& g, int s) {
    const double INF = std::numeric_limits<double>::infinity();
    Resultado r;
    r.dist.assign(g.n, INF);
    r.pred.assign(g.n, -1);
    r.dist[s] = 0.0;

    std::vector<bool> vis(g.n, false);
    for (int iter = 0; iter < g.n; ++iter) {
        int u = -1;
        double md = INF;
        for (int v = 0; v < g.n; ++v)
            if (!vis[v] && r.dist[v] < md) { md = r.dist[v]; u = v; }
        if (u == -1) break;
        vis[u] = true;
        r.alcancados++;
        for (std::size_t i = g.inicio[static_cast<std::size_t>(u)];
             i < g.inicio[static_cast<std::size_t>(u) + 1]; ++i) {
            int v = g.destino[i];
            double nd = r.dist[u] + g.peso[i];
            if (nd < r.dist[v]) { r.dist[v] = nd; r.pred[v] = u; }
        }
    }
    return r;
}

// Constroi Grafo em formato CSR a partir de lista de arcos {u, v, w_int}
static Grafo construir_grafo(int n,
                              const std::vector<std::array<int, 3>>& arcos) {
    Grafo g;
    g.n = n;
    g.m = arcos.size();
    g.inicio.assign(static_cast<std::size_t>(n) + 1, 0);
    g.destino.resize(g.m);
    g.peso.resize(g.m);

    for (auto& a : arcos) g.inicio[static_cast<std::size_t>(a[0]) + 1]++;
    for (int i = 1; i <= n; ++i)
        g.inicio[static_cast<std::size_t>(i)] +=
            g.inicio[static_cast<std::size_t>(i) - 1];

    std::vector<std::size_t> cur(g.inicio.begin(),
                                 g.inicio.begin() + n);
    for (auto& a : arcos) {
        std::size_t idx = cur[static_cast<std::size_t>(a[0])]++;
        g.destino[idx] = a[1];
        g.peso[idx]    = static_cast<double>(a[2]);
    }
    return g;
}

// Roda dijkstra<Fila> e verifica contadores; retorna o Resultado
template <class Fila>
static Resultado rodar_checar(const Grafo& g, int s, Variante var,
                               const std::string& ctx) {
    Contadores c;
    Resultado r = dijkstra<Fila>(g, s, var, c);

    if (c.extract_min != static_cast<uint64_t>(r.alcancados))
        falhou(ctx, "extract_min(" + std::to_string(c.extract_min) +
               ") != alcancados(" + std::to_string(r.alcancados) + ")");

    if (c.decrease_key > g.m)
        falhou(ctx, "decrease_key(" + std::to_string(c.decrease_key) +
               ") > m(" + std::to_string(g.m) + ")");

    if (var == Variante::Todos) {
        if (c.insert != static_cast<uint64_t>(g.n))
            falhou(ctx, "Todos: insert(" + std::to_string(c.insert) +
                   ") != n(" + std::to_string(g.n) + ")");
    } else {
        if (c.insert != static_cast<uint64_t>(r.alcancados))
            falhou(ctx, "AoAlcancar: insert(" + std::to_string(c.insert) +
                   ") != alcancados(" + std::to_string(r.alcancados) + ")");
    }

    if (c.bytes_fila_pico <= 0)
        falhou(ctx, "bytes_fila_pico <= 0");

    return r;
}

// Compara dois vetores dist (trata INF == INF como iguais)
static bool dists_iguais(const std::vector<double>& a,
                         const std::vector<double>& b) {
    if (a.size() != b.size()) return false;
    for (std::size_t i = 0; i < a.size(); ++i) {
        bool ai = std::isinf(a[i]), bi = std::isinf(b[i]);
        if (ai && bi) continue;
        if (ai != bi || a[i] != b[i]) return false;
    }
    return true;
}

// ------------------------------------------------------------------ testes T4

static void teste_dijkstra_clrs() {
    const std::string nome = "dijkstra_clrs";
    Grafo g = ler_grafo("testes/grafos/clrs.txt");

    // Distancias e predecessores esperados a partir de 0
    const std::vector<double> dist_esp = {0, 8, 9, 5, 7,
        std::numeric_limits<double>::infinity()};
    const std::vector<int> pred_esp = {-1, 3, 1, 0, 3, -1};

    for (int cfg = 0; cfg < 4; ++cfg) {
        bool  bin = (cfg < 2);
        Variante var = (cfg % 2 == 0) ? Variante::Todos : Variante::AoAlcancar;
        std::string fila_s = bin ? "binario" : "fibonacci";
        std::string var_s  = (var == Variante::Todos) ? "todos" : "alcance";
        std::string ctx    = nome + " [" + fila_s + "/" + var_s + "]";

        Resultado r = bin
            ? rodar_checar<HeapBinario>  (g, 0, var, ctx)
            : rodar_checar<HeapFibonacci>(g, 0, var, ctx);

        if (!dists_iguais(r.dist, dist_esp))
            falhou(ctx, "distancias incorretas");

        if (r.pred != pred_esp)
            falhou(ctx, "predecessores incorretos");
    }
}

static void teste_dijkstra_aleatorio() {
    const std::string nome = "dijkstra_aleatorio";
    std::mt19937_64 rng(2026);

    // 300 grafos pequenos
    for (int gi = 0; gi < 300; ++gi) {
        int n = 1 + static_cast<int>(rng() % 200);
        int m = static_cast<int>(rng() % (static_cast<uint64_t>(6 * n) + 1));
        int s = static_cast<int>(rng() % static_cast<uint64_t>(n));

        std::vector<std::array<int, 3>> arcos;
        arcos.reserve(static_cast<std::size_t>(m));
        for (int i = 0; i < m; ++i) {
            int u = static_cast<int>(rng() % static_cast<uint64_t>(n));
            int v = static_cast<int>(rng() % static_cast<uint64_t>(n));
            int w = static_cast<int>(rng() % 21); // 0 a 20
            arcos.push_back({u, v, w});
        }

        Grafo g = construir_grafo(n, arcos);
        std::string ctx = nome + " grafo#" + std::to_string(gi);

        Resultado ing = dijkstra_ingenuo(g, s);

        Resultado r0 = rodar_checar<HeapBinario>  (g, s, Variante::Todos,       ctx + " bin/todos");
        Resultado r1 = rodar_checar<HeapBinario>  (g, s, Variante::AoAlcancar,  ctx + " bin/alcance");
        Resultado r2 = rodar_checar<HeapFibonacci>(g, s, Variante::Todos,       ctx + " fib/todos");
        Resultado r3 = rodar_checar<HeapFibonacci>(g, s, Variante::AoAlcancar,  ctx + " fib/alcance");

        if (!dists_iguais(r0.dist, ing.dist)) falhou(ctx, "bin/todos != ingenuo");
        if (!dists_iguais(r1.dist, ing.dist)) falhou(ctx, "bin/alcance != ingenuo");
        if (!dists_iguais(r2.dist, ing.dist)) falhou(ctx, "fib/todos != ingenuo");
        if (!dists_iguais(r3.dist, ing.dist)) falhou(ctx, "fib/alcance != ingenuo");
    }

    // Grafo grande: n=20000, m=100000, pesos inteiros de 1 a 1000
    {
        const int NL = 20000, ML = 100000;
        int sl = static_cast<int>(rng() % static_cast<uint64_t>(NL));

        std::vector<std::array<int, 3>> arcos;
        arcos.reserve(static_cast<std::size_t>(ML));
        for (int i = 0; i < ML; ++i) {
            int u = static_cast<int>(rng() % static_cast<uint64_t>(NL));
            int v = static_cast<int>(rng() % static_cast<uint64_t>(NL));
            int w = 1 + static_cast<int>(rng() % 1000);
            arcos.push_back({u, v, w});
        }

        Grafo gl = construir_grafo(NL, arcos);
        std::string ctx = nome + " grafo_grande";

        Resultado r0 = rodar_checar<HeapBinario>  (gl, sl, Variante::Todos,      ctx + " bin/todos");
        Resultado r1 = rodar_checar<HeapBinario>  (gl, sl, Variante::AoAlcancar, ctx + " bin/alcance");
        Resultado r2 = rodar_checar<HeapFibonacci>(gl, sl, Variante::Todos,      ctx + " fib/todos");
        Resultado r3 = rodar_checar<HeapFibonacci>(gl, sl, Variante::AoAlcancar, ctx + " fib/alcance");

        if (!dists_iguais(r0.dist, r1.dist)) falhou(ctx, "bin/todos != bin/alcance");
        if (!dists_iguais(r0.dist, r2.dist)) falhou(ctx, "bin/todos != fib/todos");
        if (!dists_iguais(r0.dist, r3.dist)) falhou(ctx, "bin/todos != fib/alcance");
    }
}

// ------------------------------------------------------------------ main

int main() {
    teste_ler_grafo_clrs();
    teste_ler_grafo_invalido();
    teste_heap_binario_aleatorio();
    teste_heap_fibonacci_aleatorio();
    teste_heap_fibonacci_corte_cascata();
    teste_dijkstra_clrs();
    teste_dijkstra_aleatorio();

    std::cout << "TODOS OS TESTES PASSARAM\n";
    return 0;
}
