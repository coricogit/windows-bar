"""El menú de temas visual: una miniatura por tema y los ajustes a la vista."""
import time

from PySide6.QtCore import QEvent, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

MARGEN, HUECO, COLUMNAS = 16, 10, 2
TARJETA_AN, MINI_AL, NOMBRE_AL = 344, 46, 26
CHIP_AL, FILA_AL, ETIQUETA = 26, 34, 130
ANCHO = 2 * MARGEN + COLUMNAS * TARJETA_AN + HUECO


PESTANA_AL = 30


def colocar(seccion, medir, pestanas=(), elegida=0):
    """Dónde va cada cosa: ([(QRect, tipo, datos)], alto total). `seccion` es
    {"temas", "filas", "interruptores", "botones"} (todo opcional) y
    `pestanas`, sus títulos, arriba. `medir(texto)` da el ancho de un texto."""
    zonas, y = [], MARGEN
    if pestanas:
        x = MARGEN
        for i, t in enumerate(pestanas):
            an = medir(t) + 26
            zonas.append((QRect(x, y, an, PESTANA_AL), "pestana", {"texto": t, "indice": i, "elegido": i == elegida}))
            x += an + 4
        y += PESTANA_AL + 14
    temas = seccion.get("temas", [])
    for i, t in enumerate(temas):
        x = MARGEN + (i % COLUMNAS) * (TARJETA_AN + HUECO)
        fila = y + (i // COLUMNAS) * (MINI_AL + NOMBRE_AL + HUECO)
        zonas.append((QRect(x, fila, TARJETA_AN, MINI_AL + NOMBRE_AL), "tema", t))
    if temas:
        y += -(-len(temas) // COLUMNAS) * (MINI_AL + NOMBRE_AL + HUECO) + 6
    for titulo, opciones in seccion.get("filas", []):
        if titulo.startswith("# "):              # encabezado de un bloque
            y += 4
            zonas.append((QRect(MARGEN, y, ANCHO - 2 * MARGEN, CHIP_AL), "encabezado", titulo[2:]))
            y += FILA_AL - 4
            continue
        zonas.append((QRect(MARGEN, y, ETIQUETA, CHIP_AL), "titulo", titulo))
        x = MARGEN + ETIQUETA
        for o in opciones:
            an = medir(o["texto"]) + 22
            if x + an > ANCHO - MARGEN:
                x, y = MARGEN + ETIQUETA, y + FILA_AL
            zonas.append((QRect(x, y, an, CHIP_AL), "chip", o))
            x += an + 6
        y += FILA_AL
    x, y = MARGEN, y + 4
    for lista, tipo in ((seccion.get("interruptores", []), "chip"), (seccion.get("botones", []), "boton")):
        if not lista:
            continue
        for o in lista:
            an = medir(o["texto"]) + (40 if "marcado" in o else 22)
            if x + an > ANCHO - MARGEN:
                x, y = MARGEN, y + FILA_AL
            zonas.append((QRect(x, y, an, CHIP_AL), tipo, o))
            x += an + 6
        x, y = MARGEN, y + FILA_AL
    return zonas, y + MARGEN - 6


class Selector(QWidget):
    def __init__(self, datos):
        """`datos()` da {"pestanas": [{"titulo", "temas", "filas", "interruptores",
        "botones"}], "colores", "fuente"}."""
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setMouseTracking(True)
        self.datos = datos
        self.cerrado = 0.0           # cuándo se cerró, para no reabrir con el mismo clic
        self._d, self._zonas, self._encima, self._minis = None, [], -1, {}
        self._sitio = None
        self._pestana = 0            # se recuerda mientras la barra sigue abierta

    def abrir(self, poner):
        """`poner(ancho, alto)` da la esquina."""
        self._sitio = poner
        self.refrescar()
        self.show()
        self.raise_()
        self.activateWindow()

    def refrescar(self):
        self._d = self.datos()
        f = QFontMetrics(self._fuente())
        pes = self._d["pestanas"]
        self._pestana = min(self._pestana, len(pes) - 1)
        titulos = [x["titulo"] for x in pes]
        self._zonas, _ = colocar(pes[self._pestana], f.horizontalAdvance, titulos, self._pestana)
        # El alto de la más larga: así no salta al cambiar de pestaña.
        alto = max(colocar(x, f.horizontalAdvance, titulos)[1] for x in pes)
        self.setGeometry(QRect(*self._sitio(ANCHO, alto), ANCHO, alto))
        self.update()

    def _fuente(self, px=12, negrita=False):
        f = QFont(self._d["fuente"] if self._d else "Segoe UI")
        f.setPixelSize(px)
        f.setBold(negrita)
        return f

    def soltar_memoria(self):
        self._minis.clear()

    # ----- eventos -----
    def event(self, e):
        if e.type() == QEvent.Type.WindowDeactivate:
            self.cerrado = time.monotonic()
            self.hide()
        return super().event(e)

    def hideEvent(self, e):
        self.soltar_memoria()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.hide()

    def _en(self, pos):
        return next((i for i, (r, t, _) in enumerate(self._zonas) if t not in ("titulo", "encabezado") and r.contains(pos)), -1)

    def mouseMoveEvent(self, e):
        i = self._en(e.position().toPoint())
        if i != self._encima:
            self._encima = i
            self.setCursor(Qt.CursorShape.PointingHandCursor if i >= 0 else Qt.CursorShape.ArrowCursor)
            self.update()

    def leaveEvent(self, e):
        self._encima = -1
        self.update()

    def mousePressEvent(self, e):
        i = self._en(e.position().toPoint())
        if i < 0 or e.button() != Qt.MouseButton.LeftButton:
            return
        _, tipo, o = self._zonas[i]
        if tipo == "pestana":
            self._pestana = o["indice"]
            self.refrescar()
            return
        if tipo == "boton" and o.get("cierra", True):
            self.hide()
        o["hacer"]()
        if self.isVisible():
            self.refrescar()

    # ----- dibujo -----
    def _mini(self, ruta):
        if ruta not in self._minis:
            self._minis[ruta] = QPixmap(ruta)
        return self._minis[ruta]

    def paintEvent(self, e):
        c = {k: QColor(v) for k, v in self._d["colores"].items() if v}
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        fondo = QColor(c["fondo"])
        fondo.setAlpha(255)
        p.fillRect(self.rect(), fondo)
        p.setPen(QPen(c["acento"]))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        # Debajo de las pestañas, una línea que las separa del contenido.
        p.setPen(QPen(c["tenue"], 0.6))
        p.drawLine(MARGEN, MARGEN + PESTANA_AL + 6, ANCHO - MARGEN, MARGEN + PESTANA_AL + 6)
        for i, (r, tipo, o) in enumerate(self._zonas):
            encima = i == self._encima
            if tipo == "titulo":
                p.setFont(self._fuente())
                p.setPen(c["tenue"])
                p.drawText(r, Qt.AlignmentFlag.AlignVCenter, o)
            elif tipo == "encabezado":
                p.setFont(self._fuente(12, True))
                p.setPen(c["acento"])
                p.drawText(r, Qt.AlignmentFlag.AlignVCenter, o)
            elif tipo == "pestana":
                self._pestana_dibujo(p, r, o, c, encima, fondo)
            elif tipo == "tema":
                self._tarjeta(p, r, o, c, encima)
            else:
                self._chip(p, r, o, c, encima, fondo)
        p.end()

    def _pestana_dibujo(self, p, r, o, c, encima, fondo):
        if o["elegido"] or encima:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c["acento"] if o["elegido"] else c["encima"])
            p.drawRoundedRect(QRectF(r), 8, 8)
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.setFont(self._fuente(13, o["elegido"]))
        p.setPen(fondo if o["elegido"] else c["texto"])
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, o["texto"])

    def _tarjeta(self, p, r, o, c, encima):
        caja = QRectF(r).adjusted(1, 1, -1, -1)
        forma = QPainterPath()
        forma.addRoundedRect(caja, 8, 8)
        p.save()
        p.setClipPath(forma)
        # Un fondo de escritorio neutro, para que se vean las islas.
        g = QLinearGradient(r.left(), 0, r.right(), 0)
        g.setColorAt(0, QColor("#39506E"))
        g.setColorAt(1, QColor("#6B7F9C"))
        p.fillRect(r, g)
        mini = self._mini(o["mini"])
        if not mini.isNull():
            al = TARJETA_AN * mini.height() / mini.width()
            p.drawPixmap(QRectF(r.left(), r.top() + (MINI_AL - al) / 2, TARJETA_AN, al), mini, QRectF(mini.rect()))
        pie = QRect(r.left(), r.top() + MINI_AL, r.width(), NOMBRE_AL)
        p.fillRect(pie, c["acento"] if o["marcado"] else QColor(0, 0, 0, 40 if encima else 95))
        p.restore()
        # El pie es oscuro en todos los temas, salvo en el elegido.
        sobre = QColor(c["fondo"]) if o["marcado"] else QColor("#FFFFFF")
        sobre.setAlpha(255)
        p.setFont(self._fuente(12, o["marcado"]))
        p.setPen(sobre)
        p.drawText(pie.adjusted(10, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter, o["texto"])
        p.setPen(QPen(c["acento"] if o["marcado"] or encima else c["tenue"], 2 if o["marcado"] else 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(caja, 8, 8)

    def _chip(self, p, r, o, c, encima, fondo):
        elegido, marcable = o.get("elegido", False), "marcado" in o
        p.setPen(QPen(c["acento"] if elegido or encima else c["tenue"], 1))
        p.setBrush(c["acento"] if elegido else c["encima"] if encima else Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(r).adjusted(0.5, 0.5, -0.5, -0.5), 7, 7)
        texto = r.adjusted(11, 0, -11, 0)
        if marcable:
            caja = QRectF(r.left() + 9, r.center().y() - 6, 13, 13)
            p.setPen(QPen(c["acento"] if o["marcado"] else c["tenue"], 1.2))
            p.setBrush(c["acento"] if o["marcado"] else Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(caja, 3, 3)
            if o["marcado"]:
                p.setPen(QPen(fondo, 1.8))
                p.drawPolyline([caja.topLeft() + d for d in _PALOMA])
            texto = texto.adjusted(18, 0, 11, 0)
        p.setFont(self._fuente())
        p.setPen(fondo if elegido else c["texto"])
        p.drawText(texto, Qt.AlignmentFlag.AlignVCenter, o["texto"])


def _puntos():
    from PySide6.QtCore import QPointF
    return [QPointF(3, 6.5), QPointF(5.5, 9.5), QPointF(10.2, 3.8)]


_PALOMA = _puntos()
