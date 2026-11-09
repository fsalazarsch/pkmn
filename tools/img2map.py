#!/usr/bin/env python3
"""img2map.py - convierte una imagen (BMP/PNG) de un mapa en route1_map.c / route1_map.h.

Compara cada casilla de 16x16 de la imagen con las piezas de assets/tiles.png y escribe los ids.
Si una casilla es "pieza transparente sobre suelo" (un árbol sobre pasto), la separa en
suelo + objeto. Lo que no es exacto se reporta para que lo revises a mano.

Uso:
    python tools/img2map.py assets/route1.bmp
    python tools/img2map.py assets/route1.bmp --name route2 --crop 8,24,384,640 --preview prev.png
Requiere: pip install pillow numpy
"""
import argparse, os, re, shutil, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
CELL = 16
PENALTY = 24          # preferir "solo suelo" salvo que el objeto mejore claramente el parecido


def die(msg):
    print("ERROR: " + msg, file=sys.stderr); sys.exit(1)


def load_sheet(path):
    if not os.path.exists(path): die("No encuentro la hoja de tiles: " + path)
    a = np.array(Image.open(path).convert("RGBA"))
    h, w = a.shape[:2]
    if w % CELL or h % CELL: die("La hoja debe medir un múltiplo de 16 px.")
    rows, cols = h // CELL, w // CELL
    t = a.reshape(rows, CELL, cols, CELL, 4).swapaxes(1, 2).reshape(rows * cols, CELL, CELL, 4)
    opaque = t[:, :, :, 3] > 0
    full, none = opaque.all((1, 2)), ~opaque.any((1, 2))
    part = ~full & ~none

    def dedupe(mask):               # se queda con el primer id de cada pieza repetida
        seen, ids = set(), []
        for i in np.where(mask)[0]:
            k = t[i].tobytes()
            if k not in seen: seen.add(k); ids.append(int(i))
        return np.array(ids)
    gid, oid = dedupe(full), dedupe(part)
    G = t[gid][:, :, :, :3].reshape(len(gid), CELL * CELL, 3).astype(np.int16)
    O = t[oid][:, :, :, :3].reshape(len(oid), CELL * CELL, 3).astype(np.int16)
    M = opaque[oid].reshape(len(oid), CELL * CELL)
    return gid, G, oid, O, M, t


def load_image(path, crop, scale):
    im = Image.open(path).convert("RGB")
    if crop:
        x, y, w, h = crop; im = im.crop((x, y, x + w, y + h))
    if scale > 1:                   # imagen ampliada N veces: toma el pixel central de cada bloque
        a = np.array(im); im = Image.fromarray(a[scale // 2::scale, scale // 2::scale])
    return np.array(im)


def check_grid(arr):
    h, w = arr.shape[:2]
    if w % CELL or h % CELL:
        die("La imagen mide %dx%d y debe ser múltiplo de 16. Usa --crop x,y,ancho,alto, "
            "o prueba --auto-crop para que el script busque el desfase." % (w, h))


def auto_crop(arr, G):
    """Prueba todos los desfases posibles y se queda con el que más pixeles calza con la hoja de tiles."""
    H, W = arr.shape[:2]
    cols, rows = W // CELL, H // CELL
    if cols == 0 or rows == 0: die("La imagen es más chica que una casilla de 16x16.")
    pos = [(i, j) for j in range(rows) for i in range(cols)]
    pos = pos[::max(1, len(pos) // 60)]                 # unas 60 casillas de muestra
    best = None
    for dy in range(H - rows * CELL + 1):
        for dx in range(W - cols * CELL + 1):
            score = 0
            for i, j in pos:
                c = arr[dy + j * CELL: dy + (j + 1) * CELL, dx + i * CELL: dx + (i + 1) * CELL]
                c = c.reshape(CELL * CELL, 3).astype(np.int16)
                score += int((np.abs(G - c).sum(2) == 0).sum(1).max())
            if best is None or score > best[0]: best = (score, dx, dy)
    ratio = best[0] / (len(pos) * CELL * CELL)
    return best[1], best[2], cols * CELL, rows * CELL, ratio


def match_cell(cell, gid, G, oid, O, M):
    c = cell.reshape(CELL * CELL, 3).astype(np.int16)
    eg = np.abs(G - c).sum(2)                         # error por pixel contra cada suelo
    tot = eg.sum(1)
    g = int(tot.argmin())
    best = (int(tot[g]), int(gid[g]), 0)
    if best[0] == 0 or len(oid) == 0: return best
    eo = (np.abs(O - c).sum(2) * M).sum(1)            # error del objeto (solo donde es opaco)
    ge = (~M).astype(np.int32) @ eg.T.astype(np.int32)  # error del suelo donde el objeto es transparente
    tot2 = eo[:, None] + ge                           # todas las combinaciones objeto x suelo
    o, g = np.unravel_index(int(tot2.argmin()), tot2.shape)
    if tot2[o, g] + PENALTY < best[0]: best = (int(tot2[o, g]), int(gid[g]), int(oid[o]))
    return best


def write_c(name, w, h, ground, objects, src_dir, inc_dir):
    up = name.upper()
    os.makedirs(src_dir, exist_ok=True); os.makedirs(inc_dir, exist_ok=True)
    cpath, hpath = os.path.join(src_dir, name + "_map.c"), os.path.join(inc_dir, name + "_map.h")
    for p in (cpath, hpath):
        if os.path.exists(p): shutil.copy(p, p + ".bak")        # por si habías editado a mano
    def grid(sym, g):
        s = "const unsigned short %s[%s_H][%s_W] =\n{\n" % (sym, up, up)
        for y in range(h): s += "    {" + ",".join("%4d" % v for v in g[y]) + "},  // fila %d\n" % y
        return s + "};\n"
    with open(cpath, "w") as f:
        f.write('// Generado por tools/img2map.py (puedes seguir editándolo a mano)\n#include "%s_map.h"\n\n' % name)
        f.write("// SUELO: debajo de todo. 0 se ve negro.\n" + grid(name + "Ground", ground))
        f.write("\n// OBJETOS: encima del suelo. 0 = nada.\n" + grid(name + "Objects", objects))
    with open(hpath, "w") as f:
        f.write("#ifndef %s_MAP_H\n#define %s_MAP_H\n\n#define %s_W %d\n#define %s_H %d\n\n" % (up, up, up, w, up, h))
        f.write("extern const unsigned short %sGround[%s_H][%s_W];\n" % (name, up, up))
        f.write("extern const unsigned short %sObjects[%s_H][%s_W];\n\n#endif\n" % (name, up, up))
    return cpath, hpath


def main():
    ap = argparse.ArgumentParser(description="imagen de mapa -> ids de tiles.png")
    ap.add_argument("image")
    ap.add_argument("--tileset", default=os.path.join(ROOT, "assets", "tiles.png"))
    ap.add_argument("--name", help="nombre de los símbolos (por defecto, el del archivo)")
    ap.add_argument("--crop", help="x,y,ancho,alto de la zona útil de la imagen")
    ap.add_argument("--auto-crop", action="store_true", help="busca solo el desfase de la grilla de 16x16")
    ap.add_argument("--scale", type=int, default=1, help="si la imagen está ampliada N veces")
    ap.add_argument("--tol", type=float, default=4.0, help="error medio (0-255) sobre el cual se avisa")
    ap.add_argument("--preview", help="guarda un PNG con el resultado y las casillas dudosas en rojo")
    ap.add_argument("--out-src", default=os.path.join(ROOT, "source"))
    ap.add_argument("--out-inc", default=os.path.join(ROOT, "include"))
    a = ap.parse_args()

    name = re.sub(r"\W", "_", a.name or os.path.splitext(os.path.basename(a.image))[0])
    if not name or name[0].isdigit(): die("'%s' no sirve como nombre de C." % name)
    crop = tuple(int(v) for v in a.crop.split(",")) if a.crop else None

    img = load_image(a.image, crop, a.scale)
    gid, G, oid, O, M, tiles = load_sheet(a.tileset)
    if a.auto_crop:
        x, y, w, h, ratio = auto_crop(img, G)
        print("auto-crop: --crop %d,%d,%d,%d  (%.0f%% de los pixeles calzan con la hoja)" % (x, y, w, h, ratio * 100))
        if ratio < 0.5:
            print("  AVISO: calza poco; puede que la imagen tenga marco o piezas que no están en tiles.png")
        img = img[y:y + h, x:x + w]
    check_grid(img)
    H, W = img.shape[0] // CELL, img.shape[1] // CELL
    if W > 32: die("El mapa mide %d casillas de ancho y el máximo es 32." % W)

    ground = np.zeros((H, W), dtype=int); objects = np.zeros((H, W), dtype=int)
    errs = np.zeros((H, W)); cache = {}
    for y in range(H):
        for x in range(W):
            cell = img[y * CELL:(y + 1) * CELL, x * CELL:(x + 1) * CELL]
            k = cell.tobytes()
            if k not in cache: cache[k] = match_cell(cell, gid, G, oid, O, M)
            e, g, o = cache[k]
            ground[y, x], objects[y, x], errs[y, x] = g, o, e / (CELL * CELL * 3)

    cpath, hpath = write_c(name, W, H, ground, objects, a.out_src, a.out_inc)
    bad = [(errs[y, x], x, y) for y in range(H) for x in range(W) if errs[y, x] > a.tol]
    print("%s: %dx%d casillas (%dx%d px), %d casillas distintas" % (name, W, H, W * CELL, H * CELL, len(cache)))
    print("  con objeto encima del suelo: %d" % int((objects > 0).sum()))
    print("  -> %s  y  %s" % (cpath, hpath))
    if bad:
        bad.sort(reverse=True)
        print("AVISO: %d casillas no coinciden bien (error medio > %.1f). Peores (columna,fila):" % (len(bad), a.tol))
        print("  " + ", ".join("(%d,%d)=%.1f" % (x, y, e) for e, x, y in bad[:12]))
    else:
        print("  todas las casillas coinciden con la hoja de tiles")

    if a.preview:
        out = np.zeros((H * CELL, W * CELL, 3), dtype=np.uint8)
        for y in range(H):
            for x in range(W):
                for i in (ground[y, x], objects[y, x]):
                    if i == 0: continue
                    t = tiles[i]; m = t[:, :, 3] > 0
                    out[y * CELL:(y + 1) * CELL, x * CELL:(x + 1) * CELL][m] = t[:, :, :3][m]
        pv = Image.fromarray(out); d = ImageDraw.Draw(pv)
        for e, x, y in bad: d.rectangle([x * CELL, y * CELL, x * CELL + 15, y * CELL + 15], outline=(255, 0, 0))
        pv.save(a.preview); print("  preview: " + a.preview)


if __name__ == "__main__":
    main()