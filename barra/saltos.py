"""Listas de saltos: lo que la barra de Windows enseña con el clic derecho.

Todo se lee desde este proceso, con las interfaces del propio Windows y los
archivos de la carpeta Recent; nada se inyecta en Explorer.
- El identificador de la app sale de IApplicationResolver (sin documentar,
  pero es COM dentro de este proceso).
- Los recientes, de IApplicationDocumentLists.
- Las tareas y categorías propias ("Nueva ventana"...), de
  CustomDestinations\\<crc64 del identificador>.customDestinations-ms, que
  guarda accesos directos enteros, uno detrás de otro.
"""
import ctypes
import os
import struct
import uuid
import winreg
from ctypes import wintypes as w

from .win import GUID, PROPERTYKEY, PROPVARIANT, method, ole32, shell32

_P = ctypes.POINTER
RECIENTES = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Recent")
SHELLLINK = uuid.UUID("00021401-0000-0000-c000-000000000046").bytes_le
FIN = 0xBABFFBAB
MAX_ARCHIVO = 2_000_000

ole32.CoTaskMemFree.argtypes = (ctypes.c_void_p,)
shell32.SHCreateItemFromParsingName.argtypes = (w.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
_shlwapi = ctypes.WinDLL("shlwapi")
_shlwapi.SHCreateMemStream.restype = ctypes.c_void_p
_shlwapi.SHCreateMemStream.argtypes = (ctypes.c_char_p, w.UINT)
_shlwapi.SHLoadIndirectString.argtypes = (w.LPCWSTR, w.LPWSTR, w.UINT, ctypes.c_void_p)


def mostrar_recientes():
    """Lo que dice Windows en Personalización > Inicio > recientes."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced") as k:
            return bool(winreg.QueryValueEx(k, "Start_TrackDocs")[0])
    except OSError:
        return True


def crc64(texto):
    """El nombre de archivo de las listas de una app (CRC-64 del
    identificador en mayúsculas y UTF-16, el que usa Windows)."""
    crc = 0xFFFFFFFFFFFFFFFF
    for b in texto.upper().encode("utf-16-le"):
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0x92C64265D32139A4 if crc & 1 else crc >> 1
    return "%016x" % crc


def _crear(clsid, iid):
    p = ctypes.c_void_p()
    ole32.CoInitializeEx(None, 2)
    if ole32.CoCreateInstance(ctypes.byref(GUID(clsid)), None, 1, ctypes.byref(GUID(iid)), ctypes.byref(p)) < 0:
        return None
    return p


def _soltar(p):
    if p:
        method(p, 2)()


def _texto(p):
    if not p.value:
        return ""
    t = ctypes.wstring_at(p.value)
    ole32.CoTaskMemFree(p)
    return t


def _resolver():
    return _crear("660b90c8-73a9-4b58-8cae-355b7f55341b", "de25675a-72de-44b4-9373-05170450c140")


def id_de_ventana(hwnd):
    r = _resolver()
    if not r:
        return ""
    try:
        s, b = ctypes.c_void_p(), [w.BOOL() for _ in range(3)]
        hr = method(r, 5, w.HWND, _P(ctypes.c_void_p), *[_P(w.BOOL)] * 3)(
            w.HWND(hwnd), ctypes.byref(s), *[ctypes.byref(x) for x in b])
        return _texto(s) if hr >= 0 else ""
    finally:
        _soltar(r)


def id_de_acceso(ruta):
    """El identificador de un acceso directo (.lnk) anclado."""
    if ruta.lower().startswith("shell:appsfolder\\"):
        return ruta.split("\\", 1)[1]
    item = ctypes.c_void_p()
    if shell32.SHCreateItemFromParsingName(ruta, None, ctypes.byref(GUID("43826d1e-e718-42ee-bc55-a1e261c37bfe")),
                                           ctypes.byref(item)) < 0:
        return ""
    r = _resolver()
    try:
        s = ctypes.c_void_p()
        if r and method(r, 3, ctypes.c_void_p, _P(ctypes.c_void_p))(item, ctypes.byref(s)) >= 0:
            return _texto(s)
        return ""
    finally:
        _soltar(r)
        _soltar(item)


def recientes(appid, cuantos=8):
    """Rutas de los archivos recientes de la app, el más nuevo primero."""
    if not appid:
        return []
    adl = _crear("86bec222-30f2-47e0-9f25-60d11cd75c28", "3c594f9f-9f30-47a1-979a-c9e83d3d0a06")
    if not adl:
        return []
    arr, out = ctypes.c_void_p(), []
    try:
        if method(adl, 3, w.LPCWSTR)(appid) < 0:
            return []
        if method(adl, 4, ctypes.c_int, w.UINT, ctypes.c_void_p, _P(ctypes.c_void_p))(
                0, cuantos, ctypes.byref(GUID("92ca9dcd-5622-4bba-a805-5e9f541bd8c9")), ctypes.byref(arr)) < 0:
            return []
        n = w.UINT()
        method(arr, 3, _P(w.UINT))(ctypes.byref(n))
        for i in range(n.value):
            it = ctypes.c_void_p()
            if method(arr, 4, w.UINT, ctypes.c_void_p, _P(ctypes.c_void_p))(
                    i, ctypes.byref(GUID("43826d1e-e718-42ee-bc55-a1e261c37bfe")), ctypes.byref(it)) < 0:
                continue
            s = ctypes.c_void_p()
            if method(it, 5, ctypes.c_int, _P(ctypes.c_void_p))(0x80058000 - (1 << 32), ctypes.byref(s)) >= 0:
                ruta = _texto(s)
                if ruta:
                    out.append(ruta)
            _soltar(it)
        return out
    finally:
        _soltar(arr)
        _soltar(adl)


def trozos(datos):
    """[(categoría, [lnk en bruto, ...])] de un .customDestinations-ms.
    Categoría "" son las tareas; las conocidas de Windows (recientes,
    frecuentes) no guardan nada aquí y se saltan."""
    out, i = [], 12
    try:
        version, = struct.unpack_from("<I", datos, 0)
        if version != 2:
            return []
        while i + 4 <= len(datos):
            tipo, = struct.unpack_from("<I", datos, i)
            i += 4
            if tipo == 1:                         # categoría de Windows: solo su número
                i += 4
                nombre = None
            elif tipo == 0:
                largo, = struct.unpack_from("<H", datos, i)
                nombre = datos[i + 2:i + 2 + 2 * largo].decode("utf-16-le", "replace")
                i += 2 + 2 * largo
            elif tipo == 2:
                nombre = ""
            else:
                break
            if nombre is None:
                fin, = struct.unpack_from("<I", datos, i)
                i += 4 if fin == FIN else 0
                continue
            cuantos, = struct.unpack_from("<I", datos, i)
            i += 4
            # Cada entrada: su CLSID y el contenido; el final de una es el
            # principio de la siguiente (o la marca de fin de categoría).
            lnks = []
            for _ in range(cuantos):
                if datos[i:i + 16] != SHELLLINK:
                    return out                  # un objeto que no es acceso directo: no se sabe saltarlo
                sig = datos.find(SHELLLINK + b"\x4c\x00\x00\x00", i + 16)
                fin = datos.find(struct.pack("<I", FIN), i + 16)
                hasta = min(x for x in (sig, fin, len(datos)) if x >= 0) if len(lnks) + 1 < cuantos else \
                    (fin if fin >= 0 else len(datos))
                lnks.append(datos[i + 16:hasta])
                i = hasta
            if datos[i:i + 4] == struct.pack("<I", FIN):
                i += 4
            out.append((nombre, lnks))
    except struct.error:
        pass
    return out


def _leer_lnk(datos):
    """{"titulo", "ruta", "args", "carpeta"} de un acceso directo en bruto."""
    link = _crear("00021401-0000-0000-c000-000000000046", "000214f9-0000-0000-c000-000000000046")
    if not link:
        return None
    flujo = _shlwapi.SHCreateMemStream(datos, len(datos))
    persist = ctypes.c_void_p()
    store = ctypes.c_void_p()
    try:
        if not flujo or method(link, 0, ctypes.c_void_p, _P(ctypes.c_void_p))(
                ctypes.byref(GUID("00000109-0000-0000-c000-000000000046")), ctypes.byref(persist)) < 0:
            return None
        if method(persist, 5, ctypes.c_void_p)(flujo) < 0:          # IPersistStream::Load
            return None
        buf = ctypes.create_unicode_buffer(1024)
        method(link, 3, w.LPWSTR, ctypes.c_int, ctypes.c_void_p, w.DWORD)(buf, 1024, None, 0x4)   # SLGP_RAWPATH
        ruta = buf.value
        method(link, 10, w.LPWSTR, ctypes.c_int)(buf, 1024)
        args = buf.value
        method(link, 8, w.LPWSTR, ctypes.c_int)(buf, 1024)
        carpeta = buf.value
        titulo = ""
        if method(link, 0, ctypes.c_void_p, _P(ctypes.c_void_p))(
                ctypes.byref(GUID("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99")), ctypes.byref(store)) >= 0:
            key = PROPERTYKEY(GUID("f29f85e0-4ff9-1068-ab91-08002b27b3d9"), 2)       # PKEY_Title
            var = PROPVARIANT()
            if method(store, 5, ctypes.c_void_p, ctypes.c_void_p)(ctypes.byref(key), ctypes.byref(var)) >= 0:
                titulo = ctypes.wstring_at(var.p) if var.vt == 31 and var.p else ""
                ole32.PropVariantClear(ctypes.byref(var))
        if titulo.startswith(("@", "ms-resource:")):
            fuera = ctypes.create_unicode_buffer(512)
            titulo = fuera.value if _shlwapi.SHLoadIndirectString(titulo, fuera, 512, None) >= 0 else ""
        if not titulo:
            method(link, 6, w.LPWSTR, ctypes.c_int)(buf, 1024)       # la descripción
            titulo = buf.value
        if not ruta or not titulo:
            return None                        # los separadores son accesos vacíos
        return {"titulo": titulo, "ruta": os.path.expandvars(ruta), "args": args,
                "carpeta": os.path.expandvars(carpeta)}
    finally:
        for p in (store, persist, link):
            _soltar(p)
        if flujo:
            method(ctypes.c_void_p(flujo), 2)()


def tareas(appid):
    """[(categoría, [{"titulo", "ruta", "args", "carpeta"}])] de la app."""
    if not appid:
        return []
    ruta = os.path.join(RECIENTES, "CustomDestinations", crc64(appid) + ".customDestinations-ms")
    try:
        if os.path.getsize(ruta) > MAX_ARCHIVO:
            return []
        with open(ruta, "rb") as f:
            datos = f.read()
    except OSError:
        return []
    out = []
    for nombre, lnks in trozos(datos):
        cosas = [x for x in map(_leer_lnk, lnks) if x]
        if cosas:
            out.append((nombre, cosas))
    return out
