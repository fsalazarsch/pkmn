// El mundo: aquí se colocan los mapas y se define cómo se unen.
//
// Cada mapa va en la posición (ox, oy) del mundo, en casillas. Dos mapas quedan
// conectados cuando sus bordes se tocan: no hace falta nada más. Caminar de uno
// a otro es continuo, sin cargas ni pantallas intermedias.
//
// Reglas: todo el mundo debe caber en 32 casillas de ancho (ox + w <= 32).
//
// Para agregar un mapa: incluye su .h y añade una línea a worldMaps.
#include "world.h"
#include "route1_map.h"
#include "pallet_town_map.h"

const MapPlacement worldMaps[] =
{
    //  suelo                    objetos                    ancho            alto             ox  oy
    { &route1Ground[0][0],       &route1Objects[0][0],       ROUTE1_W,        ROUTE1_H,        0,  0        },
    { &pallet_townGround[0][0],  &pallet_townObjects[0][0],  PALLET_TOWN_W,   PALLET_TOWN_H,   0,  ROUTE1_H },  // justo debajo de route1
};

const int worldMapCount = sizeof(worldMaps) / sizeof(worldMaps[0]);

// Inicio del jugador: en Pallet Town, centrado y 3 casillas sobre su borde de abajo.
// Si cae sobre algo que bloquea, cambia estos números.
const int worldStartX = PALLET_TOWN_W / 2;
const int worldStartY = ROUTE1_H + PALLET_TOWN_H - 3;