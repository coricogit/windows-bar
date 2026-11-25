"""Qué programa hay detrás de una ventana y cómo se llama de verdad."""
import ctypes
import os
import re
from ctypes import wintypes as w

from . import win

_ver = ctypes.WinDLL("version")
# Procesos auxiliares que muestran las ventanas de otro programa.
AUXILIARES = {"steamwebhelper.exe": "steam.exe"}
_nombres = {}


def principal(exe):
    """El programa al que pertenece ese ejecutable (casi siempre, él mismo)."""
    jefe = AUXILIARES.get(os.path.basename(exe).lower())
    carpeta = os.path.dirname(exe)
    for _ in range(5):
        if not jefe or len(carpeta) < 4:
            break
        ruta = os.path.join(carpeta, jefe)
        if os.path.exists(ruta):
            return ruta
        carpeta = os.path.dirname(carpeta)
    return exe


GENERICOS = ("", "explorer.exe", "python.exe", "pythonw.exe", "javaw.exe", "rundll32.exe")


def clave_bandeja(exe, guid, tip):
    """Identifica un icono de la bandeja entre sesiones. Vale el nombre del
    archivo (la carpeta cambia al actualizarse), salvo en los que sirven a
    varios programas: ahí, además, su GUID o el principio de su texto."""
    base = os.path.basename(exe).lower()
    if base not in GENERICOS:
        return base
    return base + ":" + (guid or re.split(r"[\n:·—|(-]|\d", tip, maxsplit=1)[0].strip().lower())


def _datos(ruta):
    """(descripción, producto) del archivo, en el idioma de Windows."""
    n = _ver.GetFileVersionInfoSizeW(ctypes.c_wchar_p(ruta), None)
    if not n:
        return "", ""
    b = ctypes.create_string_buffer(n)
    p, largo = ctypes.c_void_p(), w.UINT()
    if not _ver.GetFileVersionInfoW(ctypes.c_wchar_p(ruta), 0, n, b) or not _ver.VerQueryValueW(
            b, ctypes.c_wchar_p(r"\VarFileInfo\Translation"), ctypes.byref(p), ctypes.byref(largo)) or largo.value < 4:
        return "", ""
    idioma, pagina = ctypes.cast(p, ctypes.POINTER(w.WORD))[0:2]
    out = []
    for campo in ("FileDescription", "ProductName"):
        clave = rf"\StringFileInfo\{idioma:04x}{pagina:04x}" + "\\" + campo
        ok = _ver.VerQueryValueW(b, ctypes.c_wchar_p(clave), ctypes.byref(p), ctypes.byref(largo))
        out.append(ctypes.wstring_at(p.value).strip() if ok and p.value and largo.value else "")
    return tuple(out)


def elegir(descripcion, producto, archivo):
    """El mejor nombre: la descripción, o el producto si es su versión corta."""
    if producto and len(producto) < len(descripcion) and descripcion.lower().startswith(producto.lower()):
        return producto
    if descripcion and len(descripcion) <= 60:
        return descripcion
    base = os.path.splitext(archivo)[0]
    return base[:1].upper() + base[1:]


def nombre(exe):
    if exe not in _nombres:
        try:
            datos = _datos(exe) if exe else ("", "")
        except (OSError, ValueError):
            datos = ("", "")
        _nombres[exe] = elegir(*datos, os.path.basename(exe))
    return _nombres[exe]


def nombre_tienda(ident):
    """El nombre de una app de la Tienda, o ""."""
    if ident not in _nombres:
        _nombres[ident] = ""
        item, iid = ctypes.c_void_p(), win.GUID("43826d1e-e718-42ee-bc55-a1e261c37bfe")       # IShellItem
        if win.shell32.SHCreateItemFromParsingName(ctypes.c_wchar_p("shell:AppsFolder\\" + ident), None,
                                                   ctypes.byref(iid), ctypes.byref(item)) >= 0:
            texto = ctypes.c_void_p()
            if win.method(item, 5, ctypes.c_int, ctypes.c_void_p)(0, ctypes.byref(texto)) >= 0 and texto.value:
                _nombres[ident] = ctypes.wstring_at(texto.value)
                win.ole32.CoTaskMemFree(texto)
            win.method(item, 2)()
    return _nombres[ident]


def agrupar(info, fijos, juntar, orden, elegido=()):
    """Las filas de la barra a partir de las ventanas `info` ({"hwnd", "clave",
    "nombre", "titulo", "icono", "activa", "minimizada", "exe", "z"}) y de los
    anclados. `orden` recuerda cuándo se vio cada programa, para no moverlos;
    `elegido` es el orden puesto a mano y manda sobre todo."""
    for i in sorted(info, key=lambda i: i["hwnd"]):
        orden.setdefault(i["clave"], len(orden))
    por_clave = {}
    for i in sorted(info, key=lambda i: i["hwnd"]):
        por_clave.setdefault(i["clave"], []).append(i)

    def fila(key, vs):
        cerca = min(vs, key=lambda v: v["z"])            # la usada más recientemente
        varias = len(vs) > 1
        return {"key": key, "clave": vs[0]["clave"], "titulo": vs[0]["nombre"] if varias else cerca["titulo"], "nombre": vs[0]["nombre"],
                "icono": vs[0]["icono"], "activa": any(v["activa"] for v in vs),
                "minimizada": all(v["minimizada"] for v in vs), "abierta": True, "hwnd": str(cerca["hwnd"]),
                "exe": vs[0]["exe"], "ruta": "", "cuenta": len(vs), "ventanas": [v["hwnd"] for v in vs],
                "titulos": [v["titulo"] for v in vs]}

    def filas_de(clave):
        vs = por_clave[clave]
        return [fila("g:" + clave, vs)] if juntar else [fila(str(v["hwnd"]), [v]) for v in vs]

    out, puestas = [], set()
    for x in fijos:
        puestas.add(x["clave"])
        if x["clave"] in por_clave:
            out.extend(filas_de(x["clave"]))
        else:
            out.append({"key": ("g:" if juntar else "fijo-") + x["clave"], "clave": x["clave"],
                        "titulo": x["nombre"],
                        "nombre": x["nombre"], "icono": x["icono"], "activa": False, "minimizada": False,
                        "abierta": False, "hwnd": "", "exe": x["exe"], "ruta": x["ruta"], "cuenta": 0,
                        "ventanas": [], "titulos": []})
    for clave in sorted((k for k in por_clave if k not in puestas), key=orden.get):
        out.extend(filas_de(clave))
    puesto = {c: i for i, c in enumerate(elegido)}
    out.sort(key=lambda f: puesto.get(f["clave"], len(puesto)))       # estable: el resto, como estaba
    return out
