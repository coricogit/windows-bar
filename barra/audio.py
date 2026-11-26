"""Las sesiones de sonido de cada programa (lo que enseña el Mezclador de volumen).

Sirve para dos cosas, sin inyectar nada en nadie:
- quién está usando el micrófono: los programas con una sesión de grabación activa;
- el volumen de cada programa, para cambiarlo con la rueda sobre su botón.

Un programa puede sonar desde otro proceso suyo (Chrome, Discord, Spotify): por
eso se busca por el .exe y no por el proceso de la ventana. Llamar desde un hilo
con COM iniciado (el de la interfaz ya lo está).
"""
import ctypes
import os
from ctypes import wintypes as w

from .programas import principal
from .win import GUID, exe_of, method, ole32

CLSID_ENUMERADOR = "bcde0395-e52f-467c-8e3d-c4579291692e"
IID_ENUMERADOR = "a95664d2-9614-4f35-a746-de8db63617e6"
IID_GESTOR2 = "77aa99a0-1bd6-484f-8bc7-2c654c9a9b6f"
IID_CONTROL2 = "bfb7ff88-7239-4fc9-8fa2-07c950be9c6d"
IID_VOLUMEN = "87ce5498-68d6-44e5-9215-6f0d4e1b4b8b"
SALIDA, ENTRADA = 0, 1                 # eRender, eCapture
ACTIVA = 1                             # AudioSessionStateActive


def _soltar(*objs):
    for o in objs:
        if o and o.value:
            method(o, 2)()


def _qi(obj, iid):
    out, g = ctypes.c_void_p(), GUID(iid)
    return out if method(obj, 0, ctypes.c_void_p, ctypes.c_void_p)(ctypes.byref(g), ctypes.byref(out)) >= 0 else None


def _sesiones(flujo):
    """Recorre las sesiones de todos los dispositivos activos de ese flujo:
    da (control2, pid, activa) y las suelta al seguir."""
    enum = ctypes.c_void_p()
    clsid, iid = GUID(CLSID_ENUMERADOR), GUID(IID_ENUMERADOR)
    if ole32.CoCreateInstance(ctypes.byref(clsid), None, 23, ctypes.byref(iid), ctypes.byref(enum)) < 0:
        return
    col = ctypes.c_void_p()
    try:
        if method(enum, 3, ctypes.c_int, w.DWORD, ctypes.c_void_p)(flujo, 1, ctypes.byref(col)) < 0:
            return
        n = w.UINT()
        method(col, 3, ctypes.c_void_p)(ctypes.byref(n))
        for i in range(n.value):
            dev, gestor, lista = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
            try:
                if method(col, 4, w.UINT, ctypes.c_void_p)(i, ctypes.byref(dev)) < 0:
                    continue
                g = GUID(IID_GESTOR2)
                if method(dev, 3, ctypes.c_void_p, w.DWORD, ctypes.c_void_p, ctypes.c_void_p)(
                        ctypes.byref(g), 23, None, ctypes.byref(gestor)) < 0:
                    continue
                if method(gestor, 5, ctypes.c_void_p)(ctypes.byref(lista)) < 0:
                    continue
                cuantas = ctypes.c_int()
                method(lista, 3, ctypes.c_void_p)(ctypes.byref(cuantas))
                for j in range(cuantas.value):
                    ctl = ctypes.c_void_p()
                    if method(lista, 4, ctypes.c_int, ctypes.c_void_p)(j, ctypes.byref(ctl)) < 0:
                        continue
                    ctl2 = _qi(ctl, IID_CONTROL2)
                    _soltar(ctl)
                    if not ctl2:
                        continue
                    try:
                        estado, pid = ctypes.c_int(), w.DWORD()
                        method(ctl2, 3, ctypes.c_void_p)(ctypes.byref(estado))
                        method(ctl2, 14, ctypes.c_void_p)(ctypes.byref(pid))
                        yield ctl2, pid.value, estado.value == ACTIVA
                    finally:
                        _soltar(ctl2)
            finally:
                _soltar(lista, gestor, dev)
    finally:
        _soltar(col, enum)


def _nombre_exe(pid, cache={}):
    """El programa del proceso: el principal si es uno auxiliar (steamwebhelper → steam)."""
    if pid not in cache:
        if len(cache) > 300:
            cache.clear()
        exe = exe_of(pid)
        cache[pid] = principal(exe) if exe else ""
    return cache[pid]


def grabando():
    """Los .exe que ahora mismo graban del micrófono (sin repetir), menos la propia barra."""
    propio, out = os.getpid(), []
    for _, pid, activa in _sesiones(ENTRADA):
        if activa and pid and pid != propio:
            exe = _nombre_exe(pid)
            if exe and exe not in out:
                out.append(exe)
    return out


def _mismo(exe, quiero):
    return os.path.normcase(exe) == os.path.normcase(quiero)


IID_CANALES = "1c158861-b533-4b30-b1cf-e853e51c59b8"


class _Nivel:
    """El volumen de una sesión. Lo normal es ISimpleAudioVolume, pero hay Windows
    que no lo dan para las sesiones de otros procesos: entonces, el de cada canal
    (IChannelAudioVolume), que suena igual aunque el Mezclador no lo enseñe."""

    def __init__(self, ctl):
        self.simple = _qi(ctl, IID_VOLUMEN)
        self.canales = None if self.simple else _qi(ctl, IID_CANALES)

    def __enter__(self):
        return self if (self.simple or self.canales) else None

    def __exit__(self, *_):
        _soltar(self.simple, self.canales)

    def _n(self):
        n = w.UINT()
        method(self.canales, 3, ctypes.c_void_p)(ctypes.byref(n))
        return n.value

    def leer(self):
        f = ctypes.c_float()
        if self.simple:
            ok = method(self.simple, 4, ctypes.c_void_p)(ctypes.byref(f)) >= 0
        else:
            ok = self._n() > 0 and method(self.canales, 5, w.UINT, ctypes.c_void_p)(0, ctypes.byref(f)) >= 0
        return round(f.value * 100) if ok else None

    def poner(self, nivel):
        if self.simple:
            method(self.simple, 3, ctypes.c_float, ctypes.c_void_p)(nivel / 100, None)
            if nivel > 0:
                method(self.simple, 5, w.BOOL, ctypes.c_void_p)(False, None)   # si estaba silenciado, que se oiga
        else:
            n = self._n()
            todos = (ctypes.c_float * n)(*[nivel / 100] * n)
            method(self.canales, 6, w.UINT, ctypes.c_void_p, ctypes.c_void_p)(n, todos, None)


def volumen(exe):
    """El volumen (0-100) con el que suena ese programa, o None si no tiene sonido abierto."""
    for ctl, pid, _ in _sesiones(SALIDA):
        if pid and _mismo(_nombre_exe(pid), exe):
            with _Nivel(ctl) as n:
                if n and n.leer() is not None:
                    return n.leer()
    return None


def cambiar_volumen(exe, paso):
    """Sube o baja (paso en puntos, ±) todas las sesiones de ese programa.
    Devuelve el volumen nuevo (0-100) o None si no tiene sonido abierto."""
    nuevo = None
    for ctl, pid, _ in _sesiones(SALIDA):
        if not pid or not _mismo(_nombre_exe(pid), exe):
            continue
        with _Nivel(ctl) as n:
            if not n:
                continue
            if nuevo is None:              # todas al mismo nivel: el de la primera más el paso
                antes = n.leer()
                if antes is None:
                    continue
                nuevo = max(0, min(100, antes + paso))
            n.poner(nuevo)
    return nuevo
