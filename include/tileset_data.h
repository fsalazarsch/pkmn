// Generado por tools/tileset2gba.py - no editar a mano
#ifndef TILESET_DATA_H
#define TILESET_DATA_H

#define TILESET_COLS 33   // metatiles por fila en tiles.png
#define TILESET_ROWS 37
#define TILESET_META_COUNT 1221   // id = fila*TILESET_COLS + columna
#define TILESET_TILE_COUNT 1832   // tiles 8x8 únicos (8bpp), el 0 es vacío
#define TILESET_TILES_LEN 117248
#define TILESET_PAL_LEN 512

extern const unsigned char  tilesetTiles[117248];
extern const unsigned short tilesetPal[256];
extern const unsigned short tilesetMeta[1221][4];

#endif
