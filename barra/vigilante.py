"""Vigilante: devuelve la barra de Windows si la nuestra se cierra o se cuelga.

Proceso aparte. La barra le escribe un latido por segundo; si se cierra la
tubería, o pasan SILENCIO segundos sin latidos, muestra la barra de Windows.
Si murió sin despedirse (o lleva COLGADA segundos sin responder) la vuelve a
abrir, como mucho MAX_REINICIOS veces en VENTANA segundos.
Ctrl+Alt+Mayús+B cierra la barra a la fuerza y la devuelve al momento.

    py vigilante.py --restaurar     cierra la barra (si está) y devuelve la de Windows
"""
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
from ctypes import wintypes as w

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from barra import win  # noqa: E402

SILENCIO, COLGADA = 8, 45
MAX_REINICIOS, VENTANA = 3, 300
ADIOS = "adios"
MOD = 1 | 2 | 4 | 0x4000      # Alt, Ctrl, Mayús, sin repetición
WM_HOTKEY, WM_TIMER, WM_QUIT = 0x312, 0x113, 0x12


def carpeta():
    return os.path.join(os.environ["LOCALAPPDATA"], "barra-temas")


def anotar(texto):
    try:
        with open(os.path.join(carpeta(), "barra.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + texto + "\n")
    except OSError:
        pass


def recientes(tiempos, ahora):
    return [t for t in tiempos if isinstance(t, (int, float)) and 0 <= ahora - t < VENTANA]


def puede_reiniciar(tiempos, ahora):
    return len(recientes(tiempos, ahora)) < MAX_REINICIOS


def pedido_parar():
    """¿Alguien acaba de pedir que se cierre (el .bat de restaurar)?"""
    try:
        return time.time() - os.path.getmtime(os.path.join(carpeta(), "parar")) < 15
    except OSError:
        return False


def reabrir():
    """Vuelve a abrir la barra, si no se ha reiniciado demasiado."""
    if win.user32.GetSystemMetrics(0x2000) or pedido_parar():       # SM_SHUTTINGDOWN
        return
    ruta = os.path.join(carpeta(), "reinicios.json")
    try:
        with open(ruta, encoding="utf-8") as f:
            tiempos = json.load(f)
        tiempos = tiempos if isinstance(tiempos, list) else []
    except (OSError, ValueError):
        tiempos = []
    ahora = time.time()
    if not puede_reiniciar(tiempos, ahora):
        anotar("demasiados reinicios seguidos: se queda la barra de Windows")
        return
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(recientes(tiempos, ahora) + [ahora], f)
    except OSError:
        return                      # sin poder contarlos, mejor no insistir
    anotar("la barra se cerró sola: se vuelve a abrir")
    barra = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "barra.pyw")
    exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP: no depende de este proceso
    subprocess.Popen([exe if os.path.exists(exe) else sys.executable, barra], creationflags=0x208, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def cerrar_barra(pid):
    """Solo si ese proceso sigue siendo Python: Windows reutiliza los números."""
    if pid and os.path.basename(win.exe_of(pid)).lower().startswith("python"):
        return win.terminate(pid)
    return False


def restaurar():
    try:
        open(os.path.join(carpeta(), "parar"), "w").close()      # que no la vuelvan a abrir
    except OSError:
        pass
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
    estado = {"adios": False}
    vuelta = time.monotonic()

    def leer():
        try:
            while True:
                linea = sys.stdin.readline()
                if not linea:
                    break
                ultimo[0] = time.monotonic()
                if linea.strip() == ADIOS:
                    estado["adios"] = True
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
            estado["adios"] = True
            cerrar_barra(pid)
            break
        if msg.message == WM_TIMER:
            ahora = time.monotonic()
            if ahora - vuelta > 5:          # el equipo estuvo suspendido: no es culpa suya
                ultimo[0] = ahora
            vuelta = ahora
            if ahora - ultimo[0] > COLGADA:
                anotar("la barra no responde")
                cerrar_barra(pid)
                break
            if ahora - ultimo[0] > SILENCIO:
                win.show_taskbars()         # si la barra se recupera, la volverá a ocultar
    for _ in range(3):
        win.show_taskbars()
        time.sleep(0.4)
    if not estado["adios"]:
        reabrir()


if __name__ == "__main__":
    if "--restaurar" in sys.argv:
        restaurar()
    else:
        vigilar(int(sys.argv[1]))
