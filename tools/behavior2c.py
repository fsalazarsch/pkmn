#!/usr/bin/env python3
"""behavior2c.py - lee assets/behavior.txt y genera source/tile_behavior.c / include/tile_behavior.h.

behavior.txt define qué hace cada pieza de tiles.png (por id de tiles_numerado.png):
    block  ...   no se puede pisar (árboles, agua, paredes)
    ledge  ...   saliente: solo se cruza saltando hacia abajo (2 casillas)
    walk   ...   caminable (sirve para corregir lo anterior)
Después de la palabra van los ids: 40   100-120   rect:c0,f0,c1,f1   water
    rect:c0,f0,c1,f1  = rectángulo de piezas (columna, fila) de la hoja, ambas esquinas incluidas
    water             = todas las piezas que son mayormente azules (agua)
Las líneas se aplican en orden: las de abajo pisan a las de arriba. '#' comenta.

Uso:  python tools/behavior2c.py          (genera también behavior_preview.png)
"""
import os, re, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
CELL = 16
CODE = {"walk": 0, "block": 1, "ledge": 2}


def die(m): print("ERROR: " + m, file=sys.stderr); sys.exit(1)


sheet_path = os.path.join(ROOT, "assets", "tiles.png")
txt_path = os.path.join(ROOT, "assets", "behavior.txt")
if not os.path.exists(txt_path): die("No encuentro " + txt_path)
a = np.array(Image.open(sheet_path).convert("RGBA"))
H, W = a.shape[:2]; ROWS, COLS = H // CELL, W // CELL; N = ROWS * COLS
t = a.reshape(ROWS, CELL, COLS, CELL, 4).swapaxes(1, 2).reshape(N, CELL, CELL, 4)


def water_ids():
    out = set()
    for i in range(N):
        px = t[i][t[i][:, :, 3] > 0][:, :3].astype(int)
        if len(px) < 128: continue
        blue = (px[:, 2] > px[:, 0] + 40) & (px[:, 2] >= px[:, 1])
        if blue.mean() > 0.5: out.add(i)
    return out


beh = np.zeros(N, dtype=np.uint8)
for n, line in enumerate(open(txt_path, encoding="utf-8"), 1):
    line = line.split("#")[0].strip()
    if not line: continue
    cmd, *args = line.split()
    if cmd not in CODE: die("línea %d: '%s' no es block, ledge ni walk." % (n, cmd))
    for tok in args:
        if tok == "water": ids = water_ids()
        elif tok.startswith("rect:"):
            c0, r0, c1, r1 = [int(v) for v in tok[5:].split(",")]
            ids = {r * COLS + c for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}
        elif re.fullmatch(r"\d+-\d+", tok): lo, hi = map(int, tok.split("-")); ids = set(range(lo, hi + 1))
        elif tok.isdigit(): ids = {int(tok)}
        else: die("línea %d: no entiendo '%s'." % (n, tok))
        for i in ids:
            if i >= N: die("línea %d: el id %d no existe (máximo %d)." % (n, i, N - 1))
            beh[i] = CODE[cmd]

with open(os.path.join(ROOT, "source", "tile_behavior.c"), "w") as f:
    f.write("// Generado por tools/behavior2c.py desde assets/behavior.txt - no editar a mano\n")
    f.write('#include "tile_behavior.h"\n\nconst unsigned char tileBehavior[TILESET_META_COUNT] =\n{\n')
    for i in range(0, N, 33): f.write("    " + ",".join(str(int(v)) for v in beh[i:i + 33]) + ",\n")
    f.write("};\n")
with open(os.path.join(ROOT, "include", "tile_behavior.h"), "w") as f:
    f.write("// Generado por tools/behavior2c.py - no editar a mano\n#ifndef TILE_BEHAVIOR_H\n#define TILE_BEHAVIOR_H\n\n")
    f.write('#include "tileset_data.h"\n\n#define BEH_WALK  0\n#define BEH_BLOCK 1\n#define BEH_LEDGE 2\n\n')
    f.write("extern const unsigned char tileBehavior[TILESET_META_COUNT];\n\n#endif\n")

ref = Image.new("RGBA", (W * 2, H * 2), (40, 40, 40, 255))
ref.alpha_composite(Image.fromarray(a, "RGBA").resize((W * 2, H * 2), Image.NEAREST))
ov = Image.new("RGBA", ref.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
for i in range(N):
    r, c = divmod(i, COLS); x, y = c * 32, r * 32
    if beh[i] == 1: d.rectangle([x, y, x + 31, y + 31], fill=(255, 0, 0, 110))
    elif beh[i] == 2: d.rectangle([x, y, x + 31, y + 31], fill=(0, 120, 255, 140))
    if beh[i]: d.text((x + 2, y + 2), str(i), fill=(255, 255, 255, 255))
ref.alpha_composite(ov); ref.save(os.path.join(ROOT, "behavior_preview.png"))
print("block: %d piezas   ledge: %d piezas   walk: %d" % ((beh == 1).sum(), (beh == 2).sum(), (beh == 0).sum()))
print("-> source/tile_behavior.c, include/tile_behavior.h, behavior_preview.png (rojo = bloquea, azul = saliente)")