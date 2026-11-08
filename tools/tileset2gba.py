#!/usr/bin/env python3
"""tileset2gba.py - convierte assets/tiles.png (hoja de metatiles 16x16) a C para GBA.
Uso: python tools/tileset2gba.py [assets/tiles.png]
Requiere: pip install pillow numpy"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "assets", "tiles.png")
CELL = 16
a = np.array(Image.open(src).convert("RGBA"))
H, W = a.shape[:2]
assert W % CELL == 0 and H % CELL == 0, "la hoja debe ser múltiplo de 16"
COLS, ROWS = W // CELL, H // CELL
opaque = a[:, :, 3] > 0
rgb5 = a[:, :, :3] >> 3
key = (rgb5[:, :, 0].astype(np.uint32) << 10) | (rgb5[:, :, 1].astype(np.uint32) << 5) | rgb5[:, :, 2]

# --- paleta: máximo 255 colores (0 = transparente). Si sobran, se fusionan los menos usados
vals, counts = np.unique(key[opaque], return_counts=True)
n_orig = len(vals)
def rgb(c): return np.array([(c >> 10) & 31, (c >> 5) & 31, c & 31])
order = np.argsort(-counts)
keep = [int(vals[i]) for i in order[:255]]
drop = [int(vals[i]) for i in order[255:]]
remap = {c: c for c in keep}
maxerr = 0
for c in drop:
    d = [np.abs(rgb(c) - rgb(k)).sum() for k in keep]
    j = int(np.argmin(d)); remap[c] = keep[j]; maxerr = max(maxerr, d[j])
keep.sort()
lut = {c: i + 1 for i, c in enumerate(keep)}
pal = [0] + [int(rgb(c)[0] | (rgb(c)[1] << 5) | (rgb(c)[2] << 10)) for c in keep]

idx = np.zeros(key.shape, dtype=np.uint8)
for c, r in remap.items():
    idx[(key == c) & opaque] = lut[r]

# --- tiles 8x8 únicos (tile 0 = vacío) y 4 tiles por metatile
tiles = [bytes(64)]; ids = {bytes(64): 0}
meta = []
for r in range(ROWS):
    for c in range(COLS):
        q = []
        for dy in (0, 1):
            for dx in (0, 1):
                y0, x0 = r * CELL + dy * 8, c * CELL + dx * 8
                t = idx[y0:y0 + 8, x0:x0 + 8].tobytes()
                if t not in ids: ids[t] = len(tiles); tiles.append(t)
                q.append(ids[t])
        meta.append(q)
tb = [b for t in tiles for b in t]

def arr(f, ct, name, data, per, fmt):
    f.write("const %s %s[%d] __attribute__((aligned(4))) =\n{\n" % (ct, name, len(data)))
    for i in range(0, len(data), per):
        f.write("    " + ", ".join(fmt % v for v in data[i:i + per]) + ",\n")
    f.write("};\n\n")

os.makedirs(os.path.join(ROOT, "source"), exist_ok=True); os.makedirs(os.path.join(ROOT, "include"), exist_ok=True)
with open(os.path.join(ROOT, "source", "tileset_data.c"), "w") as f:
    f.write("// Generado por tools/tileset2gba.py - no editar a mano\n#include \"tileset_data.h\"\n\n")
    arr(f, "unsigned char", "tilesetTiles", tb, 16, "0x%02X")
    arr(f, "unsigned short", "tilesetPal", pal, 8, "0x%04X")
    f.write("// Por metatile: tile de 8x8 {arriba-izq, arriba-der, abajo-izq, abajo-der}\n")
    f.write("const unsigned short tilesetMeta[%d][4] __attribute__((aligned(4))) =\n{\n" % len(meta))
    for i, q in enumerate(meta):
        f.write("    {%d, %d, %d, %d},  // id %d\n" % (*q, i))
    f.write("};\n")
with open(os.path.join(ROOT, "include", "tileset_data.h"), "w") as f:
    f.write("// Generado por tools/tileset2gba.py - no editar a mano\n#ifndef TILESET_DATA_H\n#define TILESET_DATA_H\n\n")
    f.write("#define TILESET_COLS %d   // metatiles por fila en tiles.png\n" % COLS)
    f.write("#define TILESET_ROWS %d\n#define TILESET_META_COUNT %d   // id = fila*TILESET_COLS + columna\n" % (ROWS, len(meta)))
    f.write("#define TILESET_TILE_COUNT %d   // tiles 8x8 únicos (8bpp), el 0 es vacío\n" % len(tiles))
    f.write("#define TILESET_TILES_LEN %d\n#define TILESET_PAL_LEN %d\n\n" % (len(tb), len(pal) * 2))
    f.write("extern const unsigned char  tilesetTiles[%d];\n" % len(tb))
    f.write("extern const unsigned short tilesetPal[%d];\n" % len(pal))
    f.write("extern const unsigned short tilesetMeta[%d][4];\n\n#endif\n" % len(meta))

# --- imágenes de apoyo: hoja numerada + preview de lo que verá la GBA
pv = np.zeros((H, W, 4), dtype=np.uint8)
for i, p in enumerate(pal):
    pass
P = np.array([[(p & 31) << 3, ((p >> 5) & 31) << 3, ((p >> 10) & 31) << 3, 255] for p in pal], dtype=np.uint8); P[0, 3] = 0
pv = P[idx]
Image.fromarray(pv, "RGBA").save(os.path.join(ROOT, "tiles_preview.png"))
ref = Image.new("RGBA", (W * 2, H * 2), (40, 40, 40, 255))
ref.alpha_composite(Image.fromarray(a, "RGBA").resize((W * 2, H * 2), Image.NEAREST))
d = ImageDraw.Draw(ref)
for r in range(ROWS):
    for c in range(COLS):
        x, y = c * CELL * 2, r * CELL * 2
        d.rectangle([x, y, x + 31, y + 31], outline=(255, 255, 255, 70))
        t = str(r * COLS + c); d.text((x + 2, y + 2), t, fill=(0, 0, 0, 255)); d.text((x + 1, y + 1), t, fill=(255, 255, 0, 255))
ref.save(os.path.join(ROOT, "tiles_numerado.png"))
print("hoja %dx%d px = %dx%d metatiles (%d ids, 0..%d)" % (W, H, COLS, ROWS, len(meta), len(meta) - 1))
print("colores originales: %d -> usados: %d (máx 255), error máx. por canal-suma 5bit: %d" % (n_orig, len(keep), maxerr))
print("tiles 8x8 únicos: %d  (%d bytes)" % (len(tiles), len(tb)))
