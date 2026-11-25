"""Trae a claudito/ lo que la barra necesita de Claudito.

    py installer\\copiar_claudito.py [carpeta del repositorio de Claudito]

Son copias exactas de https://github.com/coricogit/claudito (MIT). La barra usa el
Claudito instalado o el del código si los hay; esta copia es para cuando no.
"""
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.expanduser("~"), "src", "claudito")
DIBUJO = "plasma/org.corico.claudito/contents/"
ARCHIVOS = ["LICENSE", "claudito-hook", "claudito-statusline", "claudito-usage", DIBUJO + "ui/Character.qml",
            *(DIBUJO + "code/" + n for n in ("hats.js", "sprites.js", "strings.js")),
            *("windows/" + n for n in ("activity.py", "seasons.py", "compat.py", "limits.py", "install.py",
                                       "claudito_hook.py", "claudito_statusline.py", "requirements.txt"))]

if __name__ == "__main__":
    destino = os.path.join(RAIZ, "claudito")
    shutil.rmtree(destino, ignore_errors=True)
    for n in ARCHIVOS:
        # De git: sin cambios a medias.
        datos = subprocess.run(["git", "-C", ORIGEN, "show", "HEAD:" + n], capture_output=True, check=True).stdout
        ruta = os.path.join(destino, n)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "wb") as f:
            f.write(datos)
    print(len(ARCHIVOS), "archivos en", destino)
