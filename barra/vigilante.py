"""Vigilante: devuelve la barra de Windows si la nuestra se cierra o se cuelga.

Proceso aparte. La barra le escribe un latido por segundo; si se cierra la
tubería, o pasan SILENCIO segundos sin latidos, muestra la barra de Windows.
Si murió sin despedirse (o lleva COLGADA segundos sin responder) la vuelve a
abrir, como mucho MAX_REINICIOS veces en VENTANA segundos.
Ctrl+Alt+Mayús+B cierra la barra a la fuerza y la devuelve al momento.

    py vigilante.py --restaurar     cierra la barra (si está) y devuelve la de Windows
    py vigilante.py --recargar      la cierra y la vuelve a abrir (para probar código nuevo)
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


def pedido(que):
    """¿Alguien acaba de pedir que se cierre ("parar", el .bat de restaurar) o que se recargue ("recargar")?"""
    try:
        return time.time() - os.path.getmtime(os.path.join(carpeta(), que)) < 15
    except OSError:
        return False


def pedido_parar():
    return pedido("parar")


# Códigos de salida que dicen algo; el resto se anota tal cual.
CODIGOS = {
    0: "salió sin despedirse",
    1: "la cerró otro programa o falló Python",
    0xC0000005: "fallo de memoria",
    0xC0000374: "montón dañado",
    0xC0000409: "fallo interno (pila o comprobación de seguridad)",
    0xC00000FD: "desbordamiento de pila",
    0xC000013A: "Ctrl+C o cierre de sesión",
    0x40010004: "se cerró la sesión",
    259: "sigue viva pero no responde",
    0xFFFFFFFF: "la cerró otro programa (Administrador de tareas o similar)",
}


def motivo(codigo):
    if codigo is None:
        return "sin código de salida"
    texto = CODIGOS.get(codigo)
    return f"código 0x{codigo:X}" + (f", {texto}" if texto else "")


def abrir_proceso(pid):
    """Un asa para leer luego su código de salida (SYNCHRONIZE | QUERY_LIMITED_INFORMATION)."""
    return win.kernel32.OpenProcess(0x101000, False, pid) or None


def codigo_salida(h, espera=3000):
    if not h:
        return None
    try:
        win.kernel32.WaitForSingleObject(h, espera)
        codigo = w.DWORD()
        return codigo.value if win.kernel32.GetExitCodeProcess(h, ctypes.byref(codigo)) else None
    finally:
        win.kernel32.CloseHandle(h)


def traer_fallo():
    """Lo que dejó faulthandler (barra-fallo.log), al registro: dice dónde estaba al caer."""
    try:
        with open(os.path.join(carpeta(), "barra-fallo.log"), encoding="utf-8", errors="replace") as f:
            texto = f.read().strip()
    except OSError:
        return
    if texto:
        anotar("dónde estaba al caer:\n" + texto[-4000:])


def reabrir(razon="se cerró sola"):
    """Vuelve a abrir la barra, si no se ha reiniciado demasiado. Una recarga pedida no cuenta."""
    if win.user32.GetSystemMetrics(0x2000) or pedido_parar():       # SM_SHUTTINGDOWN
        return
    if pedido("recargar"):
        anotar("recarga pedida: se vuelve a abrir")
        lanzar_barra()
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
        anotar(f"la barra {razon}; demasiados reinicios seguidos: se queda la barra de Windows")
        traer_fallo()
        return
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(recientes(tiempos, ahora) + [ahora], f)
    except OSError:
        return                      # sin poder contarlos, mejor no insistir
    anotar(f"la barra {razon}: se vuelve a abrir")
    traer_fallo()
    lanzar_barra()


def lanzar_barra():
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


def avisar_y_cerrar(que):
    """Deja el aviso `que` para el vigilante y cierra la barra. Devuelve si había una que cerrar."""
    try:
        open(os.path.join(carpeta(), que), "w").close()
    except OSError:
        pass
    try:
        with open(os.path.join(carpeta(), "pid.json"), encoding="utf-8") as f:
            return cerrar_barra(int(json.load(f)["pid"]))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def restaurar():
    avisar_y_cerrar("parar")         # que no la vuelvan a abrir
    time.sleep(0.5)
    win.show_taskbars()


def recargar():
    if not avisar_y_cerrar("recargar"):
        print("no hay ninguna barra abierta")


def vigilar(pid):
    user32 = win.user32
    hilo = win.kernel32.GetCurrentThreadId()
    ultimo = [time.monotonic()]
    estado = {"adios": False, "razon": ""}
    vuelta = time.monotonic()
    proceso = abrir_proceso(pid)

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
                estado["razon"] = "no respondía"
                cerrar_barra(pid)
                break
            if ahora - ultimo[0] > SILENCIO:
                win.show_taskbars()         # si la barra se recupera, la volverá a ocultar
    for _ in range(3):
        win.show_taskbars()
        time.sleep(0.4)
    codigo = codigo_salida(proceso)
    if not estado["adios"]:
        reabrir(f'{estado["razon"] or "se cerró sola"} ({motivo(codigo)})')


if __name__ == "__main__":
    if "--restaurar" in sys.argv:
        restaurar()
    elif "--recargar" in sys.argv:
        recargar()
    else:
        vigilar(int(sys.argv[1]))
