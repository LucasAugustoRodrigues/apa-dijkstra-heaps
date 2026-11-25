#pragma once
#include "contadores.hpp"
#include <vector>
#include <cmath>

class HeapFibonacci {
    struct No {
        double chave;
        int    v;
        int    grau    = 0;
        bool   marcado = false;
        No*    pai     = nullptr;
        No*    filho   = nullptr;
        No*    esq;
        No*    dir;

        No(double c, int vertex) : chave(c), v(vertex), esq(this), dir(this) {}
    };

public:
    HeapFibonacci(int n, Contadores& c) : n_(n), c_(c), no_de_(n, nullptr) {
        c_.somar_bytes(static_cast<int64_t>(n) * static_cast<int64_t>(sizeof(No*)));
    }

    ~HeapFibonacci() {
        if (min_) deletar_lista(min_);
    }

    bool vazia() const { return min_ == nullptr; }

    double min_chave() const { return min_->chave; }

    void insert(int v, double chave) {
        c_.insert++;
        No* x = new No(chave, v);
        no_de_[v] = x;
        tamanho_++;
        c_.somar_bytes(static_cast<int64_t>(sizeof(No)));

        if (min_ == nullptr) {
            min_ = x;
        } else {
            // Insere x antes de min_ na lista de raizes
            No* me = min_->esq;
            me->dir  = x;
            x->esq   = me;
            x->dir   = min_;
            min_->esq = x;

            c_.comparacoes++; // 1 comparacao para atualizar minimo
            if (chave < min_->chave)
                min_ = x;
        }
    }

    int extract_min() {
        c_.extract_min++;
        No* z = min_;
        int v = z->v;

        // Adiciona filhos de z na lista de raizes
        if (z->filho) {
            No* child = z->filho;
            do {
                child->pai    = nullptr;
                child->marcado = false;
                child = child->dir;
            } while (child != z->filho);

            // Funde lista de filhos com lista de raizes (antes de z)
            No* fc = z->filho;
            No* fl = fc->esq;
            No* ze = z->esq;

            ze->dir  = fc;
            fc->esq  = ze;
            fl->dir  = z;
            z->esq   = fl;
        }

        // Remove z da lista de raizes
        z->esq->dir = z->dir;
        z->dir->esq = z->esq;

        no_de_[v] = nullptr;
        tamanho_--;

        if (tamanho_ == 0) {
            min_ = nullptr;
        } else {
            min_ = z->dir; // temporario
            consolidar();
        }

        c_.somar_bytes(-static_cast<int64_t>(sizeof(No)));
        delete z;
        return v;
    }

    void decrease_key(int v, double chave) {
        c_.decrease_key++;
        No* x = no_de_[v];
        x->chave = chave;
        No* y = x->pai;

        if (y != nullptr) {
            c_.comparacoes++; // comparacao: nova chave < chave do pai?
            if (chave < y->chave) {
                cortar(x, y);
                corte_cascata(y);
            }
        }

        c_.comparacoes++; // comparacao: nova chave < minimo atual?
        if (chave < min_->chave)
            min_ = x;
    }

    bool contem(int v) const { return no_de_[v] != nullptr; }

    bool verificar() const {
        if (min_ == nullptr) return tamanho_ == 0;
        if (tamanho_ == 0)   return false;
        int total = 0;
        return verificar_lista(min_, nullptr, total) && (total == tamanho_);
    }

private:
    int            n_;
    Contadores&    c_;
    int            tamanho_ = 0;
    No*            min_     = nullptr;
    std::vector<No*> no_de_;
    std::vector<No*> A_;
    std::vector<No*> raizes_;

    // ---- operacoes na lista circular ----

    void cortar(No* x, No* y) {
        // Remove x da lista de filhos de y
        if (x->dir == x) {
            y->filho = nullptr;
        } else {
            x->esq->dir = x->dir;
            x->dir->esq = x->esq;
            if (y->filho == x) y->filho = x->dir;
        }
        y->grau--;

        // Adiciona x na lista de raizes (antes de min_)
        No* me = min_->esq;
        me->dir   = x;
        x->esq    = me;
        x->dir    = min_;
        min_->esq = x;

        x->pai     = nullptr;
        x->marcado = false;
    }

    void corte_cascata(No* y) {
        No* z = y->pai;
        if (z != nullptr) {
            if (!y->marcado) {
                y->marcado = true;
            } else {
                cortar(y, z);
                corte_cascata(z);
            }
        }
    }

    void heap_link(No* y, No* x) {
        // y torna-se filho de x  (y.chave >= x.chave)
        y->pai     = x;
        y->marcado = false;
        y->esq     = y;
        y->dir     = y;

        if (x->filho == nullptr) {
            x->filho = y;
        } else {
            No* fc = x->filho;
            No* fl = fc->esq;
            fl->dir  = y;
            y->esq   = fl;
            y->dir   = fc;
            fc->esq  = y;
        }
        x->grau++;
    }

    void consolidar() {
        // Tamanho do array: floor(log_phi(n)) + 2
        int D = 2;
        if (tamanho_ > 1) {
            static const double LOG_PHI =
                std::log((1.0 + std::sqrt(5.0)) / 2.0);
            D = static_cast<int>(
                    std::log(static_cast<double>(tamanho_)) / LOG_PHI) + 2;
        }

        {
            std::size_t cap_ant = A_.capacity();
            A_.assign(static_cast<std::size_t>(D), nullptr);
            std::size_t cap_nova = A_.capacity();
            if (cap_nova != cap_ant)
                c_.somar_bytes(static_cast<int64_t>(cap_nova - cap_ant) * static_cast<int64_t>(sizeof(No*)));
        }

        // Coleta raizes atuais
        {
            raizes_.clear();
            std::size_t cap_ant = raizes_.capacity();
            No* x = min_;
            do { raizes_.push_back(x); x = x->dir; } while (x != min_);
            std::size_t cap_nova = raizes_.capacity();
            if (cap_nova != cap_ant)
                c_.somar_bytes(static_cast<int64_t>(cap_nova - cap_ant) * static_cast<int64_t>(sizeof(No*)));
        }

        // Desconecta cada raiz (self-loop) para reconstruir depois
        for (No* r : raizes_) { r->esq = r; r->dir = r; }

        for (No* w : raizes_) {
            No* x = w;
            int d = x->grau;

            while (d < static_cast<int>(A_.size()) &&
                   A_[static_cast<std::size_t>(d)] != nullptr) {

                No* y = A_[static_cast<std::size_t>(d)];
                if (x->chave > y->chave) std::swap(x, y);
                c_.comparacoes++; // comparacao do link
                heap_link(y, x);
                A_[static_cast<std::size_t>(d)] = nullptr;
                d++;
                if (d >= static_cast<int>(A_.size())) {
                    std::size_t cap_ant = A_.capacity();
                    A_.push_back(nullptr);
                    std::size_t cap_nova = A_.capacity();
                    if (cap_nova != cap_ant)
                        c_.somar_bytes(static_cast<int64_t>(cap_nova - cap_ant) * static_cast<int64_t>(sizeof(No*)));
                }
            }
            if (d >= static_cast<int>(A_.size())) {
                std::size_t cap_ant = A_.capacity();
                A_.resize(static_cast<std::size_t>(d) + 1, nullptr);
                std::size_t cap_nova = A_.capacity();
                if (cap_nova != cap_ant)
                    c_.somar_bytes(static_cast<int64_t>(cap_nova - cap_ant) * static_cast<int64_t>(sizeof(No*)));
            }
            A_[static_cast<std::size_t>(d)] = x;
        }

        // Reconstroi lista de raizes e acha novo minimo
        min_ = nullptr;
        for (No* r : A_) {
            if (r == nullptr) continue;
            r->esq = r; r->dir = r;
            if (min_ == nullptr) {
                min_ = r;
            } else {
                // Insere r apos min_
                No* md = min_->dir;
                min_->dir = r;
                r->esq    = min_;
                r->dir    = md;
                md->esq   = r;

                c_.comparacoes++; // 1 comparacao por raiz apos a primeira
                if (r->chave < min_->chave)
                    min_ = r;
            }
        }
    }

    void deletar_lista(No* lista) {
        // Coleta primeiro para nao ler ponteiros apos delete
        std::vector<No*> nivel;
        No* x = lista;
        do { nivel.push_back(x); x = x->dir; } while (x != lista);
        for (No* nd : nivel) {
            if (nd->filho) deletar_lista(nd->filho);
            c_.somar_bytes(-static_cast<int64_t>(sizeof(No)));
            delete nd;
        }
    }

    bool verificar_lista(No* inicio, No* pai_esp, int& total) const {
        No* x = inicio;
        do {
            total++;
            if (x->pai != pai_esp)                            return false;
            if (pai_esp && x->chave < pai_esp->chave)         return false;
            if (x->dir->esq != x || x->esq->dir != x)        return false;

            // grau == numero de filhos
            int g = 0;
            if (x->filho) {
                No* c = x->filho;
                do { ++g; c = c->dir; } while (c != x->filho);
            }
            if (g != x->grau) return false;

            // raiz nao pode ter chave menor que o minimo
            if (!pai_esp && x->chave < min_->chave) return false;

            if (x->filho && !verificar_lista(x->filho, x, total))
                return false;

            x = x->dir;
        } while (x != inicio);
        return true;
    }
};
