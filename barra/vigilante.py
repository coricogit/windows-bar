"""Vigilante: devuelve la barra de Windows si la nuestra se cierra o se cuelga.

Proceso aparte. La barra le escribe un latido por segundo; si se cierra la
tubería, o pasan SILENCIO segundos sin latidos, muestra la barra de Windows.
Ctrl+Alt+Mayús+B cierra la barra a la fuerza y la devuelve al momento.

    py vigilante.py --restaurar     cierra la barra (si está) y devuelve la de Windows
"""
import ctypes
import json
import os
import sys
import threading
import time
from ctypes import wintypes as w

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from barra import win  # noqa: E402

SILENCIO = 8
MOD = 1 | 2 | 4 | 0x4000      # Alt, Ctrl, Mayús, sin repetición
WM_HOTKEY, WM_TIMER, WM_QUIT = 0x312, 0x113, 0x12


def carpeta():
    return os.path.join(os.environ["LOCALAPPDATA"], "barra-temas")


def cerrar_barra(pid):
    """Solo si ese proceso sigue siendo Python: Windows reutiliza los números."""
    if pid and os.path.basename(win.exe_of(pid)).lower().startswith("python"):
        return win.terminate(pid)
    return False


def restaurar():
    try:
        with open(os.path.join(carpeta(), "pid.json"), encoding="utf-8") as f:
            cerrar_barra(int(json.load(f)["pid"]))
    except (OSError, ValueError, KeyError, TypeError):
        pass
    time.sleep(0.5)
    win.show_taskbars()


def vigilar(pid):
    user32 = win.user32
    hilo = win.kernel32.GetCurrentThreadId()
    ultimo = [time.monotonic()]

    def leer():
        try:
            while sys.stdin.readline():
                ultimo[0] = time.monotonic()
        except (OSError, ValueError):
            pass
        user32.PostThreadMessageW(hilo, WM_QUIT, 0, 0)

    threading.Thread(target=leer, daemon=True).start()
    atajo = bool(user32.RegisterHotKey(None, 1, MOD, ord("B")))
    print(json.dumps({"atajo": atajo}), flush=True)
    user32.SetTimer(None, 0, 1000, None)
    msg = w.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == WM_HOTKEY:
            cerrar_barra(pid)
            break
        if msg.message == WM_TIMER and time.monotonic() - ultimo[0] > SILENCIO:
            win.show_taskbars()     # si la barra se recupera, la volverá a ocultar
    for _ in range(3):
        win.show_taskbars()
        time.sleep(0.4)


if __name__ == "__main__":
    if "--restaurar" in sys.argv:
        restaurar()
    else:
        vigilar(int(sys.argv[1]))
