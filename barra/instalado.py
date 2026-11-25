"""Lo que el instalador necesita hacer con la barra (installer/windows-bar.iss).

    python instalado.py --parar              cierra la barra que haya y devuelve la de Windows
    python instalado.py --arranque si|no     arrancar esta copia con Windows
    python instalado.py --quitar             antes de desinstalar esta copia
"""
import json
import os
import shutil
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from barra import arranque, vigilante, win  # noqa: E402


def pid_abierta():
    try:
        with open(os.path.join(vigilante.carpeta(), "pid.json"), encoding="utf-8") as f:
            return int(json.load(f)["pid"])
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def es_de(exe, raiz):
    """¿Ese programa está dentro de esa carpeta?"""
    return os.path.normcase(os.path.abspath(exe)).startswith(os.path.normcase(os.path.abspath(raiz)) + os.sep) if exe else False


def parar():
    vigilante.restaurar()
    time.sleep(2)               # el vigilante y la bandeja se cierran solos tras ella
    win.show_taskbars()


def quitar():
    pid = pid_abierta()
    # Otra copia, como la del código, sigue abierta.
    if not pid or es_de(win.exe_of(pid), RAIZ) or not win.exe_of(pid):
        parar()
    if arranque.guardado() == arranque.orden():
        arranque.poner(False)
    shutil.rmtree(os.path.join(vigilante.carpeta(), "actualizacion"), ignore_errors=True)


if __name__ == "__main__":
    if "--parar" in sys.argv:
        parar()
    if "--arranque" in sys.argv:
        si = sys.argv[sys.argv.index("--arranque") + 1] == "si"
        if si or arranque.guardado() == arranque.orden():      # la de otra copia no se toca
            arranque.poner(si)
    if "--quitar" in sys.argv:
        quitar()
