#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <chrono>
#include <filesystem>
#include <iomanip>
#include <cmath>
#include <random>
#include <cstdint>
#include <limits>

#ifdef _WIN32
#include <windows.h>
#include <psapi.h>
#endif

#include "grafo.hpp"
#include "contadores.hpp"
#include "heap_binario.hpp"
#include "heap_fibonacci.hpp"
#include "dijkstra.hpp"

static uint64_t pico_processo() {
#ifdef _WIN32
    PROCESS_MEMORY_COUNTERS pmc;
    pmc.cb = sizeof(pmc);
    if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, pmc.cb))
        return static_cast<uint64_t>(pmc.PeakWorkingSetSize);
#endif
    return 0;
}

static std::string nome_instancia(const std::string& caminho) {
    return std::filesystem::path(caminho).stem().string();
}

static void mostrar_uso(const char* prog) {
    std::cerr
        << "Uso: " << prog
        << " --grafo <arq> --fila binario|fibonacci"
           " --variante todos|alcance --csv <arq>"
           " [--repeticoes 10] [--aquecimento 1] [--semente 2026]"
           " [--origem <v>] [--distancias <arq>]\n";
}

int main(int argc, char* argv[]) {
    std::string arq_grafo, tipo_fila, tipo_variante, arq_csv, arq_dist;
    int      repeticoes = 10, aquecimento = 1;
    uint64_t semente    = 2026;
    int      origem_fixa = -1;
    bool     tem_origem  = false;

    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if      (a == "--grafo"       && i+1 < argc) arq_grafo     = argv[++i];
        else if (a == "--fila"        && i+1 < argc) tipo_fila     = argv[++i];
        else if (a == "--variante"    && i+1 < argc) tipo_variante = argv[++i];
        else if (a == "--csv"         && i+1 < argc) arq_csv       = argv[++i];
        else if (a == "--repeticoes"  && i+1 < argc) {
            try { repeticoes = std::stoi(argv[++i]); }
            catch (...) { mostrar_uso(argv[0]); return 2; }
        }
        else if (a == "--aquecimento" && i+1 < argc) {
            try { aquecimento = std::stoi(argv[++i]); }
            catch (...) { mostrar_uso(argv[0]); return 2; }
        }
        else if (a == "--semente"     && i+1 < argc) {
            try { semente = std::stoull(argv[++i]); }
            catch (...) { mostrar_uso(argv[0]); return 2; }
        }
        else if (a == "--origem"      && i+1 < argc) {
            try { origem_fixa = std::stoi(argv[++i]); }
            catch (...) { mostrar_uso(argv[0]); return 2; }
            tem_origem = true;
        }
        else if (a == "--distancias"  && i+1 < argc) arq_dist = argv[++i];
        else { mostrar_uso(argv[0]); return 2; }
    }

    if (arq_grafo.empty() || tipo_fila.empty() || tipo_variante.empty() || arq_csv.empty()) {
        mostrar_uso(argv[0]); return 2;
    }
    if (repeticoes < 1 || aquecimento < 0) {
        mostrar_uso(argv[0]); return 2;
    }
    if (tipo_fila != "binario" && tipo_fila != "fibonacci") {
        mostrar_uso(argv[0]); return 2;
    }
    if (tipo_variante != "todos" && tipo_variante != "alcance") {
        mostrar_uso(argv[0]); return 2;
    }

    // Le o grafo (fora da medicao)
    Grafo g;
    try {
        g = ler_grafo(arq_grafo);
    } catch (const std::exception& e) {
        std::cerr << "Erro ao ler grafo: " << e.what() << "\n";
        return 1;
    }

    if (tem_origem && (origem_fixa < 0 || origem_fixa >= g.n)) {
        std::cerr << "Erro: --origem " << origem_fixa
                  << " fora do intervalo [0, " << (g.n - 1) << "]\n";
        return 2;
    }

    Variante var = (tipo_variante == "todos") ? Variante::Todos : Variante::AoAlcancar;

    // Gera origens antes de qualquer execucao (aquecimento e medicao usam a mesma lista)
    std::vector<int> origens(static_cast<std::size_t>(repeticoes));
    if (tem_origem) {
        for (int& o : origens) o = origem_fixa;
    } else {
        std::mt19937_64 gen(semente);
        for (int& o : origens)
            o = static_cast<int>(gen() % static_cast<uint64_t>(g.n));
    }

    // Abre CSV em modo append (cabecalho apenas se arquivo nao existia)
    bool precisa_header = !std::filesystem::exists(arq_csv);
    {
        auto parent = std::filesystem::path(arq_csv).parent_path();
        if (!parent.empty()) std::filesystem::create_directories(parent);
    }
    std::ofstream csv(arq_csv, std::ios::app);
    if (!csv) {
        std::cerr << "Erro ao abrir arquivo CSV: " << arq_csv << "\n";
        return 1;
    }
    csv.imbue(std::locale::classic()); // ponto como separador decimal

    if (precisa_header)
        csv << "instancia,n,m,fila,variante,repeticao,origem,tempo_ms,"
               "insert,extract_min,decrease_key,comparacoes,alcancados,"
               "bytes_fila_pico,pico_processo_bytes\n";

    std::string inst = nome_instancia(arq_grafo);

    // Aquecimento: roda com a primeira origem, sem gravar
    if (aquecimento > 0 && !origens.empty()) {
        for (int w = 0; w < aquecimento; ++w) {
            Contadores c;
            if (tipo_fila == "binario")
                dijkstra<HeapBinario>  (g, origens[0], var, c);
            else
                dijkstra<HeapFibonacci>(g, origens[0], var, c);
        }
    }

    // Repeticoes medidas
    std::vector<double> dist_primeira;

    for (int rep = 0; rep < repeticoes; ++rep) {
        int orig = origens[static_cast<std::size_t>(rep)];
        Contadores c;

        auto t0 = std::chrono::steady_clock::now();
        Resultado r;
        if (tipo_fila == "binario")
            r = dijkstra<HeapBinario>  (g, orig, var, c);
        else
            r = dijkstra<HeapFibonacci>(g, orig, var, c);
        auto t1 = std::chrono::steady_clock::now();

        double   tempo_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
        uint64_t pico     = pico_processo();

        if (rep == 0 && !arq_dist.empty())
            dist_primeira = r.dist;

        csv << inst           << ","
            << g.n            << ","
            << g.m            << ","
            << tipo_fila      << ","
            << tipo_variante  << ","
            << (rep + 1)      << ","
            << orig           << ","
            << std::fixed << std::setprecision(6) << tempo_ms << ","
            << c.insert       << ","
            << c.extract_min  << ","
            << c.decrease_key << ","
            << c.comparacoes  << ","
            << r.alcancados   << ","
            << c.bytes_fila_pico << ","
            << pico           << "\n";
    }

    // Arquivo de distancias (1a repeticao medida)
    if (!arq_dist.empty() && !dist_primeira.empty()) {
        {
            auto parent = std::filesystem::path(arq_dist).parent_path();
            if (!parent.empty()) std::filesystem::create_directories(parent);
        }
        std::ofstream df(arq_dist);
        if (!df) {
            std::cerr << "Erro ao abrir arquivo de distancias: " << arq_dist << "\n";
            return 1;
        }
        df.imbue(std::locale::classic());
        df << std::setprecision(17);
        for (int v = 0; v < g.n; ++v) {
            double d = dist_primeira[static_cast<std::size_t>(v)];
            if (std::isinf(d))
                df << v << " inf\n";
            else
                df << v << " " << d << "\n";
        }
    }

    return 0;
}
