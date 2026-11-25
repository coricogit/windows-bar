"""El menú de temas visual: una miniatura por tema y los ajustes a la vista."""
import time

from PySide6.QtCore import QEvent, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

MARGEN, HUECO, COLUMNAS = 16, 10, 2
TARJETA_AN, MINI_AL, NOMBRE_AL = 344, 46, 26
CHIP_AL, FILA_AL, ETIQUETA = 26, 34, 130
ANCHO = 2 * MARGEN + COLUMNAS * TARJETA_AN + HUECO


def colocar(temas, filas, interruptores, botones, medir):
    """Dónde va cada cosa: ([(QRect, tipo, datos)], alto total). `medir(texto)`
    da el ancho de un texto."""
    zonas, y = [], MARGEN + 26
    for i, t in enumerate(temas):
        x = MARGEN + (i % COLUMNAS) * (TARJETA_AN + HUECO)
        fila = y + (i // COLUMNAS) * (MINI_AL + NOMBRE_AL + HUECO)
        zonas.append((QRect(x, fila, TARJETA_AN, MINI_AL + NOMBRE_AL), "tema", t))
    y += -(-len(temas) // COLUMNAS) * (MINI_AL + NOMBRE_AL + HUECO) + 6
    for titulo, opciones in filas:
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
    for lista, tipo in ((interruptores, "chip"), (botones, "boton")):
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
        """`datos()` da {"temas", "filas", "interruptores", "botones", "colores", "fuente"}."""
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setMouseTracking(True)
        self.datos = datos
        self.cerrado = 0.0           # cuándo se cerró, para no reabrir con el mismo clic
        self._d, self._zonas, self._encima, self._minis = None, [], -1, {}
        self._sitio = None

    def abrir(self, centro_x, abajo, pantalla):
        self._sitio = (centro_x, abajo, pantalla)
        self.refrescar()
        self.show()
        self.raise_()
        self.activateWindow()

    def refrescar(self):
        self._d = self.datos()
        f = QFontMetrics(self._fuente())
        self._zonas, alto = colocar(self._d["temas"], self._d["filas"], self._d["interruptores"], self._d["botones"],
                                    f.horizontalAdvance)
        x, abajo, g = self._sitio
        x = round(min(max(x - ANCHO / 2, g.left() + 8), g.right() - ANCHO - 8))
        self.setGeometry(QRect(x, round(max(g.top() + 8, abajo - alto - 10)), ANCHO, alto))
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
        return next((i for i, (r, t, _) in enumerate(self._zonas) if t != "titulo" and r.contains(pos)), -1)

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
        p.setFont(self._fuente(14, True))
        p.setPen(c["texto"])
        p.drawText(QRect(MARGEN, MARGEN - 6, 300, 26), Qt.AlignmentFlag.AlignVCenter, "Temas")
        for i, (r, tipo, o) in enumerate(self._zonas):
            encima = i == self._encima
            if tipo == "titulo":
                p.setFont(self._fuente())
                p.setPen(c["tenue"])
                p.drawText(r, Qt.AlignmentFlag.AlignVCenter, o)
            elif tipo == "tema":
                self._tarjeta(p, r, o, c, encima)
            else:
                self._chip(p, r, o, c, encima, fondo)
        p.end()

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
