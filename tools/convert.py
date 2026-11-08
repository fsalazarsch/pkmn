#!/usr/bin/env python3
"""Convierte assets/route1.png y assets/player.png a C para GBA.
Uso (desde la raíz del proyecto):  python tools/convert.py
Requiere: pip install pillow
"""
from PIL import Image
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
SRC = os.path.join(ROOT, "source")
INC = os.path.join(ROOT, "include")

def bgr15(rgb):
    r, g, b = rgb
    return (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)

def write_array(f, ctype, name, data, per_line=12, fmt="0x%02X"):
    f.write("const %s %s[%d] __attribute__((aligned(4))) =\n{\n" % (ctype, name, len(data)))
    for i in range(0, len(data), per_line):
        f.write("    " + ", ".join(fmt % v for v in data[i:i + per_line]) + ",\n")
    f.write("};\n\n")

# ----------------------------------------------------------------------
# MAPA (fondo): recorta el marco del screenshot, deduplica tiles de 8x8
# ----------------------------------------------------------------------
MAP_X0, MAP_Y0, MAP_W, MAP_H = 8, 24, 384, 640   # zona útil dentro del PNG

def convert_map():
    im = Image.open(os.path.join(ASSETS, "route1.png")).convert("RGB")
    im = im.crop((MAP_X0, MAP_Y0, MAP_X0 + MAP_W, MAP_Y0 + MAP_H))

    # Paleta: índice 0 reservado (transparente en BG), colores desde 1
    colors = sorted(set(im.getdata()))
    assert len(colors) < 256
    pal = {c: i + 1 for i, c in enumerate(colors)}
    palette = [0] + [bgr15(c) for c in colors]

    tw, th = MAP_W // 8, MAP_H // 8
    tiles, tile_ids, tilemap = [], {}, []
    for ty in range(th):
        for tx in range(tw):
            t = im.crop((tx * 8, ty * 8, tx * 8 + 8, ty * 8 + 8))
            data = bytes(pal[p] for p in t.getdata())
            if data not in tile_ids:
                tile_ids[data] = len(tiles)
                tiles.append(data)
            tilemap.append(tile_ids[data])

    # Tile 0 debe ser el "vacío" (se ve en las columnas sobrantes del BG de 64x64)
    print("mapa: %dx%d tiles, %d tiles únicos, %d colores" % (tw, th, len(tiles), len(colors)))

    tile_bytes = [b for t in tiles for b in t]
    with open(os.path.join(SRC, "route1_data.c"), "w") as f:
        f.write("// Generado por tools/convert.py - no editar a mano\n")
        f.write('#include "route1_data.h"\n\n')
        write_array(f, "unsigned char", "route1Tiles", tile_bytes, 16)
        write_array(f, "unsigned short", "route1Pal", palette, 8, "0x%04X")
        write_array(f, "unsigned short", "route1Map", tilemap, 12, "%d")

    with open(os.path.join(INC, "route1_data.h"), "w") as f:
        f.write("// Generado por tools/convert.py - no editar a mano\n")
        f.write("#ifndef ROUTE1_DATA_H\n#define ROUTE1_DATA_H\n\n")
        f.write("#define ROUTE1_TILES_W %d\n#define ROUTE1_TILES_H %d\n" % (tw, th))
        f.write("#define ROUTE1_TILE_COUNT %d\n" % len(tiles))
        f.write("#define ROUTE1_TILES_LEN %d\n#define ROUTE1_PAL_LEN %d\n\n" % (len(tile_bytes), len(palette) * 2))
        f.write("extern const unsigned char  route1Tiles[%d];\n" % len(tile_bytes))
        f.write("extern const unsigned short route1Pal[%d];\n" % len(palette))
        f.write("extern const unsigned short route1Map[%d];\n\n#endif\n" % len(tilemap))

# ----------------------------------------------------------------------
# JUGADOR (sprites): hoja 3x escalada, 3 columnas x 4 filas de 16x32
# filas: 0=abajo 1=arriba 2=izquierda 3=derecha   columnas: 0,1(idle),2
# ----------------------------------------------------------------------
SCALE, FRAME_W, FRAME_H, PITCH_X, PITCH_Y = 3, 16, 32, 17, 33
BG_ORANGE = (255, 127, 39)

def convert_player():
    sheet = Image.open(os.path.join(ASSETS, "player.png")).convert("RGB")
    # Reducir 3x (tomando el pixel central de cada bloque 3x3)
    w, h = sheet.size
    small = Image.new("RGB", (w // SCALE, h // SCALE))
    for y in range(h // SCALE):
        for x in range(w // SCALE):
            small.putpixel((x, y), sheet.getpixel((x * SCALE + 1, y * SCALE + 1)))

    # Paleta de 16 colores: 0 = transparente (naranja de fondo)
    # Los blancos de las líneas de la rejilla se ignoran al recortar cada frame.
    colors = sorted(set(small.getdata()) - {BG_ORANGE})
    if len(colors) > 15:
        raise SystemExit("El sprite tiene %d colores, máximo 15" % len(colors))
    pal = {c: i + 1 for i, c in enumerate(colors)}
    pal[BG_ORANGE] = 0
    palette = [0] + [bgr15(c) for c in colors]
    palette += [0] * (16 - len(palette))

    out = []
    for row in range(4):
        for col in range(3):
            x0, y0 = col * PITCH_X, row * PITCH_Y -1
            for ty in range(FRAME_H // 8):          # orden de tiles OBJ_1D_MAP:
                for tx in range(FRAME_W // 8):      # de izq. a der., arriba a abajo
                    for y in range(8):
                        for x in range(0, 8, 2):    # 4bpp: 2 pixeles por byte
                            px = []
                            for dx in (0, 1):
                                xx, yy = x0 + tx * 8 + x + dx, y0 + ty * 8 + y
                                if 0 <= yy < small.size[1] and xx < small.size[0]:
                                    px.append(pal.get(small.getpixel((xx, yy)), 0))
                                else:
                                    px.append(0)
                            out.append(px[0] | (px[1] << 4))
    print("jugador: 12 frames de 16x32, %d bytes, %d colores" % (len(out), len(colors)))

    with open(os.path.join(SRC, "player_data.c"), "w") as f:
        f.write("// Generado por tools/convert.py - no editar a mano\n")
        f.write('#include "player_data.h"\n\n')
        write_array(f, "unsigned char", "playerTiles", out, 16)
        write_array(f, "unsigned short", "playerPal", palette, 8, "0x%04X")

    with open(os.path.join(INC, "player_data.h"), "w") as f:
        f.write("// Generado por tools/convert.py - no editar a mano\n")
        f.write("#ifndef PLAYER_DATA_H\n#define PLAYER_DATA_H\n\n")
        f.write("#define PLAYER_FRAME_TILES 8   // 16x32 a 4bpp = 8 tiles de 8x8\n")
        f.write("#define PLAYER_TILES_LEN %d\n\n" % len(out))
        f.write("extern const unsigned char  playerTiles[%d];\n" % len(out))
        f.write("extern const unsigned short playerPal[16];\n\n#endif\n")

if __name__ == "__main__":
    convert_map()
    convert_player()
