"""Vista previa al pasar el ratón: una miniatura en vivo por cada ventana del
grupo. Las dibuja el propio Windows (DWM), así que aquí no se captura nada."""
import ctypes
from ctypes import wintypes as w

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import win

dwm = win.dwmapi
ANCHO, ALTO, MARGEN, CABEZA, HUECO = 240, 150, 8, 28, 6
MIN_ANCHO, LISTA_ANCHO = 150, 320


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


def disponer(tamanos, max_ancho):
    """Dónde va cada ventana. `tamanos` son los de las ventanas reales ((0, 0)
    si no hay imagen). Devuelve (tarjetas, miniaturas, ancho, alto): una fila de
    miniaturas, más pequeñas si hace falta, o una lista si no caben."""
    n = len(tamanos)
    minis = []
    if n == 1:
        escalas = [1]
    else:
        escalas = [1, 0.85, 0.7]
    for k in escalas:
        minis = [encajar(a, b, ANCHO * k, ALTO * k) for a, b in tamanos]
        anchos = [max(m[0], MIN_ANCHO) + 2 * MARGEN for m in minis]
        total = sum(anchos) + HUECO * (n - 1)
        if total <= max_ancho:
            alto_mini = max((m[1] for m in minis), default=0)
            alto = CABEZA + (alto_mini + MARGEN if alto_mini else 0)
            tarjetas, rects, x = [], [], 0
            for an, (ma, mb) in zip(anchos, minis):
                tarjetas.append(QRect(x, 0, an, alto))
                rects.append(QRect(x + (an - ma) // 2, CABEZA + (alto_mini - mb) // 2, ma, mb) if mb else QRect())
                x += an + HUECO
            return tarjetas, rects, total, alto
    ancho = min(LISTA_ANCHO, max_ancho)
    return [QRect(0, i * CABEZA, ancho, CABEZA) for i in range(n)], [QRect()] * n, ancho, n * CABEZA


class Vista(QWidget):
    def __init__(self, al_pulsar, al_cerrar):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.al_pulsar, self.al_cerrar = al_pulsar, al_cerrar
        self.clave, self.hwnds = "", []
        self._minis, self._tarjetas, self._titulos = [], [], []
        self._col, self._fuente, self._sitio = {}, "Segoe UI", None
        self._encima, self._en_x = -1, False
        self._esconder = QTimer(self, singleShot=True, interval=220, timeout=self.ocultar)

    # ----- mostrar y ocultar -----
    def mostrar(self, clave, ventanas, centro_x, abajo, pantalla, tema):
        """`ventanas` es [(hwnd, título)]; `centro_x` y `abajo`, globales."""
        self._esconder.stop()
        self._soltar()
        self.clave, self._sitio = clave, (centro_x, abajo, pantalla, tema)
        self.hwnds, self._titulos = [h for h, _ in ventanas], [t for _, t in ventanas]
        self._col, self._fuente = tema["colores"], tema["fuente"]
        self._encima = -1
        tamanos = []
        for h in self.hwnds:
            mini, tam = ctypes.c_void_p(), w.SIZE()
            if dwm.DwmRegisterThumbnail(int(self.winId()), h, ctypes.byref(mini)) == 0:
                dwm.DwmQueryThumbnailSourceSize(mini, ctypes.byref(tam))
                self._minis.append(mini)
            else:
                self._minis.append(None)
            # Las minimizadas a veces solo dan su barra de título: mejor sin imagen.
            tamanos.append((tam.cx, tam.cy) if tam.cy > 60 else (0, 0))
        self._tarjetas, rects, ancho, alto = disponer(tamanos, pantalla.width() - 24)
        x = round(min(max(centro_x - ancho / 2, pantalla.left() + 6), pantalla.right() - ancho - 6))
        self.setGeometry(QRect(x, round(max(pantalla.top() + 6, abajo - alto - 8)), ancho, alto))
        self.show()
        r = self.devicePixelRatioF()
        for mini, q in zip(self._minis, rects):
            if mini and not q.isEmpty():
                p = PROPS(dwFlags=1 | 8 | 16, fVisible=True, fSourceClientAreaOnly=False,
                          rcDestination=w.RECT(*(round(v * r) for v in (q.left(), q.top(), q.left() + q.width(),
                                                                        q.top() + q.height()))))
                dwm.DwmUpdateThumbnailProperties(mini, ctypes.byref(p))
        self.update()

    def quitar_muertas(self, vivas):
        """Se cerró alguna ventana: seguir con las que quedan."""
        quedan = [(h, t) for h, t in zip(self.hwnds, self._titulos) if h in vivas]
        if len(quedan) == len(self.hwnds):
            return
        if quedan:
            self.mostrar(self.clave, quedan, *self._sitio)
        else:
            self.ocultar()

    def pronto(self):
        """Se oculta enseguida, salvo que el ratón pase a la vista."""
        if self.isVisible():
            self._esconder.start()

    def ocultar(self):
        self._esconder.stop()
        self._soltar()
        self.hide()
        self.clave, self.hwnds = "", []

    def _soltar(self):
        for m in self._minis:
            if m:
                dwm.DwmUnregisterThumbnail(m)
        self._minis = []

    # ----- ratón -----
    @staticmethod
    def _zona_x(t):
        return QRect(t.right() - CABEZA + 1, t.top(), CABEZA, CABEZA)

    def _en(self, pos):
        return next((i for i, t in enumerate(self._tarjetas) if t.contains(pos)), -1)

    def enterEvent(self, e):
        self._esconder.stop()

    def leaveEvent(self, e):
        self._encima, self._en_x = -1, False
        self.update()
        self.pronto()

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()
        i = self._en(pos)
        x = i >= 0 and self._zona_x(self._tarjetas[i]).contains(pos)
        if (i, x) != (self._encima, self._en_x):
            self._encima, self._en_x = i, x
            self.update()

    def mousePressEvent(self, e):
        pos = e.position().toPoint()
        i = self._en(pos)
        if i < 0 or i >= len(self.hwnds):
            return
        hwnd, x = self.hwnds[i], self._zona_x(self._tarjetas[i]).contains(pos)
        if x or e.button() == Qt.MouseButton.MiddleButton:
            if len(self.hwnds) == 1:
                self.ocultar()
            self.al_cerrar(hwnd)          # si quedan más, quitar_muertas la retira
        elif e.button() == Qt.MouseButton.LeftButton:
            self.ocultar()
            self.al_pulsar(hwnd)

    # ----- dibujo -----
    def paintEvent(self, e):
        p = QPainter(self)
        c = {k: QColor(v) for k, v in self._col.items() if v}
        fondo = QColor(c["fondo"])
        fondo.setAlpha(255)
        p.fillRect(self.rect(), fondo)
        f = QFont(self._fuente)
        f.setPixelSize(12)
        p.setFont(f)
        for i, t in enumerate(self._tarjetas):
            encima = i == self._encima
            if encima:
                p.fillRect(t, c["encima"])
            p.setPen(c["texto"])
            zona = QRect(t.left() + MARGEN, t.top(), t.width() - CABEZA - MARGEN, CABEZA)
            titulo = self._titulos[i] if i < len(self._titulos) else ""
            p.drawText(zona, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       QFontMetrics(f).elidedText(titulo, Qt.TextElideMode.ElideRight, zona.width()))
            z = self._zona_x(t)
            en_x = encima and self._en_x
            if en_x:
                p.fillRect(z.adjusted(3, 3, -3, -3), c["alerta"])
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QPen(fondo if en_x else c["tenue"], 1.4))
            m = z.center()
            p.drawLine(m.x() - 4, m.y() - 4, m.x() + 4, m.y() + 4)
            p.drawLine(m.x() + 4, m.y() - 4, m.x() - 4, m.y() + 4)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.setPen(QPen(c["acento"]))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        p.end()
