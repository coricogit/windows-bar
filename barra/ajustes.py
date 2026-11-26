"""Los ajustes guardados: valores por defecto y paso de versiones anteriores."""
import copy
import json
import os

from . import tiempo

DEFECTO = {"tema": "tokyo", "formatos": {}, "auto": False, "tema_dia": "bosque", "tema_noche": "tokyo",
           "dia": 8, "noche": 19, "por_programa": {}, "modo_juego": True, "pincel": False,
           "fijados": [], "quitados": [], "alineacion": "windows", "vidrio": "normal", "animaciones": "suaves", "icono": "tema", "agrupar": True,
           "orden": [], "posicion": "abajo", "opacidad": 85, "ocultos": [],
           "actualizar": True, "intentos": "", "atajos": True, "widgets": True, "ciudad": {},
           "cava": True, "iconos": "originales", "esconder": False, "isla": True,
           "buscador": True, "barra_busqueda": True, "lanzados": {}}


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
    if not tiempo.ciudad_valida(a["ciudad"]):
        a["ciudad"] = {}
    a["opacidad"] = max(0, min(100, int(a["opacidad"])))
    a["quitados"] = [q for q in a["quitados"] if isinstance(q, str)]
    a["ocultos"] = list(dict.fromkeys(c for c in a["ocultos"] if isinstance(c, str)))[:MAX_ORDEN]
    a["orden"] = [c for c in a["orden"] if isinstance(c, str)]
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
