#pragma once
#include <cstdint>
#include <algorithm>

struct Contadores {
    uint64_t insert        = 0;
    uint64_t extract_min   = 0;
    uint64_t decrease_key  = 0;
    uint64_t comparacoes   = 0;
    int64_t  bytes_fila    = 0;
    int64_t  bytes_fila_pico = 0;

    void zerar() {
        insert = extract_min = decrease_key = comparacoes = 0;
        bytes_fila = bytes_fila_pico = 0;
    }

    void somar_bytes(int64_t delta) {
        bytes_fila += delta;
        bytes_fila_pico = std::max(bytes_fila_pico, bytes_fila);
    }
};
