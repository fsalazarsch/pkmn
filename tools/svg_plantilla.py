#!/usr/bin/env python3
# Crea maps/plantilla.svg a partir de assets/tiles.png (piezas de 16x16)
#   python tools/svg_plantilla.py [ancho_casillas] [alto_casillas]
import os, sys
from PIL import Image
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = int(sys.argv[1]) if len(sys.argv) > 1 else 32
H = int(sys.argv[2]) if len(sys.argv) > 2 else 32
hoja = Image.open(os.path.join(RAIZ, "assets", "tiles.png")).convert("RGBA")
cols, filas = hoja.width // 16, hoja.height // 16
usadas = [t for t in range(cols * filas)
          if hoja.crop(((t % cols) * 16, (t // cols) * 16, (t % cols) * 16 + 16, (t // cols) * 16 + 16)).getchannel("A").getbbox()]

o = []
o.append('<?xml version="1.0" encoding="UTF-8"?>')
o.append('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"'
         ' xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"'
         ' width="%d" height="%d" viewBox="0 0 %d %d" data-casillas-w="%d" data-casillas-h="%d">'
         % (W * 16, H * 16, W * 16, H * 16, W, H))
o.append('  <defs>')
o.append('    <image id="hoja" width="%d" height="%d" style="image-rendering:pixelated" xlink:href="../assets/tiles.png"/>'
         % (hoja.width, hoja.height))
for t in usadas:
    o.append('    <symbol id="t%d" viewBox="%d %d 16 16" width="16" height="16"><use xlink:href="#hoja"/></symbol>'
             % (t, (t % cols) * 16, (t // cols) * 16))
o.append('    <pattern id="rejilla" width="16" height="16" patternUnits="userSpaceOnUse">'
         '<path d="M16 0H0V16" fill="none" stroke="#000" stroke-opacity=".25" stroke-width=".5"/></pattern>')
o.append('  </defs>')
o.append('  <rect width="100%" height="100%" fill="#7fb4e8"/>')
# Capas del mapa (de abajo hacia arriba). Cada pieza: <use xlink:href="#tN" x= y=> con x,y multiplos de 16
for n in (1, 2, 3):
    o.append('  <g id="capa%d" inkscape:groupmode="layer" inkscape:label="capa%d">' % (n, n))
    if n == 1:
        o.append('    <!-- ejemplo: <use xlink:href="#t0" x="0" y="0"/> -->')
    o.append('  </g>')
o.append('  <rect width="100%" height="100%" fill="url(#rejilla)" pointer-events="none"/>')
# Hoja de piezas: copiala (clon) hacia las capas. Fuera del mapa, a la derecha.
o.append('  <g id="piezas" inkscape:groupmode="layer" inkscape:label="piezas (copiar de aqui)" transform="translate(%d,0)">' % (W * 16 + 32))
for t in usadas:
    o.append('    <use id="p%d" xlink:href="#t%d" x="%d" y="%d"/>' % (t, t, (t % cols) * 16, (t // cols) * 16))
o.append('  </g>')
o.append('</svg>')
ruta = os.path.join(RAIZ, "maps", "plantilla.svg")
open(ruta, "w", encoding="utf-8").write("\n".join(o) + "\n")
print("Listo: maps/plantilla.svg  (%d piezas, mapa %dx%d casillas)" % (len(usadas), W, H))