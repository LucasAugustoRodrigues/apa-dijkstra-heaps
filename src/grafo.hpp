#pragma once
#include <vector>
#include <string>
#include <cstddef>

struct Grafo {
    int n = 0;
    std::size_t m = 0;
    std::vector<std::size_t> inicio;
    std::vector<int> destino;
    std::vector<double> peso;
};

Grafo ler_grafo(const std::string& caminho);
