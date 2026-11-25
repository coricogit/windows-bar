"""Los ajustes guardados: valores por defecto y paso de versiones anteriores."""
import copy
import json
import os

DEFECTO = {"tema": "tokyo", "formatos": {}, "auto": False, "tema_dia": "bosque", "tema_noche": "tokyo",
           "dia": 8, "noche": 19, "por_programa": {}, "modo_juego": True, "pincel": False,
           "fijados": [], "quitados": [], "alineacion": "windows", "vidrio": "normal"}


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
    a["quitados"] = [q for q in a["quitados"] if isinstance(q, str)]
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


def lista_fijos(a, de_windows):
    """Los anclados que tocan, en orden. `de_windows` es [{"clave", ...}]."""
    return [f for f in de_windows if f["clave"] not in a["quitados"]] + a["fijados"]
