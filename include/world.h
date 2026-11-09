#ifndef WORLD_H
#define WORLD_H

// Un mapa colocado dentro del mundo. ox y oy son la posición de su esquina
// superior izquierda, en casillas de 16x16, contando desde la esquina del mundo.
typedef struct
{
    const unsigned short *ground;    // &nombreGround[0][0]
    const unsigned short *objects;   // &nombreObjects[0][0]
    int w, h;                        // tamaño en casillas
    int ox, oy;                      // posición dentro del mundo
} MapPlacement;

extern const MapPlacement worldMaps[];
extern const int worldMapCount;

// Casilla donde empieza el jugador (coordenadas del mundo)
extern const int worldStartX, worldStartY;

#endif