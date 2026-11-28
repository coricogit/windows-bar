"""El calendario que sale al pulsar el reloj, con los colores del tema."""
import datetime
import time

from PySide6.QtCore import QLocale, QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QWidget

ANCHO, MARGEN, CABEZA, DIAS, CELDA, PIE = 300, 14, 44, 26, 36, 38
ALTO = CABEZA + DIAS + 6 * CELDA + 8 + PIE


def cuadricula(anio, mes, primero=0):
    """Las 42 fechas que se ven de ese mes; la semana empieza en `primero`
    (0 lunes ... 6 domingo)."""
    uno = datetime.date(anio, mes, 1)
    desde = uno - datetime.timedelta(days=(uno.weekday() - primero) % 7)
    return [desde + datetime.timedelta(days=i) for i in range(42)]


def mover(anio, mes, paso):
    n = anio * 12 + (mes - 1) + paso
    return n // 12, n % 12 + 1


class Calendario(QWidget):
    def __init__(self, al_avisos):
        # Popup: se cierra solo al pulsar fuera, como los menús.
        super().__init__(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.NoDropShadowWindowHint)
        self.al_avisos = al_avisos
        self._col, self._fuente = {}, "Segoe UI"
        self._loc = QLocale.system()
        self._primero = (self._loc.firstDayOfWeek().value - 1) % 7      # Qt: lunes = 1
        hoy = datetime.date.today()
        self._anio, self._mes = hoy.year, hoy.month
        self._encima = None
        self.cerrado = 0.0
        self.setMouseTracking(True)

    def hideEvent(self, e):
        self.cerrado = time.monotonic()
        super().hideEvent(e)

    def mostrar(self, poner, tema, escala=1.0):
        """`escala`: el «Tamaño del texto» de Windows; crece todo junto (WCAG 1.4.4)."""
        hoy = datetime.date.today()
        self._anio, self._mes = hoy.year, hoy.month
        self._col, self._fuente = tema["colores"], tema["fuente"]
        self._esc = max(1.0, min(2.0, escala))
        an, al = round(ANCHO * self._esc), round(ALTO * self._esc)
        self.setGeometry(QRect(*poner(an, al), an, al))
        self.show()

    def _punto(self, e):
        """Dónde está el ratón en el dibujo sin escalar."""
        esc = getattr(self, "_esc", 1.0)
        p = e.position()
        return QPoint(round(p.x() / esc), round(p.y() / esc))

    # ----- zonas -----
    @staticmethod
    def _flecha(pos):
        if pos.y() < CABEZA:
            if pos.x() > ANCHO - MARGEN - 30:
                return "sig"
            if pos.x() > ANCHO - MARGEN - 62:
                return "ant"
            return "hoy"
        if pos.y() > ALTO - PIE:
            return "avisos"
        return None

    def mouseMoveEvent(self, e):
        z = self._flecha(self._punto(e))
        if z != self._encima:
            self._encima = z
            self.update()

    def leaveEvent(self, e):
        self._encima = None
        self.update()

    def mousePressEvent(self, e):
        if not self.rect().contains(e.position().toPoint()):
            self.hide()
            return
        z = self._flecha(self._punto(e))
        if z in ("ant", "sig"):
            self._anio, self._mes = mover(self._anio, self._mes, -1 if z == "ant" else 1)
        elif z == "hoy":
            hoy = datetime.date.today()
            self._anio, self._mes = hoy.year, hoy.month
        elif z == "avisos":
            self.hide()
            self.al_avisos()
            return
        self.update()

    def wheelEvent(self, e):
        self._anio, self._mes = mover(self._anio, self._mes, -1 if e.angleDelta().y() > 0 else 1)
        self.update()

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key.Key_Escape:
            self.hide()
        elif k in (Qt.Key.Key_Left, Qt.Key.Key_PageUp, Qt.Key.Key_Right, Qt.Key.Key_PageDown):
            self._anio, self._mes = mover(self._anio, self._mes, -1 if k in (Qt.Key.Key_Left, Qt.Key.Key_PageUp) else 1)
            self.update()

    # ----- dibujo -----
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(getattr(self, "_esc", 1.0), getattr(self, "_esc", 1.0))
        todo = QRect(0, 0, ANCHO, ALTO)
        c = {k: QColor(v) for k, v in self._col.items()}
        fondo = QColor(c.get("fondo", QColor("#202020")))
        fondo.setAlpha(255)
        p.fillRect(todo, fondo)
        p.setPen(QPen(c["acento"]))
        p.drawRect(todo.adjusted(0, 0, -1, -1))
        f = QFont(self._fuente)
        f.setPixelSize(13)
        negrita = QFont(f)
        negrita.setBold(True)
        negrita.setPixelSize(15)
        pequena = QFont(f)
        pequena.setPixelSize(11)
        centro = Qt.AlignmentFlag.AlignCenter

        def zona_encima(z, r):
            if self._encima == z:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c["encima"])
                p.drawRoundedRect(QRectF(r), 6, 6)
                p.setBrush(Qt.BrushStyle.NoBrush)

        # cabecera: mes y flechas
        mes = self._loc.standaloneMonthName(self._mes, QLocale.FormatType.LongFormat)
        titulo = f"{mes[:1].upper()}{mes[1:]} {self._anio}"
        r_hoy = QRect(MARGEN - 6, 8, ANCHO - 2 * MARGEN - 60, CABEZA - 14)
        zona_encima("hoy", r_hoy)
        p.setFont(negrita)
        p.setPen(c["texto"])
        p.drawText(r_hoy.adjusted(6, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, titulo)
        for z, x, t in (("ant", ANCHO - MARGEN - 62, "‹"), ("sig", ANCHO - MARGEN - 30, "›")):
            r = QRect(x, 8, 30, CABEZA - 14)
            zona_encima(z, r)
            p.setFont(negrita)
            p.setPen(c["texto"])
            p.drawText(r, centro, t)

        # días de la semana
        ancho_c = (ANCHO - 2 * MARGEN) / 7
        p.setFont(pequena)
        p.setPen(c["tenue"])
        for i in range(7):
            dia = (self._primero + i) % 7 + 1                       # Qt: 1 lunes ... 7 domingo
            nombre = self._loc.standaloneDayName(dia, QLocale.FormatType.ShortFormat)[:2]
            p.drawText(QRectF(MARGEN + i * ancho_c, CABEZA, ancho_c, DIAS), centro, nombre.capitalize())

        # la cuadrícula
        hoy = datetime.date.today()
        p.setFont(f)
        for i, d in enumerate(cuadricula(self._anio, self._mes, self._primero)):
            r = QRectF(MARGEN + (i % 7) * ancho_c, CABEZA + DIAS + (i // 7) * CELDA, ancho_c, CELDA)
            if d == hoy:
                lado = min(r.width(), r.height()) - 6
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c["acento"])
                p.drawEllipse(QRectF(r.center().x() - lado / 2, r.center().y() - lado / 2, lado, lado))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(fondo)
            elif d.month == self._mes:
                p.setPen(c["texto"])
            else:
                otro = QColor(c["tenue"])
                otro.setAlphaF(otro.alphaF() * 0.55)
                p.setPen(otro)
            p.drawText(r, centro, str(d.day))

        # pie: la fecha de hoy y el panel de Windows
        y = ALTO - PIE
        p.setPen(QPen(c["tenue"], 0.5))
        p.drawLine(MARGEN, y, ANCHO - MARGEN, y)
        r = QRect(MARGEN - 6, y + 5, ANCHO - 2 * MARGEN + 12, PIE - 10)
        zona_encima("avisos", r)
        p.setFont(pequena)
        p.setPen(c["tenue"])
        medida = QFontMetrics(pequena)
        sitio = r.width() - 12 - medida.horizontalAdvance("Notificaciones ›") - 10
        fecha = self._loc.toString(hoy, "dddd d 'de' MMMM")
        if medida.horizontalAdvance(fecha) > sitio:
            fecha = self._loc.toString(hoy, "ddd d MMM")
        p.drawText(r.adjusted(6, 0, -6, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   medida.elidedText(fecha[:1].upper() + fecha[1:], Qt.TextElideMode.ElideRight, sitio))
        p.setPen(c["acento"])
        p.drawText(r.adjusted(6, 0, -6, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                   "Notificaciones ›")
        p.end()
