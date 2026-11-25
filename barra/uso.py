"""Uso de Claude, calculado por los propios scripts de Claudito. Proceso aparte
y de solo lectura: no escribe en su carpeta ni en su caché.

Imprime {"hoy": tokens escritos hoy, "limites": [[nombre, porcentaje, reinicio]]}
"""
import json
import os
import sys

sys.dont_write_bytecode = True
RAIZ = os.path.join(os.path.expanduser("~"), "src", "claudito", "windows")


def main():
    sys.path.insert(0, RAIZ)
    import compat
    compat.setup_env()
    import limits
    mod = compat.load_usage()
    mod.write_json = lambda *a, **k: None
    datos = {"live": mod.live()}
    datos.update(mod.totals(mod.transcripts()))
    print(json.dumps({"hoy": datos["periods"]["today"]["out"], "limites": limits.rows(datos)}))


if __name__ == "__main__":
    main()
