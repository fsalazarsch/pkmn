#!/usr/bin/env python3
# map2gba.py: mapa en texto + assets/tiles.png -> source/NOMBRE_data.c e include/NOMBRE_data.h
#   python tools/map2gba.py --guia              crea assets/guia.png con el numero de cada pieza
#   python tools/map2gba.py maps/prueba.txt     convierte el mapa
import argparse, os, re, sys
from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_ANCHO, MAX_TILES, MAX_COLORES = 32, 895, 255   # casillas, tiles de 8x8, colores


def error(msg):
    sys.exit("ERROR: " + msg)


def guia(hoja, salida):
    cols, E = hoja.width // 16, 3
    g = Image.new("RGBA", hoja.size, (255, 0, 255, 255))
    g.alpha_composite(hoja)
    g = g.resize((hoja.width * E, hoja.height * E), Image.NEAREST)
    d = ImageDraw.Draw(g)
    for t in range(cols * (hoja.height // 16)):
        fy, fx = divmod(t, cols)
        if hoja.crop((fx * 16, fy * 16, fx * 16 + 16, fy * 16 + 16)).getchannel("A").getbbox():
            x, y = fx * 16 * E, fy * 16 * E
            d.rectangle((x, y, x + 16 * E - 1, y + 16 * E - 1), outline=(255, 255, 255, 255))
            d.text((x + 3, y + 3), str(t), fill=(0, 0, 0, 255))
            d.text((x + 2, y + 2), str(t), fill=(255, 255, 0, 255))
    g.convert("RGB").save(salida)


def leer_mapa(ruta):
    """Capas separadas por una linea en blanco. Cada celda: numero de pieza, o '.' si va vacia."""
    capas, actual = [], []
    for linea in open(ruta, encoding="utf-8").read().splitlines() + [""]:
        linea = linea.split("#")[0].strip()
        if linea:
            actual.append(linea.split())
        elif actual:
            capas.append(actual)
            actual = []
    if not capas:
        error("El mapa esta vacio")
    h, w = len(capas[0]), len(capas[0][0])
    for c in capas:
        if len(c) != h or any(len(f) != w for f in c):
            error("Todas las filas y capas deben tener el mismo largo")
    return w, h, [[[None if t == "." else int(t) for t in f] for f in c] for c in capas]


def componer(w, h, capas, hoja):
    cols, filas = hoja.width // 16, hoja.height // 16
    lienzo = Image.new("RGBA", (w * 16, h * 16), (0, 0, 0, 0))
    meta = [[0] * w for _ in range(h)]                  # pieza de arriba +1 (0 = nada)
    for capa in capas:                                  # la primera capa queda abajo
        for y in range(h):
            for x in range(w):
                t = capa[y][x]
                if t is None:
                    continue
                if not 0 <= t < cols * filas:
                    error("La pieza %d no existe en la hoja (fila %d, col %d)" % (t, y + 1, x + 1))
                fy, fx = divmod(t, cols)
                lienzo.alpha_composite(hoja.crop((fx * 16, fy * 16, fx * 16 + 16, fy * 16 + 16)), (x * 16, y * 16))
                meta[y][x] = t + 1
    return lienzo, meta


def convertir(lienzo, w, h):
    px = lienzo.load()
    W, H = lienzo.size
    indice = [[0] * W for _ in range(H)]                # 0 = transparente
    colores = {}
    for y in range(H):
        for x in range(W):
            r, g, b, a = px[x, y]
            if a:
                c = (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)       # color de 15 bits de la GBA
                indice[y][x] = colores.setdefault(c, len(colores) + 1)
    if len(colores) > MAX_COLORES:
        error("El mapa usa %d colores y el maximo es %d" % (len(colores), MAX_COLORES))
    paleta = [0] + list(colores)
    huecos = [(x, y) for y in range(h) for x in range(w)
              if any(px[x * 16 + i, y * 16 + j][3] == 0 for j in range(16) for i in range(16))]
    tiles, vistos, mapa = [], {}, []                    # tiles de 8x8 sin repetidos
    for ty in range(h * 2):
        for tx in range(w * 2):
            t = bytes(indice[ty * 8 + j][tx * 8 + i] for j in range(8) for i in range(8))
            if t not in vistos:
                vistos[t] = len(tiles)
                tiles.append(t)
            mapa.append(vistos[t])
    return tiles, mapa, paleta, huecos


def arreglo(f, tipo, nombre, datos, por_linea, fmt):
    f.write("const %s %s[%d] __attribute__((aligned(4))) =\n{\n" % (tipo, nombre, len(datos)))
    for i in range(0, len(datos), por_linea):
        f.write("    " + ", ".join(fmt % v for v in datos[i:i + por_linea]) + ",\n")
    f.write("};\n\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mapa", nargs="?", help="archivo de texto con el mapa")
    ap.add_argument("--guia", action="store_true", help="crea assets/guia.png")
    ap.add_argument("--hoja", default=os.path.join(RAIZ, "assets", "tiles.png"))
    ap.add_argument("--nombre", help="nombre de los simbolos C (por defecto, el del archivo)")
    a = ap.parse_args()
    hoja = Image.open(a.hoja).convert("RGBA")
    if hoja.width % 16 or hoja.height % 16:
        error("La hoja debe medir un multiplo de 16 px")
    if a.guia:
        guia(hoja, os.path.join(RAIZ, "assets", "guia.png"))
        return print("Listo: assets/guia.png")
    if not a.mapa:
        error("Falta el mapa. Ejemplo: python tools/map2gba.py maps/prueba.txt")

    nombre = re.sub(r"\W", "_", a.nombre or os.path.splitext(os.path.basename(a.mapa))[0])
    up = nombre.upper()
    w, h, capas = leer_mapa(a.mapa)
    if w > MAX_ANCHO:
        error("El mapa mide %d casillas de ancho y el maximo es %d" % (w, MAX_ANCHO))
    lienzo, meta = componer(w, h, capas, hoja)
    tiles, mapa, paleta, huecos = convertir(lienzo, w, h)
    if len(tiles) > MAX_TILES:
        error("El mapa usa %d tiles de 8x8 distintos y el maximo es %d" % (len(tiles), MAX_TILES))
    datos = [b for t in tiles for b in t]

    with open(os.path.join(RAIZ, "source", nombre + "_data.c"), "w") as f:
        f.write('// Generado por tools/map2gba.py\n#include "%s_data.h"\n\n' % nombre)
        arreglo(f, "unsigned char", nombre + "Tiles", datos, 16, "0x%02X")
        arreglo(f, "unsigned short", nombre + "Pal", paleta, 8, "0x%04X")
        arreglo(f, "unsigned short", nombre + "Map", mapa, 12, "%d")
        arreglo(f, "unsigned short", nombre + "Meta", [v for fila in meta for v in fila], 12, "%d")
    with open(os.path.join(RAIZ, "include", nombre + "_data.h"), "w") as f:
        f.write("// Generado por tools/map2gba.py\n#ifndef %s_DATA_H\n#define %s_DATA_H\n\n" % (up, up))
        f.write("#define %s_TILES_W %d\n#define %s_TILES_H %d\n" % (up, w * 2, up, h * 2))
        f.write("#define %s_META_W %d\n#define %s_META_H %d\n" % (up, w, up, h))
        f.write("#define %s_TILE_COUNT %d\n#define %s_TILES_LEN %d\n#define %s_PAL_LEN %d\n\n"
                % (up, len(tiles), up, len(datos), up, len(paleta) * 2))
        f.write("extern const unsigned char  %sTiles[%d];\n" % (nombre, len(datos)))
        f.write("extern const unsigned short %sPal[%d];\n" % (nombre, len(paleta)))
        f.write("extern const unsigned short %sMap[%d];\n" % (nombre, len(mapa)))
        f.write("extern const unsigned short %sMeta[%d];\n\n#endif\n" % (nombre, w * h))

    print("%s: %dx%d casillas, %d capas, %d tiles de 8x8, %d colores"
          % (nombre, w, h, len(capas), len(tiles), len(paleta) - 1))
    if huecos:
        print("AVISO: %d casillas tienen pixeles sin cubrir (se veran negros): %s"
              % (len(huecos), ", ".join("(%d,%d)" % p for p in huecos[:8])))


if __name__ == "__main__":
    main()