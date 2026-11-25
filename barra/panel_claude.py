"""El panel que sale sobre Claudito: sesiones de Claude, límites y uso de hoy."""
import time

from PySide6.QtCore import QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QWidget

ANCHO, MARGEN, FILA, CABEZA = 290, 12, 28, 30
MAX_SESIONES = 6


def miles(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} M"
    return f"{n / 1000:.1f} k" if n >= 1000 else str(n)


def falta(cuando, ahora):
    """"2 h 10 min" hasta `cuando`, o ""."""
    if not cuando or cuando <= ahora:
        return ""
    m = int(cuando - ahora) // 60
    if m >= 1440:
        return f"{m // 1440} d {m % 1440 // 60} h"
    return f"{m // 60} h {m % 60} min" if m >= 60 else f"{m} min"


class Panel(QWidget):
    def __init__(self, al_elegir):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.al_elegir = al_elegir
        self._sesiones, self._uso, self._col, self._fuente = [], None, {}, "Segoe UI"
        self._encima, self._sitio = -1, None
        self._esconder = QTimer(self, singleShot=True, interval=260, timeout=self.hide)

    def mostrar(self, sesiones, uso, centro_x, abajo, pantalla, tema):
        self._esconder.stop()
        self._sitio = (centro_x, abajo, pantalla)
        self._col, self._fuente = tema["colores"], tema["fuente"]
        self.poner(sesiones, uso)
        self.show()

    def poner(self, sesiones, uso):
        """Datos nuevos; conserva el sitio."""
        self._sesiones, self._uso = sesiones[:MAX_SESIONES], uso
        if not self._sitio:
            return
        x, abajo, g = self._sitio
        n = max(1, len(self._sesiones))
        limites = len(uso["limites"]) if uso else 0
        alto = CABEZA + n * FILA + 10 + limites * 34 + 26
        x = round(min(max(x - ANCHO / 2, g.left() + 6), g.right() - ANCHO - 6))
        self.setGeometry(QRect(x, round(abajo - alto - 8), ANCHO, alto))
        self.update()

    def pronto(self):
        if self.isVisible():
            self._esconder.start()

    # ----- ratón -----
    def _fila(self, pos):
        i = (pos.y() - CABEZA) // FILA
        return int(i) if 0 <= i < len(self._sesiones) else -1

    def enterEvent(self, e):
        self._esconder.stop()

    def leaveEvent(self, e):
        self._encima = -1
        self.pronto()

    def mouseMoveEvent(self, e):
        i = self._fila(e.position().toPoint())
        if i != self._encima:
            self._encima = i
            self.update()

    def mousePressEvent(self, e):
        i = self._fila(e.position().toPoint())
        if i >= 0 and e.button() == Qt.MouseButton.LeftButton:
            self.hide()
            self.al_elegir(self._sesiones[i]["id"])

    # ----- dibujo -----
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = {k: QColor(v) for k, v in self._col.items()}
        fondo = c["fondo"]
        fondo.setAlpha(255)
        p.fillRect(self.rect(), fondo)
        p.setPen(QPen(c["acento"]))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        f = QFont(self._fuente)
        f.setPixelSize(12)
        negrita = QFont(f)
        negrita.setBold(True)
        dentro = QRect(MARGEN, 0, ANCHO - 2 * MARGEN, CABEZA)

        def texto(zona, t, color, fuente=f, lado=Qt.AlignmentFlag.AlignLeft):
            p.setFont(fuente)
            p.setPen(color)
            t = QFontMetrics(fuente).elidedText(t, Qt.TextElideMode.ElideRight, zona.width())
            p.drawText(zona, Qt.AlignmentFlag.AlignVCenter | lado, t)

        texto(dentro, "Sesiones de Claude", c["acento"], negrita)
        y = CABEZA
        if not self._sesiones:
            texto(QRect(MARGEN, y, dentro.width(), FILA), "No hay ninguna abierta", c["tenue"])
            y += FILA
        for i, s in enumerate(self._sesiones):
            if i == self._encima:
                p.fillRect(QRect(1, y, ANCHO - 2, FILA), c["encima"])
            urge = s["modo"] == "waiting"
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c["alerta"] if urge else c["tenue"] if s["modo"] in ("idle", "sleep") else c["acento"])
            p.drawEllipse(QRectF(MARGEN, y + FILA / 2 - 4, 8, 8))
            p.setBrush(Qt.BrushStyle.NoBrush)
            texto(QRect(MARGEN + 16, y, 124, FILA), s["proyecto"] or "Claude", c["texto"], negrita if urge else f)
            texto(QRect(ANCHO - MARGEN - 122, y, 122, FILA), s["texto"], c["alerta"] if urge else c["tenue"], f,
                  Qt.AlignmentFlag.AlignRight)
            y += FILA
        p.setPen(QPen(c["tenue"], 0.5))
        p.drawLine(MARGEN, y + 5, ANCHO - MARGEN, y + 5)
        y += 10
        ahora = time.time()
        for nombre, pct, cuando in (self._uso or {}).get("limites", []):
            zona = QRect(MARGEN, y, dentro.width(), 20)
            resto = falta(cuando, ahora)
            texto(zona.adjusted(0, 0, -48, 0), nombre + (f" · reinicia en {resto}" if resto else ""), c["tenue"])
            texto(zona, f"{pct:.0f} %", c["alerta"] if pct >= 80 else c["texto"], negrita, Qt.AlignmentFlag.AlignRight)
            p.setPen(Qt.PenStyle.NoPen)
            barra = QRectF(MARGEN, y + 22, dentro.width(), 5)
            p.setBrush(c["encima"])
            p.drawRoundedRect(barra, 2.5, 2.5)
            barra.setWidth(max(5, barra.width() * min(100, max(0, pct)) / 100))
            p.setBrush(c["alerta"] if pct >= 80 else c["acento"])
            p.drawRoundedRect(barra, 2.5, 2.5)
            p.setBrush(Qt.BrushStyle.NoBrush)
            y += 34
        pie = "Calculando el uso…" if self._uso is None else f"Hoy: {miles(self._uso['hoy'])} tokens escritos"
        texto(QRect(MARGEN, y - 2, dentro.width(), 24), pie, c["tenue"])
        p.end()
