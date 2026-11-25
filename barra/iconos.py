"""Los iconos de los programas, adaptados al tema.

`estilo()` describe la adaptación en un texto corto que viaja en la dirección de
la imagen ("image://iconos/nombre/3~d-…"), y `adaptar()` la aplica:

    d-AAAAAA-BBBBBB-CCCCCC   de lo oscuro a lo claro, por esos tres colores
    p-AAAAAA                 pixel art de 16 x 16 con ese contorno
"""
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from . import temas

ESTILOS = {"originales": "Originales", "tema": "Adaptados al tema"}
PIXELES = 16
PALETA = [tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) for c in (
    "17122E", "3A3F5C", "8A8FA8", "D5D9E8", "FFFFFF", "FFF4D6", "FFD23F", "FF9F43", "E8590C", "FF6B6B", "C92A3F",
    "7A1F3D", "F48FB1", "B15AC9", "6B3FA0", "7C8CF8", "1F4FA0", "74C0FC", "1BA3C6", "63E6BE", "4C9A5F", "1B6E50",
    "6E4A33", "C08A5A")]


def mezcla(a, b, cuanto):
    return tuple(x + (y - x) * cuanto for x, y in zip(a[:3], b[:3]))


def tonos(t):
    """Los tres colores del tema, de oscuro a claro, visibles sobre su fondo."""
    c = {**t["colores"], **(t["coloresClaros"] if t["clara"] else {})}
    acento, texto, acento2 = (temas.rgb(c[k]) for k in ("acento", "texto", "acento2"))
    if t["clara"] or (t["opacidad"] >= 60 and temas.luz(temas.base_de(t)) > 0.3):
        return mezcla(texto, acento, 0.2), acento[:3], mezcla(acento, (1, 1, 1), 0.68)
    return mezcla(acento, (0, 0, 0), 0.5), mezcla(acento, acento2, 0.25), mezcla(texto, (1, 1, 1), 0.45)


def tonos_bandeja(t):
    """Los de la bandeja: claros si lleva su propio fondo oscuro."""
    c = {**t["colores"], **(t["coloresClaros"] if t["clara"] else {})}
    fondo, acento = temas.rgb(c["fondoBandeja"]), temas.rgb(c["acento"])
    visto = mezcla(temas.base_de(t), fondo, fondo[3])       # con lo que deja pasar
    if fondo[3] < 0.3 or temas.luz(visto) > 0.3:
        return tonos(t)
    return tuple(mezcla(acento, (1, 1, 1), x) for x in (0.6, 0.8, 0.97))


def _hex(c):
    return "%02X%02X%02X" % tuple(max(0, min(255, round(x * 255))) for x in c[:3])


def estilo(t, cual, de=tonos):
    """El texto del estilo para ese tema, o "" con los iconos originales."""
    if cual != "tema":
        return ""
    if t["pixelado"]:
        return "~p-" + _hex(temas.rgb(t["colores"]["borde"]))
    return "~d-" + "-".join(_hex(x) for x in de(t))


def con_iconos(t, cual):
    e = estilo(t, cual)
    if not e:
        return {**t, "estiloIconos": "", "estiloBandeja": ""}
    # El pixel art, a un múltiplo exacto de su tamaño.
    tam = (PIXELES if t["compacto"] else 2 * PIXELES) if t["pixelado"] else t["icono"]
    return {**t, "estiloIconos": e, "estiloBandeja": estilo(t, cual, tonos_bandeja), "icono": tam}


def _color(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _dos_tonos(img, colores):
    img = img.convertToFormat(QImage.Format.Format_ARGB32)
    b = bytearray(img.constBits())
    luces = [(b[i + 2] * 54 + b[i + 1] * 183 + b[i] * 19) >> 8 for i in range(0, len(b), 4)]
    vistas = sorted(l for l, a in zip(luces, b[3::4]) if a > 60)
    if not vistas:
        return img
    # Cada icono usa todo el recorrido; si es de un solo tono, el del medio.
    bajo, alto = vistas[len(vistas) // 20], vistas[-1 - len(vistas) // 20]
    tabla = []
    for l in range(256):
        x = max(0.0, min(1.0, (l - bajo) / (alto - bajo))) if alto - bajo > 24 else 0.5
        a, z, f = (colores[0], colores[1], x * 2) if x < 0.5 else (colores[1], colores[2], x * 2 - 1)
        tabla.append(bytes(round(p + (q - p) * f) for p, q in zip(a[::-1], z[::-1])))
    for n, l in enumerate(luces):
        b[n * 4:n * 4 + 3] = tabla[l]
    return QImage(bytes(b), img.width(), img.height(), img.width() * 4, QImage.Format.Format_ARGB32).copy()


def _pixel_art(img, contorno):
    n = PIXELES - 2
    chica = img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied).scaled(
        n, n, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    chica = chica.convertToFormat(QImage.Format.Format_ARGB32)
    out = QImage(PIXELES, PIXELES, QImage.Format.Format_ARGB32)
    out.fill(0)
    ox, oy = (PIXELES - chica.width()) // 2, (PIXELES - chica.height()) // 2
    lleno = set()
    for y in range(chica.height()):
        for x in range(chica.width()):
            p = chica.pixel(x, y)
            if p >> 24 > 110:
                r, g, b = p >> 16 & 255, p >> 8 & 255, p & 255
                q = min(PALETA, key=lambda c: 3 * (c[0] - r) ** 2 + 4 * (c[1] - g) ** 2 + 2 * (c[2] - b) ** 2)
                out.setPixel(x + ox, y + oy, 0xFF000000 | q[0] << 16 | q[1] << 8 | q[2])
                lleno.add((x + ox, y + oy))
    borde = 0xFF000000 | contorno[0] << 16 | contorno[1] << 8 | contorno[2]
    for x, y in lleno:
        for p in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if p not in lleno and 0 <= p[0] < PIXELES and 0 <= p[1] < PIXELES:
                out.setPixel(*p, borde)
    return out


def adaptar(img, texto):
    """El icono con ese estilo; si el texto no se entiende, tal cual."""
    if img is None or img.isNull():
        return img
    if re.fullmatch(r"d(-[0-9A-F]{6}){3}", texto):
        return _dos_tonos(img, [_color(h) for h in texto.split("-")[1:]])
    if re.fullmatch(r"p-[0-9A-F]{6}", texto):
        return _pixel_art(img, _color(texto[2:]))
    return img
