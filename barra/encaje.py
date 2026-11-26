"""Encajar abajo en las pantallas verticales.

En una pantalla vertical, Windows encaja una ventana en la mitad de abajo al
soltarla en el borde inferior; ese borde lo tapa nuestra barra y el encaje no
llega a saltar. Aquí se hace lo mismo: al arrastrar una ventana sobre la barra
de una pantalla vertical se ve dónde quedará, y al soltarla ocupa la mitad de
abajo del área libre. Windows avisa de que empieza y acaba el arrastre
(SetWinEventHook, sin inyectar nada); la posición del ratón se mira mientras dura.
"""
import ctypes
from ctypes import wintypes as w

from PySide6.QtCore import QObject, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import win

EMPIEZA, ACABA = 0x000A, 0x000B           # EVENT_SYSTEM_MOVESIZESTART / END


def mitad_de_abajo(area):
    """La mitad de abajo de un área (izquierda, arriba, derecha, abajo)."""
    return area[0], area[1] + (area[3] - area[1]) // 2, area[2], area[3]


def en_zona(cursor, pantalla, area):
    """¿Soltar ahí encaja abajo? En una pantalla vertical, con el ratón en la franja
    de abajo que queda fuera del área libre (la barra) o pegado al borde."""
    x, y = cursor
    vertical = pantalla[3] - pantalla[1] > pantalla[2] - pantalla[0]
    dentro = pantalla[0] <= x < pantalla[2] and pantalla[1] <= y < pantalla[3]
    return vertical and dentro and y >= min(area[3], pantalla[3] - 6) - 1


class Previa(QWidget):
    """El hueco donde quedará la ventana, como el que dibuja Windows."""

    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowTransparentForInput
                         | Qt.WindowType.WindowDoesNotAcceptFocus | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.color = QColor("#4CC2FF")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        relleno = QColor(self.color)
        relleno.setAlpha(55)
        p.setBrush(relleno)
        borde = QColor(self.color)
        borde.setAlpha(200)
        p.setPen(QPen(borde, 2))
        p.drawRoundedRect(self.rect().adjusted(6, 6, -6, -6), 8, 8)
        p.end()


class EncajeAbajo(QObject):
    def __init__(self, color=lambda: "#4CC2FF"):
        super().__init__()
        self._color = color
        self._ventana, self._tam, self._destino = None, None, None
        self._previa = None
        self._raton = QTimer(self)
        self._raton.setInterval(40)
        self._raton.timeout.connect(self._mirar)
        self._proc = win.EVENTPROC(self._evento)            # vivo mientras exista el gancho
        self._gancho = win.user32.SetWinEventHook(EMPIEZA, ACABA, None, self._proc, 0, 0, 2)
        self.ok = bool(self._gancho)

    def cerrar(self):
        if self._gancho:
            win.user32.UnhookWinEvent(self._gancho)
            self._gancho = None
        self._raton.stop()
        if self._previa:
            self._previa.hide()

    def _evento(self, gancho, evento, hwnd, objeto, hijo, hilo, hora):
        try:
            if objeto != 0:                                  # OBJID_WINDOW
                return
            if evento == EMPIEZA:
                r = w.RECT()
                win.user32.GetWindowRect(hwnd, ctypes.byref(r))
                self._ventana, self._tam, self._destino = hwnd, (r.right - r.left, r.bottom - r.top), None
                self._raton.start()
            elif evento == ACABA and hwnd == self._ventana:
                self._raton.stop()
                self._mirar()
                destino, self._ventana = self._destino, None
                self._ver(None)
                if destino:
                    # Si Windows ya la ha encajado por su cuenta, se deja como está.
                    QTimer.singleShot(120, lambda: self._encajar(hwnd, destino))
        except Exception:
            pass

    def _mirar(self):
        h = self._ventana
        if not h:
            return
        r = w.RECT()
        win.user32.GetWindowRect(h, ctypes.byref(r))
        if (r.right - r.left, r.bottom - r.top) != self._tam:        # se está cambiando de tamaño, no moviendo
            self._ver(None)
            return
        pos = w.POINT()
        win.user32.GetCursorPos(ctypes.byref(pos))
        info = win.MONITORINFO(cbSize=ctypes.sizeof(win.MONITORINFO))
        win.user32.GetMonitorInfoW(win.user32.MonitorFromPoint(pos, 2), ctypes.byref(info))
        m, a = info.rcMonitor, info.rcWork
        pantalla, area = (m.left, m.top, m.right, m.bottom), (a.left, a.top, a.right, a.bottom)
        self._ver(mitad_de_abajo(area) if en_zona((pos.x, pos.y), pantalla, area) else None)

    def _ver(self, destino):
        self._destino = destino
        if destino is None:
            if self._previa and self._previa.isVisible():
                self._previa.hide()
            return
        if self._previa is None:
            self._previa = Previa()
        self._previa.color = QColor(self._color())
        # De píxeles reales a los de Qt (iguales con la escala al 100 %).
        centro = ((destino[0] + destino[2]) // 2, (destino[1] + destino[3]) // 2)
        pantalla = next((s for s in QGuiApplication.screens()
                         if s.geometry().contains(round(centro[0] / s.devicePixelRatio()),
                                                  round(centro[1] / s.devicePixelRatio()))),
                        QGuiApplication.primaryScreen())
        k = pantalla.devicePixelRatio()
        self._previa.setGeometry(QRect(round(destino[0] / k), round(destino[1] / k),
                                       round((destino[2] - destino[0]) / k), round((destino[3] - destino[1]) / k)))
        if not self._previa.isVisible():
            self._previa.show()
        self._previa.update()

    @staticmethod
    def _encajar(hwnd, destino):
        u = win.user32
        if not u.IsWindow(hwnd) or u.IsZoomed(hwnd) or (hasattr(u, "IsWindowArranged") and u.IsWindowArranged(hwnd)):
            return
        r, f = w.RECT(), w.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        if win.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(f), ctypes.sizeof(f)) != 0:
            f = r
        # Lo que se ve va al hueco; el borde invisible de la ventana, por fuera.
        x, y = destino[0] - (f.left - r.left), destino[1] - (f.top - r.top)
        an = destino[2] - destino[0] + (f.left - r.left) + (r.right - f.right)
        al = destino[3] - destino[1] + (f.top - r.top) + (r.bottom - f.bottom)
        u.SetWindowPos(hwnd, None, x, y, an, al, 0x0014)            # NOZORDER | NOACTIVATE
