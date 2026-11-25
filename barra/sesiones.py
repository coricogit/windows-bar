"""La ventana en la que corre una sesión de Claude Code.

    py sesiones.py --consola PID    (uso interno: imprime la ventana de su consola)
"""
import ctypes
import json
import os
import subprocess
import sys
from ctypes import wintypes as w

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from barra import win  # noqa: E402

k32 = win.kernel32
CARPETA = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude"),
                       "sessions")
# Antepasados que no son la terminal: sus ventanas son otra cosa.
NO_SON = {"explorer.exe", "services.exe", "svchost.exe", "wininit.exe", "winlogon.exe"}


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("pid", w.DWORD), ("heap", ctypes.c_size_t),
                ("modulo", w.DWORD), ("hilos", w.DWORD), ("padre", w.DWORD), ("prio", w.LONG),
                ("flags", w.DWORD), ("exe", w.WCHAR * 260)]


k32.CreateToolhelp32Snapshot.restype = w.HANDLE
k32.CreateToolhelp32Snapshot.argtypes = (w.DWORD, w.DWORD)
for n in ("Process32FirstW", "Process32NextW"):
    getattr(k32, n).argtypes = (w.HANDLE, ctypes.POINTER(PROCESSENTRY32W))


def procesos():
    """{pid: (padre, ejecutable)}"""
    foto, out = k32.CreateToolhelp32Snapshot(2, 0), {}
    e = PROCESSENTRY32W(dwSize=ctypes.sizeof(PROCESSENTRY32W))
    ok = k32.Process32FirstW(foto, ctypes.byref(e))
    while ok:
        out[e.pid] = (e.padre, e.exe.lower())
        ok = k32.Process32NextW(foto, ctypes.byref(e))
    k32.CloseHandle(foto)
    return out


def cadena(pid, tabla):
    """El proceso y sus antepasados, sin dar vueltas."""
    out = []
    while pid in tabla and pid not in out and len(out) < 12 and tabla[pid][1] not in NO_SON:
        out.append(pid)
        pid = tabla[pid][0]
    return out


def pid_de(sesion):
    try:
        nombres = os.listdir(CARPETA)
    except OSError:
        return None
    for n in nombres:
        if n.endswith(".json") and n[:-5].isdigit():
            try:
                with open(os.path.join(CARPETA, n), encoding="utf-8") as f:
                    if json.load(f).get("sessionId") == sesion:
                        return int(n[:-5])
            except (OSError, ValueError, AttributeError):
                pass
    return None


def ventana_de(pid):
    """La ventana de la sesión, o None."""
    dueños = {}
    for h in win.windows():
        dueños.setdefault(win.pid_of(h), h)
    for p in cadena(pid, procesos()):
        if p in dueños:
            return dueños[p]
    # Terminal abierta por su cuenta (no es antepasado): preguntar a la consola.
    try:
        r = subprocess.run([sys.executable.replace("pythonw.exe", "python.exe"), os.path.abspath(__file__),
                            "--consola", str(pid)], capture_output=True, text=True, timeout=5,
                           creationflags=0x08000000)
        h = int(r.stdout.strip() or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    return h if h and win.user32.IsWindowVisible(h) else None


def ventana_consola(pid):
    k32.GetConsoleWindow.restype = w.HWND
    win.user32.GetAncestor.restype = w.HWND
    win.user32.GetAncestor.argtypes = (w.HWND, w.UINT)
    k32.FreeConsole()
    if not k32.AttachConsole(pid):
        return 0
    h = k32.GetConsoleWindow()
    k32.FreeConsole()
    return (win.user32.GetAncestor(h, 3) or h) if h else 0       # GA_ROOTOWNER


if __name__ == "__main__" and sys.argv[1:2] == ["--consola"]:
    salida = os.dup(1)
    os.write(salida, str(ventana_consola(int(sys.argv[2]))).encode())
