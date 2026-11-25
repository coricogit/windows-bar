"""CPU, memoria, gráfica y volumen, sin dependencias."""
import ctypes
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


class Gpu:
    """Uso de la primera gráfica NVIDIA; None si no hay."""

    def __init__(self):
        self._dev = None
        try:
            self._lib = ctypes.CDLL("nvml.dll")
            dev = ctypes.c_void_p()
            if self._lib.nvmlInit_v2() == 0 and \
                    self._lib.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev)) == 0:
                self._dev = dev
        except (OSError, AttributeError):
            pass

    def percent(self):
        if not self._dev:
            return None
        use = (ctypes.c_uint * 2)()
        return int(use[0]) if self._lib.nvmlDeviceGetUtilizationRates(self._dev, use) == 0 else None


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
