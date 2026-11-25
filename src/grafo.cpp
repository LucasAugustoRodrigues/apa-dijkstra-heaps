#include "grafo.hpp"
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <charconv>
#include <cmath>
#include <limits>

// Le o conteudo inteiro do arquivo em uma string
static std::string ler_arquivo(const std::string& caminho) {
    std::ifstream f(caminho, std::ios::binary | std::ios::ate);
    if (!f)
        throw std::runtime_error("Nao foi possivel abrir o arquivo: " + caminho);
    auto tamanho = f.tellg();
    f.seekg(0);
    std::string conteudo(static_cast<std::size_t>(tamanho), '\0');
    f.read(conteudo.data(), tamanho);
    return conteudo;
}

// Avanca o ponteiro sobre espacos e tabs (nao quebras de linha)
static const char* pular_espaco(const char* p, const char* fim) {
    while (p < fim && (*p == ' ' || *p == '\t'))
        ++p;
    return p;
}

// Avanca o ponteiro sobre qualquer espaco em branco incluindo quebras
static const char* pular_ws(const char* p, const char* fim) {
    while (p < fim && (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n'))
        ++p;
    return p;
}

Grafo ler_grafo(const std::string& caminho) {
    std::string conteudo = ler_arquivo(caminho);
    const char* p   = conteudo.data();
    const char* fim = p + conteudo.size();

    p = pular_ws(p, fim);

    // Le n
    int n = 0;
    auto res = std::from_chars(p, fim, n);
    if (res.ec != std::errc{})
        throw std::runtime_error("Erro ao ler n em: " + caminho);
    p = res.ptr;
    p = pular_espaco(p, fim);

    // Le m
    std::size_t m = 0;
    res = std::from_chars(p, fim, m);
    if (res.ec != std::errc{})
        throw std::runtime_error("Erro ao ler m em: " + caminho);
    p = res.ptr;

    if (n < 1)
        throw std::runtime_error("n deve ser >= 1 em: " + caminho);

    // Listas temporarias de arcos
    struct Arco { int u, v; double w; };
    std::vector<Arco> arcos;
    arcos.reserve(m);

    std::size_t lidos = 0;
    while (lidos < m) {
        p = pular_ws(p, fim);
        if (p >= fim)
            break;

        int u = 0;
        res = std::from_chars(p, fim, u);
        if (res.ec != std::errc{})
            throw std::runtime_error("Erro ao ler u no arco " + std::to_string(lidos) + " em: " + caminho);
        p = res.ptr;
        p = pular_espaco(p, fim);

        int v = 0;
        res = std::from_chars(p, fim, v);
        if (res.ec != std::errc{})
            throw std::runtime_error("Erro ao ler v no arco " + std::to_string(lidos) + " em: " + caminho);
        p = res.ptr;
        p = pular_espaco(p, fim);

        // Peso como double via from_chars
        double w = 0.0;
        auto res_d = std::from_chars(p, fim, w);
        if (res_d.ec != std::errc{})
            throw std::runtime_error("Erro ao ler peso no arco " + std::to_string(lidos) + " em: " + caminho);
        p = res_d.ptr;

        if (u < 0 || u >= n || v < 0 || v >= n)
            throw std::runtime_error("Vertice fora do intervalo [0, n-1] no arco " + std::to_string(lidos) + " em: " + caminho);
        if (w < 0.0 || std::isnan(w) || std::isinf(w))
            throw std::runtime_error("Peso invalido (negativo, NaN ou infinito) no arco " + std::to_string(lidos) + " em: " + caminho);

        arcos.push_back({u, v, w});
        ++lidos;
    }

    if (lidos < m)
        throw std::runtime_error("Arquivo com menos de m arcos em: " + caminho);

    // Monta CSR
    Grafo g;
    g.n = n;
    g.m = m;
    g.inicio.assign(static_cast<std::size_t>(n) + 1, 0);
    g.destino.resize(m);
    g.peso.resize(m);

    // Conta arcos saindo de cada vertice
    for (auto& a : arcos)
        g.inicio[static_cast<std::size_t>(a.u) + 1]++;

    // Acumula prefixos
    for (int i = 1; i <= n; ++i)
        g.inicio[static_cast<std::size_t>(i)] += g.inicio[static_cast<std::size_t>(i) - 1];

    // Preenche destino e peso mantendo ordem do arquivo
    std::vector<std::size_t> cursor(g.inicio.begin(), g.inicio.begin() + n);
    for (auto& a : arcos) {
        std::size_t idx = cursor[static_cast<std::size_t>(a.u)]++;
        g.destino[idx] = a.v;
        g.peso[idx]    = a.w;
    }

    return g;
}
