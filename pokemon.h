#pragma once
#include <string>

class Pokemon {
private:
    std::string nombre;
    std::string tipo;
    int nivel;
    int hp;
    std::string ataques[4];

public:
    Pokemon(std::string n, std::string t, int nv, int vida,
            std::string atk1, std::string atk2, std::string atk3, std::string atk4);

    void mostrar() const;
    void usarAtaque(int i) const;
};