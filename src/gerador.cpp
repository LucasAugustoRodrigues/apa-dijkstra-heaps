#include <iostream>
#include <string>
#include <charconv>
#include <cstdio>
#include <cstdint>
#include <cstddef>
#include <random>
#include <filesystem>

static void mostrar_uso(const char* prog) {
    std::cerr << "Uso: " << prog
              << " --n <n> --grau <k> --saida <arq> [--semente 2026]\n"
              << "  n >= 2, k >= 1 (inteiros)\n";
}

int main(int argc, char* argv[]) {
    std::size_t n = 0, k = 0;
    uint64_t semente = 2026;
    std::string arq;
    bool tem_n = false, tem_k = false, tem_saida = false;

    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--n" && i + 1 < argc) {
            try {
                long long v = std::stoll(argv[++i]);
                if (v < 2) { mostrar_uso(argv[0]); return 2; }
                n = static_cast<std::size_t>(v);
                tem_n = true;
            } catch (...) { mostrar_uso(argv[0]); return 2; }
        } else if (a == "--grau" && i + 1 < argc) {
            try {
                long long v = std::stoll(argv[++i]);
                if (v < 1) { mostrar_uso(argv[0]); return 2; }
                k = static_cast<std::size_t>(v);
                tem_k = true;
            } catch (...) { mostrar_uso(argv[0]); return 2; }
        } else if (a == "--saida" && i + 1 < argc) {
            arq = argv[++i];
            tem_saida = true;
        } else if (a == "--semente" && i + 1 < argc) {
            try {
                semente = std::stoull(argv[++i]);
            } catch (...) { mostrar_uso(argv[0]); return 2; }
        } else {
            mostrar_uso(argv[0]); return 2;
        }
    }

    if (!tem_n || !tem_k || !tem_saida) {
        mostrar_uso(argv[0]); return 2;
    }

    std::size_t m = k * n;

    std::mt19937_64 gen(semente);

    auto parent = std::filesystem::path(arq).parent_path();
    if (!parent.empty()) std::filesystem::create_directories(parent);

    FILE* f = fopen(arq.c_str(), "wb");
    if (!f) {
        std::cerr << "Erro ao abrir arquivo: " << arq << "\n";
        return 1;
    }

    static char buf[1 << 20];
    std::size_t pos = 0;

    auto flush_buf = [&]() {
        if (pos > 0) {
            fwrite(buf, 1, pos, f);
            pos = 0;
        }
    };

    auto escreve_uint = [&](uint64_t v) {
        if (pos + 25 > sizeof(buf)) flush_buf();
        auto res = std::to_chars(buf + pos, buf + sizeof(buf), v);
        pos = static_cast<std::size_t>(res.ptr - buf);
    };

    auto escreve_char = [&](char c) {
        if (pos + 1 > sizeof(buf)) flush_buf();
        buf[pos++] = c;
    };

    // cabecalho
    escreve_uint(static_cast<uint64_t>(n));
    escreve_char(' ');
    escreve_uint(static_cast<uint64_t>(m));
    escreve_char('\n');

    // ciclo: i -> (i+1)%n
    for (std::size_t i = 0; i < n; ++i) {
        uint64_t w = 1 + gen() % 1000;
        escreve_uint(static_cast<uint64_t>(i));
        escreve_char(' ');
        escreve_uint(static_cast<uint64_t>((i + 1) % n));
        escreve_char(' ');
        escreve_uint(w);
        escreve_char('\n');
    }

    // arcos aleatorios
    for (std::size_t i = 0; i < m - n; ++i) {
        uint64_t u = gen() % static_cast<uint64_t>(n);
        uint64_t v;
        do { v = gen() % static_cast<uint64_t>(n); } while (v == u);
        uint64_t w = 1 + gen() % 1000;
        escreve_uint(u);
        escreve_char(' ');
        escreve_uint(v);
        escreve_char(' ');
        escreve_uint(w);
        escreve_char('\n');
    }

    flush_buf();
    fclose(f);

    std::cout << "gerado " << arq << ": n=" << n << " m=" << m << "\n";
    return 0;
}
