#pragma once
#include "contadores.hpp"
#include <vector>
#include <utility>

class HeapBinario {
public:
    using Par = std::pair<double, int>; // (chave, v)

    HeapBinario(int n, Contadores& c) : n_(n), c_(c), pos_(n, -1) {
        c_.somar_bytes(static_cast<int64_t>(n) * static_cast<int64_t>(sizeof(int)));
    }

    bool vazia() const { return heap_.empty(); }

    double min_chave() const { return heap_[0].first; }

    void insert(int v, double chave) {
        c_.insert++;
        std::size_t cap_ant = heap_.capacity();
        heap_.emplace_back(chave, v);
        std::size_t cap_nova = heap_.capacity();
        if (cap_nova != cap_ant)
            c_.somar_bytes(static_cast<int64_t>(cap_nova - cap_ant) * static_cast<int64_t>(sizeof(Par)));
        int i = static_cast<int>(heap_.size()) - 1;
        pos_[v] = i;
        subir(i);
    }

    int extract_min() {
        c_.extract_min++;
        int v = heap_[0].second;
        int ultimo = heap_.back().second;
        heap_[0] = heap_.back();
        pos_[ultimo] = 0;
        heap_.pop_back();
        pos_[v] = -1;
        if (!heap_.empty())
            descer(0);
        return v;
    }

    void decrease_key(int v, double chave) {
        c_.decrease_key++;
        int i = pos_[v];
        heap_[i].first = chave;
        subir(i);
    }

    bool contem(int v) const { return pos_[v] != -1; }

private:
    int n_;
    Contadores& c_;
    std::vector<Par> heap_;
    std::vector<int> pos_;

    void trocar(int i, int j) {
        std::swap(heap_[i], heap_[j]);
        pos_[heap_[i].second] = i;
        pos_[heap_[j].second] = j;
    }

    void subir(int i) {
        while (i > 0) {
            int pai = (i - 1) / 2;
            c_.comparacoes++;
            if (heap_[pai].first > heap_[i].first) {
                trocar(i, pai);
                i = pai;
            } else {
                break;
            }
        }
    }

    void descer(int i) {
        int sz = static_cast<int>(heap_.size());
        while (true) {
            int menor = i;
            int esq = 2 * i + 1;
            int dir = 2 * i + 2;
            if (esq < sz) {
                c_.comparacoes++;
                if (heap_[esq].first < heap_[menor].first)
                    menor = esq;
            }
            if (dir < sz) {
                c_.comparacoes++;
                if (heap_[dir].first < heap_[menor].first)
                    menor = dir;
            }
            if (menor != i) {
                trocar(i, menor);
                i = menor;
            } else {
                break;
            }
        }
    }
};
