extern "C" {
    #include <gba_console.h>
    #include <gba_video.h>
    #include <gba_interrupt.h>
    #include <gba_systemcalls.h>
}

#include "Pokemon.h"

int main() {
    irqInit();
    irqEnable(IRQ_VBLANK);
    consoleDemoInit();

    Pokemon charmander("Charmander", "Fuego", 12, 39,
                       "Ascuas", "Arañazo", "Gruñido", "Pantalla de Humo");

    charmander.mostrar();
    charmander.usarAtaque(1);

    while (1)
        VBlankIntrWait();

    return 0;
}