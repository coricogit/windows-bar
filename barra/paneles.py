"""Los paneles de Windows junto a la barra, en el lado en que esté.

Windows 11 no admite la barra a los lados: los ajustes rápidos (sonido, wifi,
música) y las notificaciones con el calendario abren siempre en la esquina de
abajo a la derecha. Sus ventanas sí se dejan mover desde fuera, así que, cuando
una pasa a primer plano (SetWinEventHook, sin inyectar nada en Explorer), se
coloca junto a la barra y pegada abajo, como en Windows 10. Si Windows la
devuelve a su sitio (al desplegar algo dentro), se vuelve a colocar durante un
rato. El menú Inicio no se puede: Windows lo dibuja donde quiere aunque se mueva
su ventana.
"""
import ctypes
import os
from ctypes import wintypes as w

from PySide6.QtCore import QObject, QTimer

from . import win

PRIMER_PLANO = 0x0003                     # EVENT_SYSTEM_FOREGROUND
ANFITRIONES = ("shellhost.exe", "shellexperiencehost.exe")
VIGILAR_MS, CADA_MS = 3000, 80


def es_panel(exe, rect, pantalla):
    """¿Es un panel de la barra de Windows (ajustes rápidos, notificaciones)? Los
    abre ShellHost o ShellExperienceHost, pegados al borde derecho y altos."""
    if os.path.basename(exe).lower() not in ANFITRIONES:
        return False
    x0, y0, x1, y1 = rect
    px0, py0, px1, py1 = pantalla
    return abs(x1 - px1) <= 2 and (y1 - y0) >= (py1 - py0) // 2 and (x1 - x0) < (px1 - px0) // 2


def destino(lado, rect, pantalla, barra):
    """Dónde va (x, y) la ventana de un panel con la barra en `lado`, o None si se
    queda donde la pone Windows. Las ventanas de estos paneles llevan su margen de
    12 px por dentro: pegarlas a la barra y al borde de abajo deja ese hueco."""
    an, al = rect[2] - rect[0], rect[3] - rect[1]
    abajo = pantalla[3] - al
    if lado == "izquierda":
        return barra[2], abajo
    if lado == "derecha":
        return barra[0] - an, abajo
    return None


class Paneles(QObject):
    def __init__(self, donde):
        """`donde(hwnd, rect)` da (lado, pantalla, barra) en píxeles físicos
        (x0, y0, x1, y1), o None si en esa pantalla no hay barra a un lado."""
        super().__init__()
        self._donde = donde
        self._ventana, self._meta, self._hasta = None, None, 0
        self._tic = QTimer(self, interval=CADA_MS, timeout=self._mirar)
        self._proc = win.EVENTPROC(self._evento)             # vivo mientras exista el gancho
        self._gancho = win.user32.SetWinEventHook(PRIMER_PLANO, PRIMER_PLANO, None, self._proc, 0, 0, 2)
        self.ok = bool(self._gancho)

    def cerrar(self):
        if self._gancho:
            win.user32.UnhookWinEvent(self._gancho)
            self._gancho = None
        self._tic.stop()

    @staticmethod
    def _rect(hwnd):
        r = w.RECT()
        win.user32.GetWindowRect(hwnd, ctypes.byref(r))
        return r.left, r.top, r.right, r.bottom

    def _evento(self, gancho, evento, hwnd, objeto, hijo, hilo, hora):
        try:
            if objeto != 0 or not hwnd:
                return
            if hwnd != self._ventana:
                self._ventana, self._meta = None, None
                self._tic.stop()
            self._colocar(hwnd, nuevo=True)
        except Exception:
            pass

    def _colocar(self, hwnd, nuevo=False):
        rect = self._rect(hwnd)
        if nuevo:
            sitio = self._donde(hwnd, rect)
            if not sitio:
                return
            lado, pantalla, barra = sitio
            if not es_panel(win.exe_of(win.pid_of(hwnd)), rect, pantalla):
                return
            meta = destino(lado, rect, pantalla, barra)
            if not meta:
                return
            self._ventana, self._meta = hwnd, meta
            self._tic.start()
            self._vueltas = VIGILAR_MS // CADA_MS
        if self._meta and (rect[0], rect[1]) != self._meta:
            # SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
            win.user32.SetWindowPos(hwnd, None, self._meta[0], self._meta[1], 0, 0, 0x0001 | 0x0004 | 0x0010)

    def _mirar(self):
        """Un rato después de abrirse: si Windows lo devolvió a su esquina, otra vez a su sitio."""
        self._vueltas -= 1
        h = self._ventana
        if not h or self._vueltas <= 0 or win.user32.GetForegroundWindow() != h:
            self._tic.stop()
            return
        self._colocar(h)
