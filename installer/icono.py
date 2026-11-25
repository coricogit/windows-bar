"""icono.py <salida.ico>: el icono de la barra, una pantalla con una isla abajo."""
import struct
import sys

from PySide6.QtCore import QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter

app = QGuiApplication([])


def dibujar(n):
    img = QImage(n, n, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.scale(n / 64, n / 64)
    g = QLinearGradient(0, 0, 64, 64)
    g.setColorAt(0, QColor("#5B6EE1"))
    g.setColorAt(1, QColor("#BB9AF7"))
    p.setBrush(g)
    p.drawRoundedRect(QRectF(2, 2, 60, 60), 14, 14)
    p.setBrush(QColor("#1A1B26"))
    p.drawRoundedRect(QRectF(8, 38, 48, 18), 8, 8)
    for x, c in ((14, "#7AA2F7"), (28, "#9ECE6A"), (42, "#F7768E")):
        p.setBrush(QColor(c))
        p.drawRoundedRect(QRectF(x, 43, 8, 8), 2.5, 2.5)
    p.end()
    return img


imagenes = []
for n in (16, 32, 48, 64, 128, 256):
    b = QBuffer()
    b.open(QIODevice.OpenModeFlag.WriteOnly)
    dibujar(n).save(b, "PNG")
    imagenes.append((n, bytes(b.data())))
donde = 6 + 16 * len(imagenes)
cabeza = struct.pack("<HHH", 0, 1, len(imagenes))
for n, datos in imagenes:
    cabeza += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(datos), donde)
    donde += len(datos)
with open(sys.argv[1], "wb") as f:
    f.write(cabeza + b"".join(d for _, d in imagenes))
