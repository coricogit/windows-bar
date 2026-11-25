"""Uso de Claude, calculado por los propios scripts de Claudito. Proceso aparte:
no escribe en la carpeta de Claudito ni en su caché.

Imprime {"hoy", "semana", "mensajes", "limites": [[nombre, porcentaje, reinicio]],
"cuenta": {"plan", "correo"}, "conexion"}. Todo sale de archivos de este equipo.
"""
import json
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from barra import claudito, conectar  # noqa: E402

RAIZ = os.path.join(claudito.RAIZ, "windows")
CACHE = os.path.join(os.environ["LOCALAPPDATA"], "barra-temas", "uso.json")


def elegir_cache(mod, ahora):
    """Con Claudito en marcha, se lee la suya. Si no, una propia: sin caché, cada
    vez habría que leer todas las conversaciones."""
    try:
        reciente = ahora - os.path.getmtime(mod.FILES_CACHE) < 86400
    except OSError:
        reciente = False
    if reciente:
        mod.write_json = lambda *a, **k: None
    else:
        mod.FILES_CACHE = CACHE


def cuenta(compat):
    c = compat.saved_account() or {}
    return {"plan": str(c.get("subscriptionType") or ""), "correo": str(c.get("email") or "")}


def main():
    sys.path.insert(0, RAIZ)
    import compat
    compat.setup_env()
    import limits
    mod = compat.load_usage()
    elegir_cache(mod, time.time())
    datos = {"live": mod.live()}
    datos.update(mod.totals(mod.transcripts()))
    p = datos["periods"]
    print(json.dumps({"hoy": p["today"]["out"], "semana": p["week"]["out"], "mensajes": p["today"]["msgs"],
                      "limites": limits.rows(datos), "cuenta": cuenta(compat), "conexion": conectar.estado()}))


if __name__ == "__main__":
    main()
