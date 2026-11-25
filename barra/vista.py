"""Vista previa de una ventana al pasar el ratón: una miniatura en vivo que
dibuja el propio Windows (DWM), así que aquí no se captura nada."""
import ctypes
from ctypes import wintypes as w

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import win

dwm = win.dwmapi
ANCHO, ALTO, MARGEN, CABEZA = 240, 150, 8, 28


class PROPS(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("dwFlags", w.DWORD), ("rcDestination", w.RECT), ("rcSource", w.RECT),
                ("opacity", ctypes.c_ubyte), ("fVisible", w.BOOL), ("fSourceClientAreaOnly", w.BOOL)]


dwm.DwmRegisterThumbnail.argtypes = (w.HWND, w.HWND, ctypes.POINTER(ctypes.c_void_p))
dwm.DwmUnregisterThumbnail.argtypes = (ctypes.c_void_p,)
dwm.DwmQueryThumbnailSourceSize.argtypes = (ctypes.c_void_p, ctypes.POINTER(w.SIZE))
dwm.DwmUpdateThumbnailProperties.argtypes = (ctypes.c_void_p, ctypes.POINTER(PROPS))


def encajar(ancho, alto, max_ancho=ANCHO, max_alto=ALTO):
    """Tamaño de la miniatura, con la misma proporción y sin agrandar."""
    if ancho <= 0 or alto <= 0:
        return 0, 0
    k = min(max_ancho / ancho, max_alto / alto, 1)
    return max(1, round(ancho * k)), max(1, round(alto * k))


class Vista(QWidget):
    def __init__(self, al_pulsar, al_cerrar):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.al_pulsar, self.al_cerrar = al_pulsar, al_cerrar
        self.hwnd = 0
        self._mini = None
        self._titulo, self._col, self._fuente = "", {}, "Segoe UI"
        self._en_x = False
        self._esconder = QTimer(self, singleShot=True, interval=220, timeout=self.ocultar)

    # ----- mostrar y ocultar -----
    def mostrar(self, hwnd, titulo, centro_x, abajo, pantalla, tema):
        """`centro_x` y `abajo` son globales; se coloca encima de la barra."""
        self._esconder.stop()
        self._soltar()
        self.hwnd, self._titulo = hwnd, titulo
        self._col, self._fuente = tema["colores"], tema["fuente"]
        mini = ctypes.c_void_p()
        tam = w.SIZE()
        if dwm.DwmRegisterThumbnail(int(self.winId()), hwnd, ctypes.byref(mini)) == 0:
            self._mini = mini
            dwm.DwmQueryThumbnailSourceSize(mini, ctypes.byref(tam))
        # Las minimizadas a veces solo dan su barra de título: mejor sin imagen.
        an, al = encajar(tam.cx, tam.cy) if tam.cy > 60 else (0, 0)
        ancho = max(an, 180) + 2 * MARGEN
        alto = CABEZA + (al + MARGEN if al else 0)
        x = round(min(max(centro_x - ancho / 2, pantalla.left() + 6), pantalla.right() - ancho - 6))
        self.setGeometry(QRect(x, round(abajo - alto - 8), ancho, alto))
        self.show()
        if self._mini and al:
            r = self.devicePixelRatioF()
            izq = (ancho - an) / 2
            p = PROPS(dwFlags=1 | 8 | 16, fVisible=True, fSourceClientAreaOnly=False,
                      rcDestination=w.RECT(*(round(v * r) for v in (izq, CABEZA, izq + an, CABEZA + al))))
            dwm.DwmUpdateThumbnailProperties(self._mini, ctypes.byref(p))
        self.update()

    def pronto(self):
        """Se oculta enseguida, salvo que el ratón pase a la vista."""
        if self.isVisible():
            self._esconder.start()

    def ocultar(self):
        self._esconder.stop()
        self._soltar()
        self.hide()
        self.hwnd = 0

    def _soltar(self):
        if self._mini:
            dwm.DwmUnregisterThumbnail(self._mini)
            self._mini = None

    # ----- ratón -----
    def _zona_x(self):
        return QRect(self.width() - CABEZA, 0, CABEZA, CABEZA)

    def enterEvent(self, e):
        self._esconder.stop()

    def leaveEvent(self, e):
        self._en_x = False
        self.pronto()

    def mouseMoveEvent(self, e):
        en = self._zona_x().contains(e.position().toPoint())
        if en != self._en_x:
            self._en_x = en
            self.update()

    def mousePressEvent(self, e):
        hwnd, x = self.hwnd, self._zona_x().contains(e.position().toPoint())
        self.ocultar()
        if x or e.button() == Qt.MouseButton.MiddleButton:
            self.al_cerrar(hwnd)
        elif e.button() == Qt.MouseButton.LeftButton:
            self.al_pulsar(hwnd)

    # ----- dibujo -----
    def paintEvent(self, e):
        p = QPainter(self)
        c = {k: QColor(v) for k, v in self._col.items()}
        fondo = c["fondo"]
        fondo.setAlpha(255)
        p.fillRect(self.rect(), fondo)
        p.setPen(QPen(c["acento"]))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        f = QFont(self._fuente)
        f.setPixelSize(12)
        p.setFont(f)
        p.setPen(c["texto"])
        zona = QRect(MARGEN, 0, self.width() - CABEZA - MARGEN, CABEZA)
        texto = QFontMetrics(f).elidedText(self._titulo, Qt.TextElideMode.ElideRight, zona.width())
        p.drawText(zona, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, texto)
        z = self._zona_x()
        if self._en_x:
            p.fillRect(z.adjusted(3, 3, -3, -3), c["alerta"])
        p.setPen(QPen(fondo if self._en_x else c["tenue"], 1.4))
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        m = z.center()
        p.drawLine(m.x() - 4, m.y() - 4, m.x() + 4, m.y() + 4)
        p.drawLine(m.x() + 4, m.y() - 4, m.x() - 4, m.y() + 4)
        p.end()
