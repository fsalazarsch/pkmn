extern "C" {
    #include <gba_console.h>
}

#include "Pokemon.h"

Pokemon::Pokemon(std::string n, std::string t, int nv, int vida,
                 std::string atk1, std::string atk2, std::string atk3, std::string atk4)
    : nombre(n), tipo(t), nivel(nv), hp(vida)
{
    ataques[0] = atk1;
    ataques[1] = atk2;
    ataques[2] = atk3;
    ataques[3] = atk4;
}

void Pokemon::mostrar() const {
    iprintf("POKEMON: %s\n", nombre.c_str());
    iprintf("TIPO: %s\n", tipo.c_str());
    iprintf("NIVEL: %d\n", nivel);
    iprintf("HP: %d\n", hp);
    iprintf("ATAQUES:\n");
    for (int i = 0; i < 4; i++) {
        iprintf(" - %s\n", ataques[i].c_str());
    }
    iprintf("\n");
}

void Pokemon::usarAtaque(int i) const {
    if (i >= 0 && i < 4)
        iprintf("%s usa %s!\n", nombre.c_str(), ataques[i].c_str());
    else
        iprintf("Ataque no valido!\n");
}