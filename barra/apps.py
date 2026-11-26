"""Las aplicaciones del menú Inicio, leídas de shell:AppsFolder (lo mismo que Get-StartApps, sin PowerShell).

Cada una es {"nombre", "id"}; se abre con `explorer shell:AppsFolder\\<id>` y su icono sale de win.store_icon(id).
"""
import ctypes
from ctypes import wintypes as w

from .win import GUID, method, ole32, shell32

IID_ISHELLITEM = "43826d1e-e718-42ee-bc55-a1e261c37bfe"
IID_IENUMSHELLITEMS = "70629033-e363-4a28-a567-0db78006e6d7"
BHID_ENUMITEMS = "94f60519-2850-4924-aa5a-d15e84868039"
SIGDN_NORMALDISPLAY, SIGDN_PARENTRELATIVEPARSING = 0, 0x80018001

ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, w.DWORD]
ole32.CoUninitialize.argtypes = []
shell32.SHCreateItemFromParsingName.argtypes = [w.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]


def _texto(item, sigdn):
    p = ctypes.c_void_p()
    if method(item, 5, w.DWORD, ctypes.c_void_p)(sigdn, ctypes.byref(p)) < 0 or not p.value:
        return ""
    try:
        return ctypes.wstring_at(p.value)
    finally:
        ole32.CoTaskMemFree(p)


def leer():
    """[{"nombre", "id"}] ordenadas por nombre. Llamar desde un hilo propio: inicia COM ahí."""
    iniciado = ole32.CoInitializeEx(None, 2) >= 0          # COINIT_APARTMENTTHREADED
    carpeta, enum, out = ctypes.c_void_p(), ctypes.c_void_p(), []
    try:
        iid = GUID(IID_ISHELLITEM)
        if shell32.SHCreateItemFromParsingName("shell:AppsFolder", None, ctypes.byref(iid), ctypes.byref(carpeta)) < 0:
            return out
        bhid, iid_enum = GUID(BHID_ENUMITEMS), GUID(IID_IENUMSHELLITEMS)
        if method(carpeta, 3, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
                None, ctypes.byref(bhid), ctypes.byref(iid_enum), ctypes.byref(enum)) < 0:
            return out
        siguiente = method(enum, 3, w.ULONG, ctypes.c_void_p, ctypes.c_void_p)
        vistos = set()
        while True:
            hijo, n = ctypes.c_void_p(), w.ULONG()
            if siguiente(1, ctypes.byref(hijo), ctypes.byref(n)) != 0 or not n.value:
                break
            try:
                nombre, ident = _texto(hijo, SIGDN_NORMALDISPLAY).strip(), _texto(hijo, SIGDN_PARENTRELATIVEPARSING)
            finally:
                method(hijo, 2)()
            if nombre and ident and (nombre, ident) not in vistos:
                vistos.add((nombre, ident))
                out.append({"nombre": nombre, "id": ident})
    finally:
        for p in (enum, carpeta):
            if p.value:
                method(p, 2)()
        if iniciado:
            ole32.CoUninitialize()
    return sorted(out, key=lambda a: a["nombre"].lower())
