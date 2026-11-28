"""Los ajustes guardados: valores por defecto y paso de versiones anteriores."""
import copy
import json
import os

from . import tiempo
from .win import sin_version

DEFECTO = {"tema": "tokyo", "formatos": {}, "auto": False, "tema_dia": "bosque", "tema_noche": "tokyo",
           "dia": 8, "noche": 19, "por_programa": {}, "modo_juego": True, "pincel": False,
           "fijados": [], "quitados": [], "alineacion": "windows", "vidrio": "normal", "animaciones": "suaves", "icono": "tema", "agrupar": True,
           "orden": [], "posicion": "abajo", "opacidad": 85, "ocultos": [],
           "actualizar": True, "intentos": "", "atajos": True, "widgets": True, "ciudad": {},
           "cava": True, "iconos": "originales", "esconder": False, "isla": True,
           "buscador": True, "barra_busqueda": True, "pomodoro": [25, 5], "variantes": {}, "lanzados": {}, "arranque": "",
           "pantallas": "suya", "vista_tareas": True, "integrado": False,
           "sistema": True, "claudito": True, "medidores": ["cpu", "ram", "gpu"], "medidores_mini": False, "concentrar_pomodoro": True, "disenos": {},
           "menus": "barra"}


def normalizar(d, temas, formatos):
    """Ajustes completos y válidos a partir de lo leído del disco."""
    a = copy.deepcopy(DEFECTO)
    if isinstance(d, dict):
        a.update({k: v for k, v in d.items() if k in DEFECTO and isinstance(v, type(DEFECTO[k]))})
    for k in ("tema", "tema_dia", "tema_noche"):       # puede ser uno ya retirado
        if a[k] not in temas:
            a[k] = DEFECTO[k] if DEFECTO[k] in temas else next(iter(temas))
    # Antes el formato era uno para todos: pasa a ser el del tema elegido.
    viejo = d.get("formato") if isinstance(d, dict) else None
    if viejo in formatos and viejo != "tema":
        a["formatos"].setdefault(a["tema"], viejo)
    a["formatos"] = {t: f for t, f in a["formatos"].items() if t in temas and f in formatos}
    a["fijados"] = [f for f in a["fijados"] if isinstance(f, dict) and f.get("clave") and f.get("exe")]
    for f in a["fijados"]:
        f["clave"] = sin_version(f["clave"])
    if not tiempo.ciudad_valida(a["ciudad"]):
        a["ciudad"] = {}
    a["opacidad"] = max(0, min(100, int(a["opacidad"])))
    a["quitados"] = list(dict.fromkeys(sin_version(q) for q in a["quitados"] if isinstance(q, str)))
    a["ocultos"] = list(dict.fromkeys(c for c in a["ocultos"] if isinstance(c, str)))[:MAX_ORDEN]
    a["orden"] = list(dict.fromkeys(sin_version(c) for c in a["orden"] if isinstance(c, str)))
    a["medidores"] = [m for m in ("cpu", "ram", "gpu") if m in a["medidores"]]
    a["disenos"] = {k: v for k, v in a["disenos"].items() if isinstance(v, str)}
    return a


def leer(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def guardar(ruta, a):
    with open(ruta + ".tmp", "w", encoding="utf-8") as f:
        json.dump(a, f, indent=2, ensure_ascii=False)
    os.replace(ruta + ".tmp", ruta)


def fijar(a, entrada, de_windows):
    """Ancla un programa. `de_windows`: claves ancladas en la barra de Windows."""
    clave = entrada["clave"]
    a["quitados"] = [q for q in a["quitados"] if q != clave]
    if clave not in de_windows and all(f["clave"] != clave for f in a["fijados"]):
        a["fijados"].append(entrada)


def familia_paquete(exe):
    r"""De ...\WindowsApps\Microsoft.WindowsTerminal_1.25.3131.0_x64__8wekyb3d8bbwe\x.exe
    saca "Microsoft.WindowsTerminal_8wekyb3d8bbwe" (nombre y editor, sin versión)."""
    partes = exe.replace("/", "\\").split("\\")
    for i, p in enumerate(partes[:-1]):
        if p.lower() == "windowsapps" and i + 1 < len(partes) - 1:
            trozos = partes[i + 1].split("_")
            return trozos[0] + "_" + trozos[-1] if len(trozos) >= 5 else ""
    return ""


def reparar_fijados(a, leer_apps):
    """Los anclados de la Tienda guardados sin su identificador (por ejemplo
    Windows Terminal, que no lo pone en su ventana) apuntan a una carpeta con
    versión que desaparece al actualizarse: se les busca el identificador.
    `leer_apps` da [{"id", ...}] y solo se llama si hace falta."""
    rotos = [f for f in a["fijados"] if not f.get("ruta") and familia_paquete(f["exe"])]
    if not rotos:
        return False
    ids = [x["id"] for x in leer_apps()]
    cambiado = False
    for f in rotos:
        familia = familia_paquete(f["exe"]).lower() + "!"
        candidatos = [i for i in ids if i.lower().startswith(familia)]
        if candidatos:
            f["ruta"] = "shell:AppsFolder\\" + candidatos[0]
            cambiado = True
    return cambiado


def soltar(a, clave, de_windows):
    """Lo desancla de esta barra; la de Windows no cambia."""
    a["fijados"] = [f for f in a["fijados"] if f["clave"] != clave]
    if clave in de_windows and clave not in a["quitados"]:
        a["quitados"].append(clave)


MAX_ORDEN = 200


def fusionar_orden(guardado, visibles):
    """El orden guardado, con los programas a la vista como los acaban de dejar.
    Los que ahora no se ven siguen detrás del mismo vecino."""
    detras, vecino = {}, None
    for c in guardado:
        if c in visibles:
            vecino = c
        else:
            detras.setdefault(vecino, []).append(c)
    out = list(detras.get(None, []))
    for c in visibles:
        out += [c, *detras.get(c, [])]
    sobran = len(out) - MAX_ORDEN
    if sobran > 0:                 # olvidar primero los que no se ven
        ocultos = set([c for c in out if c not in visibles][-sobran:])
        out = [c for c in out if c not in ocultos][:MAX_ORDEN]
    return out


def lista_fijos(a, de_windows):
    """Los anclados que tocan, en orden. `de_windows` es [{"clave", ...}]."""
    return [f for f in de_windows if f["clave"] not in a["quitados"]] + a["fijados"]
