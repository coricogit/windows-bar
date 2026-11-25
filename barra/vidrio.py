"""Vidrio líquido: refracta de verdad el fondo de escritorio.

`Fondo` pide a Windows la imagen de la capa del fondo (también la de Wallpaper
Engine), nunca de las ventanas, y guarda solo la franja que hay tras la barra.
`Vidrio` la pinta difuminada, con los bordes curvados como una lente.
"""
import ctypes
import threading
import time
from ctypes import wintypes as w

from PySide6.QtCore import Property, QObject, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient,
                           QTransform)
from PySide6.QtQml import qmlRegisterType
from PySide6.QtQuick import QQuickPaintedItem

from . import temas, win
from .bandeja import BITMAPINFOHEADER, gdi32, user32

user32.PrintWindow.argtypes = (w.HWND, w.HDC, w.UINT)
CADA = 1.2           # segundos entre lecturas del fondo
EXTRA = 70           # píxeles de más por arriba, para la lente
# (velo oscuro, difuminado): de más claro a más tintado.
NIVELES = {"muy_claro": (0.02, 5), "claro": (0.10, 7), "normal": (0.20, 9), "tintado": (0.36, 11),
           "muy_tintado": (0.56, 13)}
NOMBRES = {"muy_claro": "Muy claro", "claro": "Claro", "normal": "Predeterminado", "tintado": "Tintado",
           "muy_tintado": "Muy tintado"}


def velo(nivel, luces, clara):
    """Opacidad del velo de una pieza. `luces`: lo claro que es el fondo por
    tramos. Oscuro, sube lo que haga falta para que se lea el texto blanco
    hasta en el tramo más claro; con la pieza clara es blanco."""
    base = NIVELES.get(nivel, NIVELES["normal"])[0]
    if clara:
        return min(0.75, 0.12 + base)
    mas = max(luces, default=0.3)
    falta = (mas - 0.46) / (mas - 0.07) if mas > 0.46 else 0
    return min(0.85, max(base, falta))


def velo_justo(luces, clara):
    """Para temas sin vidrio: solo el velo imprescindible, y ninguno si no hace falta."""
    mas = max(luces, default=0.3)
    return 0 if clara or mas <= 0.46 else min(0.85, (mas - 0.46) / (mas - 0.07))


def es_clara(luces, antes):
    """¿Texto oscuro? Solo si todo el fondo es claro; con margen, para no parpadear."""
    return bool(luces) and min(luces) > (0.54 if antes else 0.62)


def luces_de(img, x, y, an, al, n=8):
    """Lo claro que es `img` en `n` tramos de ese rectángulo."""
    chica = img.copy(QRect(round(x), round(y), max(1, round(an)), max(1, round(al)))).scaled(
        n, 1, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    out = []
    for i in range(n):
        q = QColor(chica.pixel(i, 0))
        out.append(0.2126 * q.redF() + 0.7152 * q.greenF() + 0.0722 * q.blueF())
    return out


def difuminar(img, radio):
    k = max(2, radio)
    chica = img.scaled(max(1, img.width() // k), max(1, img.height() // k), Qt.AspectRatioMode.IgnoreAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    return chica.scaled(img.width(), img.height(), Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)


def luminosidad(img):
    if img.isNull():
        return 0.3
    c = img.scaled(1, 1, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    q = QColor(c.pixel(0, 0))
    return 0.2126 * q.redF() + 0.7152 * q.greenF() + 0.0722 * q.blueF()


class _Lienzo:
    """Un mapa de bits del tamaño del fondo; solo existe mientras hay vidrio."""

    def __init__(self, ancho, alto):
        self.ancho, self.alto = ancho, alto
        info = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), ancho, -alto, 1, 32, 0, 0, 0, 0, 0, 0)
        self.bits = ctypes.c_void_p()
        self.dc = gdi32.CreateCompatibleDC(None)
        self.bmp = gdi32.CreateDIBSection(self.dc, ctypes.byref(info), 0, ctypes.byref(self.bits), None, 0)
        self.viejo = gdi32.SelectObject(self.dc, self.bmp)

    def recorte(self, x, y, an, al):
        x, y = max(0, x), max(0, y)
        an, al = min(an, self.ancho - x), min(al, self.alto - y)
        if an <= 0 or al <= 0:
            return QImage()
        fila = self.ancho * 4
        datos = ctypes.string_at(self.bits.value + y * fila, al * fila)
        return QImage(datos, self.ancho, al, fila, QImage.Format.Format_RGB32).copy(QRect(x, 0, an, al))

    def cerrar(self):
        gdi32.SelectObject(self.dc, self.viejo)
        gdi32.DeleteObject(self.bmp)
        gdi32.DeleteDC(self.dc)


def capa_fondo():
    """La ventana que pinta el fondo de escritorio, o None."""
    progman = win.user32.FindWindowExW(None, None, "Progman", None)
    for padre in (progman, None):
        h = win.user32.FindWindowExW(padre, None, "WorkerW", None)
        while h:
            if win.user32.IsWindowVisible(h) and not win.user32.FindWindowExW(h, None, "SHELLDLL_DefView", None):
                return h
            h = win.user32.FindWindowExW(padre, h, "WorkerW", None)
    return None


class Fondo(QObject):
    cambio = Signal()

    def __init__(self):
        super().__init__()
        self.franjas = {}        # (x, y, ancho, alto) global -> {"nitida", "difusa"}
        self.zonas = []
        self.nivel = "normal"
        self.activo = False      # solo con un tema de vidrio a la vista
        self._lienzo = None
        self._huella = {}
        self._cerrojo = threading.Lock()
        self._despierta = threading.Event()
        self._hilo = None

    def poner(self, zonas, nivel, activo):
        """`zonas`: rectángulos globales (x, y, ancho, alto) de las barras."""
        if (zonas, nivel, activo) == (self.zonas, self.nivel, self.activo):
            return
        self.zonas, self.nivel, self.activo = zonas, nivel, activo
        self._huella.clear()
        if activo and not self._hilo:
            self._hilo = threading.Thread(target=self._seguir, daemon=True)
            self._hilo.start()
        self._despierta.set()

    def _seguir(self):
        quieto = 0
        while True:
            if self.activo:
                try:
                    if self.leer():
                        self.cambio.emit()
                        quieto = 0
                    else:
                        quieto += 1
                except Exception:          # un fallo aquí solo deja el fondo anterior
                    pass
                # Fondo quieto: cada vez se mira menos, hasta cada 6 s.
                self._despierta.wait(min(6, CADA * (1 + quieto / 2)))
            else:
                if self._lienzo:
                    self._lienzo.cerrar()
                    self._lienzo = None
                self._despierta.wait()
            self._despierta.clear()

    def leer(self):
        """Actualiza las franjas. Devuelve si algo cambió."""
        h = capa_fondo()
        r = w.RECT()
        if h:
            win.user32.GetWindowRect(h, ctypes.byref(r))
        ancho, alto = r.right - r.left, r.bottom - r.top
        listo = False
        if ancho > 0 and alto > 0:
            if not self._lienzo or (self._lienzo.ancho, self._lienzo.alto) != (ancho, alto):
                if self._lienzo:
                    self._lienzo.cerrar()
                self._lienzo = _Lienzo(ancho, alto)
            listo = bool(user32.PrintWindow(h, self._lienzo.dc, 2))      # RENDERFULLCONTENT
        cambio = False
        for z in list(self.zonas):
            x, y, an, al = z
            img = self._lienzo.recorte(x - r.left, y - EXTRA - r.top, an, al + EXTRA) if listo else QImage()
            if img.isNull() or luminosidad(img) < 0.004:
                img = self._de_archivo(an, al + EXTRA)
            if img.isNull():
                continue
            mini = img.scaled(48, 6, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            huella = bytes(mini.constBits())
            if self._huella.get(z) == huella:
                continue
            self._huella[z] = huella
            dif = difuminar(img, NIVELES.get(self.nivel, NIVELES["normal"])[1])
            vieja = self.franjas.get(z)
            if vieja and vieja["difusa"].size() == dif.size():      # mezcla, para que no salte
                p = QPainter(dif)
                p.setOpacity(0.4)
                p.drawImage(0, 0, vieja["difusa"])
                p.end()
            nueva = {"nitida": difuminar(img, 2), "difusa": dif}
            with self._cerrojo:
                self.franjas = {**{k: v for k, v in self.franjas.items() if k in self.zonas}, z: nueva}
            cambio = True
        return cambio

    @staticmethod
    def _de_archivo(an, al):
        """Si Windows no da la capa: la parte de abajo de la imagen de fondo."""
        img = QImage(temas.imagen_fondo(True) or "")
        if img.isNull():
            return img
        img = img.scaledToWidth(an, Qt.TransformationMode.SmoothTransformation)
        return img.copy(0, max(0, img.height() - al), an, al).convertToFormat(QImage.Format.Format_RGB32)

    def franja(self, x, y):
        with self._cerrojo:
            for (zx, zy, an, al), f in self.franjas.items():
                if zx <= x < zx + an and zy - EXTRA <= y < zy + al:
                    return (zx, zy), f
        return None, None


fondo = None          # lo pone la barra al arrancar


class Vidrio(QQuickPaintedItem):
    """Una pieza de vidrio que llena su rectángulo."""
    cambio = Signal()
    claraCambio = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clara, self._luces, self._medido, self._pintar = False, [], None, True
        # Las piezas se mueven al crecer sus vecinas, y eso no las repinta.
        self._t = QTimer(self, interval=450, timeout=self._medir)
        self._t.start()
        self.setAntialiasing(True)
        self._radio, self._luzX, self._origen = 20.0, -1.0, None
        self.cambio.connect(self.update)
        if fondo:
            fondo.cambio.connect(self._fondo_nuevo)

    def _get_radio(self):
        return self._radio

    def _set_radio(self, v):
        if v != self._radio:
            self._radio = v
            self.cambio.emit()

    radio = Property(float, _get_radio, _set_radio, notify=cambio)

    def _get_luz(self):
        return self._luzX

    def _set_luz(self, v):
        if v != self._luzX:
            self._luzX = v
            self.cambio.emit()

    def _get_pintar(self):
        return self._pintar

    def _set_pintar(self, v):
        if v != self._pintar:
            self._pintar = v
            self.cambio.emit()

    # Falso: solo mide el fondo y pone el velo imprescindible.
    pintar = Property(bool, _get_pintar, _set_pintar, notify=cambio)

    # Dónde está el ratón sobre la pieza; negativo si no está.
    luzX = Property(float, _get_luz, _set_luz, notify=cambio)

    clara = Property(bool, lambda self: self._clara, notify=claraCambio)

    def _fondo_nuevo(self):
        self._medido = None
        self._medir()

    def _medir(self):
        if not fondo or not self.isVisible() or self.width() < 4:
            return
        x, y = self._posicion()
        ahora = (round(x), round(y), round(self.width()), round(self.height()), fondo.nivel)
        if ahora == self._medido:
            return
        zona, f = fondo.franja(x + self.width() / 2, y + self.height() / 2)
        if f:
            self._medido = ahora
            self._luces = luces_de(f["difusa"], x - zona[0], y - zona[1] + EXTRA, self.width(), self.height())
            clara = es_clara(self._luces, self._clara)
            if clara != self._clara:
                self._clara = clara
                self.claraCambio.emit()
        self.update()

    def _posicion(self):
        if self.window() and self.window().x() < -5000:      # --vista, fuera de la pantalla
            p = self.mapToScene(QPointF(0, 0))
            z = fondo.zonas[0] if fondo and fondo.zonas else (0, 0)
            return z[0] + p.x(), z[1] + p.y()
        p = self.mapToGlobal(QPointF(0, 0))
        return p.x(), p.y()

    def paint(self, p):
        an, al = self.width(), self.height()
        if an < 4 or al < 4:
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setPen(Qt.PenStyle.NoPen)
        caja = QRectF(0.75, 0.75, an - 1.5, al - 1.5)
        radio = min(self._radio, caja.height() / 2)
        if not self._pintar:
            v = velo_justo(self._luces, self._clara)
            if v > 0.03:
                p.setBrush(QColor.fromRgbF(0.05, 0.07, 0.11, v))
                p.drawPath(self._camino(caja, 10))
            return
        forma = self._camino(caja, radio)
        gx, gy = self._posicion()
        zona, f = fondo.franja(gx + an / 2, gy + al / 2) if fondo else (None, None)
        if f:
            dx, dy = zona[0] - gx, zona[1] - EXTRA - gy       # la franja, vista desde la pieza
            p.setBrush(self._textura(f["difusa"], dx, dy, an, al, 1, 1))
            p.drawPath(forma)
            # La lente: cada anillo, más cerca del borde, comprime más el fondo.
            for grosor, d, nitidez in ((10, 3, 0.35), (7, 7, 0.55), (4, 11, 0.8)):
                ex, ey = max(0.3, 1 - 2 * d / an), max(0.3, 1 - 2 * d / al)
                dentro = caja.adjusted(grosor, grosor, -grosor, -grosor)
                if dentro.height() <= 0 or dentro.width() <= 0:
                    continue
                anillo = forma.subtracted(self._camino(dentro, max(1, radio - grosor)))
                p.setOpacity(nitidez)
                p.setBrush(self._textura(f["nitida"], dx, dy, an, al, ex, ey))
                p.drawPath(anillo)
            p.setOpacity(1)
        else:
            p.setBrush(QColor(60, 72, 90, 150))
            p.drawPath(forma)

        # Velo para que se lea, algo más denso abajo.
        v = velo(fondo.nivel if fondo else "normal", self._luces, self._clara)
        tono = (1, 1, 1) if self._clara else (0.05, 0.07, 0.11)
        g = QLinearGradient(0, 0, 0, al)
        g.setColorAt(0, QColor.fromRgbF(*tono, v * 0.9))
        g.setColorAt(1, QColor.fromRgbF(*tono, v))
        p.setBrush(QBrush(g))
        p.drawPath(forma)
        # Luz que entra por arriba y rebota abajo.
        g = QLinearGradient(0, 0, 0, al)
        for pos, a in ((0, 0.34), (0.22, 0.08), (0.55, 0.0), (0.85, 0.05), (1, 0.17)):
            g.setColorAt(pos, QColor.fromRgbF(1, 1, 1, a))
        p.setBrush(QBrush(g))
        p.drawPath(forma)
        if self._luzX >= 0:
            r = QRadialGradient(self._luzX, al * 0.2, 70)
            r.setColorAt(0, QColor(255, 255, 255, 74))
            r.setColorAt(1, QColor(255, 255, 255, 0))
            p.setBrush(QBrush(r))
            p.drawPath(forma)

        # Canto: oscuro por fuera, dispersión de color y filo brillante en diagonal.
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 80 if self._clara else 60), 1.5))
        p.drawPath(forma)
        for ox, color in ((-0.6, QColor(120, 220, 255, 60)), (0.6, QColor(255, 150, 210, 60))):
            p.setPen(QPen(color, 1))
            p.drawPath(self._camino(caja.adjusted(1.6 + ox, 1.6, -1.6 + ox, -1.6), radio - 1.6))
        g = QLinearGradient(0, 0, min(an, al * 4), al)
        for pos, a in ((0, 0.95), (0.3, 0.35), (0.55, 0.12), (0.8, 0.30), (1, 0.75)):
            g.setColorAt(pos, QColor.fromRgbF(1, 1, 1, a))
        p.setPen(QPen(QBrush(g), 1.2))
        p.drawPath(self._camino(caja.adjusted(0.6, 0.6, -0.6, -0.6), radio - 0.6))

    @staticmethod
    def _camino(caja, radio):
        c = QPainterPath()
        c.addRoundedRect(caja, radio, radio)
        return c

    @staticmethod
    def _textura(img, dx, dy, an, al, ex, ey):
        """El fondo como pincel, escalado desde el centro de la pieza."""
        t = QTransform()
        t.translate(an / 2, al / 2)
        t.scale(ex, ey)
        t.translate(dx - an / 2, dy - al / 2)
        b = QBrush(img)
        b.setTransform(t)
        return b


def registrar_tipo():
    qmlRegisterType(Vidrio, "BarraTemas", 1, 0, "Vidrio")


if __name__ == "__main__":
    t = time.perf_counter()
    print(capa_fondo(), time.perf_counter() - t)
