"""CPU, memoria, gráfica y volumen, sin dependencias."""
import ctypes
import struct
import time
from ctypes import wintypes as w

from .win import GUID, kernel32, method, ole32


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", w.DWORD), ("dwMemoryLoad", w.DWORD)] + [
        (n, ctypes.c_ulonglong) for n in "a b c d e f g".split()]


class Cpu:
    def __init__(self):
        self._old = self._times()

    @staticmethod
    def _times():
        idle, kern, user = w.FILETIME(), w.FILETIME(), w.FILETIME()
        kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user))
        i, k, u = ((t.dwHighDateTime << 32) | t.dwLowDateTime for t in (idle, kern, user))
        return i, k + u          # el tiempo de núcleo ya incluye el inactivo

    def percent(self):
        new = self._times()
        idle, total = new[0] - self._old[0], new[1] - self._old[1]
        self._old = new
        return round(100 * (total - idle) / total) if total > 0 else 0


def ram_percent():
    m = MEMORYSTATUSEX(dwLength=ctypes.sizeof(MEMORYSTATUSEX))
    kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return int(m.dwMemoryLoad)


class LUID(ctypes.Structure):
    _fields_ = [("lo", w.DWORD), ("hi", w.LONG)]


class ADAPTERINFO(ctypes.Structure):
    _fields_ = [("h", w.UINT), ("luid", LUID), ("fuentes", w.ULONG), ("preciso", w.BOOL)]


class ENUMADAPTERS2(ctypes.Structure):
    _fields_ = [("n", w.ULONG), ("lista", ctypes.POINTER(ADAPTERINFO))]


class QUERYSTATISTICS(ctypes.Structure):
    _fields_ = [("tipo", ctypes.c_int), ("luid", LUID), ("proceso", ctypes.c_void_p),
                ("res", ctypes.c_ubyte * 776), ("nodo", w.ULONG), ("_", w.ULONG)]


class Gpu:
    """Uso de la gráfica, de cualquier marca: el del motor más ocupado, como en
    el Administrador de tareas. Se lo pregunta a Windows; nvml.dll gasta 20 MB."""

    def __init__(self):
        self._nodos, self._old, self._cuando = [], {}, 0
        try:
            self._g = ctypes.WinDLL("gdi32")
            e = ENUMADAPTERS2()
            if self._g.D3DKMTEnumAdapters2(ctypes.byref(e)) != 0:
                return
            lista = (ADAPTERINFO * e.n)()
            e.lista = lista
            if self._g.D3DKMTEnumAdapters2(ctypes.byref(e)) != 0:
                return
            for ad in lista[:e.n]:
                datos = self._pedir(ad.luid, 0, 0)
                if datos:
                    self._nodos += [(ad.luid, i) for i in range(min(struct.unpack_from("<II", datos)[1], 32))]
                self._g.D3DKMTCloseAdapter(ctypes.byref(w.UINT(ad.h)))
            self.percent()
        except (OSError, AttributeError):
            self._nodos = []

    def _pedir(self, luid, tipo, nodo):
        q = QUERYSTATISTICS(tipo=tipo, luid=luid, nodo=nodo)
        return bytes(q.res[:16]) if self._g.D3DKMTQueryStatistics(ctypes.byref(q)) == 0 else None

    def percent(self):
        if not self._nodos:
            return None
        ahora, nuevo = time.perf_counter(), {}
        for luid, i in self._nodos:
            datos = self._pedir(luid, 5, i)
            if datos:
                nuevo[luid.lo, i] = struct.unpack_from("<q", datos)[0]
        pasado = (ahora - self._cuando) * 1e7         # en unidades de 100 ns
        uso = max((100 * (v - self._old[k]) / pasado for k, v in nuevo.items() if k in self._old), default=0)
        self._old, self._cuando = nuevo, ahora
        return max(0, min(100, round(uso)))


class Volume:
    """Volumen de la salida de sonido predeterminada."""

    def __init__(self):
        ole32.CoInitializeEx(None, 2)     # el hilo de la interfaz ya es STA

    def read(self):
        """(porcentaje, silenciado), o None."""
        enum = ctypes.c_void_p()
        clsid, iid = GUID("bcde0395-e52f-467c-8e3d-c4579291692e"), GUID("a95664d2-9614-4f35-a746-de8db63617e6")
        if ole32.CoCreateInstance(ctypes.byref(clsid), None, 23, ctypes.byref(iid), ctypes.byref(enum)) < 0:
            return None
        dev, vol = ctypes.c_void_p(), ctypes.c_void_p()
        try:
            if method(enum, 4, ctypes.c_int, ctypes.c_int, ctypes.c_void_p)(0, 1, ctypes.byref(dev)) < 0:
                return None
            iid = GUID("5cdf2c82-841e-4546-9722-0cf74078229a")
            if method(dev, 3, ctypes.c_void_p, w.DWORD, ctypes.c_void_p, ctypes.c_void_p)(
                    ctypes.byref(iid), 23, None, ctypes.byref(vol)) < 0:
                return None
            level, mute = ctypes.c_float(), w.BOOL()
            method(vol, 9, ctypes.c_void_p)(ctypes.byref(level))
            method(vol, 15, ctypes.c_void_p)(ctypes.byref(mute))
            return round(level.value * 100), bool(mute.value)
        finally:
            for obj in (vol, dev, enum):
                if obj:
                    method(obj, 2)()
