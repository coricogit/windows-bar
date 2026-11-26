"""Red y batería para el botón de ajustes rápidos, sin dependencias.

- Wi-Fi: wlanapi (nombre y señal de la conexión actual).
- Internet: INetworkListManager::GetConnectivity.
- Batería: GetSystemPowerStatus.
"""
import ctypes
from ctypes import wintypes as w

from .win import GUID, method, ole32

kernel32 = ctypes.WinDLL("kernel32")
try:
    _wlan = ctypes.WinDLL("wlanapi")
except OSError:                 # Windows sin el servicio de Wi-Fi
    _wlan = None


class WLAN_INTERFACE_INFO(ctypes.Structure):
    _fields_ = [("guid", GUID), ("descripcion", w.WCHAR * 256), ("estado", ctypes.c_int)]


class WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
    _fields_ = [("n", w.DWORD), ("i", w.DWORD), ("lista", WLAN_INTERFACE_INFO * 1)]


class DOT11_SSID(ctypes.Structure):
    _fields_ = [("largo", w.ULONG), ("ssid", ctypes.c_ubyte * 32)]


class WLAN_CONNECTION_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("estado", ctypes.c_int), ("modo", ctypes.c_int), ("perfil", w.WCHAR * 256),
                ("ssid", DOT11_SSID), ("tipo_bss", ctypes.c_int), ("bssid", ctypes.c_ubyte * 6),
                ("phy", ctypes.c_int), ("phy_i", w.ULONG), ("senal", w.ULONG), ("rx", w.ULONG), ("tx", w.ULONG)]


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [("enchufe", ctypes.c_ubyte), ("marcas", ctypes.c_ubyte), ("porcentaje", ctypes.c_ubyte),
                ("ahorro", ctypes.c_ubyte), ("vida", w.DWORD), ("total", w.DWORD)]


if _wlan:
    _wlan.WlanOpenHandle.argtypes = (w.DWORD, ctypes.c_void_p, ctypes.POINTER(w.DWORD), ctypes.POINTER(w.HANDLE))
    _wlan.WlanEnumInterfaces.argtypes = (w.HANDLE, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
    _wlan.WlanQueryInterface.argtypes = (w.HANDLE, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p,
                                         ctypes.POINTER(w.DWORD), ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p)
    _wlan.WlanFreeMemory.argtypes = (ctypes.c_void_p,)


def bateria():
    """(porcentaje, cargando) o None si no hay batería."""
    s = SYSTEM_POWER_STATUS()
    if not kernel32.GetSystemPowerStatus(ctypes.byref(s)) or s.marcas & 128 or s.marcas == 255 or s.porcentaje > 100:
        return None
    return s.porcentaje, s.enchufe == 1


def glifo_bateria(pct, cargando):
    n = max(0, min(10, round(pct / 10)))
    return chr((0xEBAB if cargando else 0xEBA0) + n)


def glifo_red(r):
    if r["tipo"] == "wifi":
        if not r["internet"]:
            return ""
        return "" if r["senal"] >= 75 else "" if r["senal"] >= 50 else "" if r["senal"] >= 25 else ""
    if r["tipo"] == "cable":
        return "" if r["internet"] else ""
    return ""


class Red:
    def __init__(self):
        self._h = w.HANDLE()
        if _wlan:
            v = w.DWORD()
            if _wlan.WlanOpenHandle(2, None, ctypes.byref(v), ctypes.byref(self._h)) != 0:
                self._h = w.HANDLE()
        self._nlm = None

    def _wifi(self):
        """(nombre, señal) de la conexión Wi-Fi, o None."""
        if not self._h:
            return None
        lista = ctypes.c_void_p()
        if _wlan.WlanEnumInterfaces(self._h, None, ctypes.byref(lista)) != 0:
            return None
        try:
            n = ctypes.cast(lista, ctypes.POINTER(w.DWORD))[0]
            info = ctypes.cast(ctypes.c_void_p(lista.value + 8), ctypes.POINTER(WLAN_INTERFACE_INFO * n)).contents
            for i in info:
                if i.estado != 1:                      # wlan_interface_state_connected
                    continue
                datos, tam = ctypes.c_void_p(), w.DWORD()
                if _wlan.WlanQueryInterface(self._h, ctypes.byref(i.guid), 7, None, ctypes.byref(tam),
                                            ctypes.byref(datos), None) != 0:
                    continue
                try:
                    a = ctypes.cast(datos, ctypes.POINTER(WLAN_CONNECTION_ATTRIBUTES)).contents
                    nombre = bytes(a.ssid.ssid[:min(a.ssid.largo, 32)]).decode("utf-8", "replace")
                    return nombre or a.perfil, int(a.senal)
                finally:
                    _wlan.WlanFreeMemory(datos)
        finally:
            _wlan.WlanFreeMemory(lista)
        return None

    def _conectividad(self):
        if self._nlm is None:
            p = ctypes.c_void_p()
            ole32.CoInitializeEx(None, 2)
            if ole32.CoCreateInstance(ctypes.byref(GUID("dcb00c01-570f-4a9b-8d69-199fdba5723b")), None, 1,
                                      ctypes.byref(GUID("dcb00000-570f-4a9b-8d69-199fdba5723b")), ctypes.byref(p)) < 0:
                return None
            self._nlm = p
        c = ctypes.c_int()
        if method(self._nlm, 13, ctypes.POINTER(ctypes.c_int))(ctypes.byref(c)) < 0:
            return None
        return c.value

    def leer(self):
        """{"tipo": "wifi"|"cable"|"no", "internet", "senal", "nombre"}"""
        c = self._conectividad()
        internet = c is None or bool(c & 0x440)        # NLM_CONNECTIVITY_IPV4/IPV6_INTERNET
        wifi = self._wifi()
        if wifi:
            return {"tipo": "wifi", "internet": internet, "senal": wifi[1], "nombre": wifi[0]}
        if c:                         # alguna red, y no es Wi-Fi
            return {"tipo": "cable", "internet": internet, "senal": 100, "nombre": "Ethernet"}
        return {"tipo": "no", "internet": False, "senal": 0, "nombre": ""}
