"""Instalar, actualizar y quitar la barra.

    python instalado.py --instalar           desde la carpeta descomprimida (instalar.ps1)
    python instalado.py --actualizar DESTINO  ídem, sobre una copia instalada (barra/actualizar.py)
    python instalado.py --desinstalar        desde la copia instalada

Y lo que usa el instalador .exe (installer/windows-bar.iss):

    python instalado.py --parar              cierra la barra que haya y devuelve la de Windows
    python instalado.py --arranque si|no     arrancar esta copia con Windows
    python instalado.py --quitar             antes de desinstalar esta copia
"""
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
import winreg

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from barra import arranque, vigilante, win  # noqa: E402
from barra.win import GUID, method, ole32  # noqa: E402

DESTINO = os.path.join(os.environ["LOCALAPPDATA"], "Programs", "Windows Bar")
PARTES = ("python", "barra", "qml", "temas", "lib", "licenses", "barra.pyw", "version.txt", "windows-bar.ico",
          "LICENSE", "README.md")
NECESARIAS = ("python/pythonw.exe", "barra/win.py", "qml/Barra.qml", "temas/tokyo/tema.json", "barra.pyw", "version.txt")
NOMBRE = "Windows Bar"
RESTAURAR = "Restaurar barra de Windows"
CLAVE = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\WindowsBar"
CLAVE_EXE = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{B0A9C1D4-6E37-4C52-9F0B-2B7B5C3E8A61}_is1"
MENU = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs")
SUELTO = 0x208 | 0x08000000      # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW


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


def quitar(raiz=RAIZ):
    pid = pid_abierta()
    # Otra copia, como la del código, sigue abierta.
    if not pid or es_de(win.exe_of(pid), raiz) or not win.exe_of(pid):
        parar()
    if arranque.guardado() == arranque.orden():
        arranque.poner(False)
    shutil.rmtree(os.path.join(vigilante.carpeta(), "actualizacion"), ignore_errors=True)


# ----- poner los archivos -----

def _borrar(ruta):
    if os.path.isdir(ruta):
        shutil.rmtree(ruta, ignore_errors=True)
    elif os.path.exists(ruta):
        os.remove(ruta)


def completa(carpeta):
    return all(os.path.exists(os.path.join(carpeta, n)) for n in NECESARIAS)


def _devolver(destino, apartadas):
    for n in apartadas:
        ruta = os.path.join(destino, n)
        _borrar(ruta)
        os.rename(ruta + ".old", ruta)


def _apartar(destino):
    """Aparta la versión de antes. Si algo está en uso, la deja como estaba y falla."""
    hechas = []
    try:
        for n in PARTES:
            ruta = os.path.join(destino, n)
            if os.path.exists(ruta):
                _borrar(ruta + ".old")
                os.rename(ruta, ruta + ".old")
                hechas.append(n)
    except OSError:
        _devolver(destino, hechas)
        raise
    return hechas


def poner(origen, destino, intentos=40, pausa=0.5):
    """Copia `origen` en `destino`. Si falla, queda la versión que había."""
    if not completa(origen):
        raise OSError("a la copia nueva le faltan archivos")
    os.makedirs(destino, exist_ok=True)
    for i in range(intentos):
        try:
            apartadas = _apartar(destino)
            break
        except OSError:              # la barra tarda un poco en soltar sus archivos
            if i == intentos - 1:
                raise
            time.sleep(pausa)
    try:
        for n in PARTES:
            de, a = os.path.join(origen, n), os.path.join(destino, n)
            if os.path.isdir(de):
                shutil.copytree(de, a, ignore=shutil.ignore_patterns("__pycache__"))
            elif os.path.exists(de):
                shutil.copy2(de, a)
        if not completa(destino):
            raise OSError("la copia no quedó completa")
    except OSError:
        for n in PARTES:
            if n not in apartadas:
                _borrar(os.path.join(destino, n))
        _devolver(destino, apartadas)
        raise
    for n in apartadas:
        _borrar(os.path.join(destino, n) + ".old")


# ----- accesos y ficha de Windows -----

def acceso(nombre, destino, argumentos):
    """Un acceso directo en el menú Inicio."""
    enlace, archivo = ctypes.c_void_p(), ctypes.c_void_p()
    clsid, iid = GUID("00021401-0000-0000-c000-000000000046"), GUID("000214f9-0000-0000-c000-000000000046")
    if ole32.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(enlace)) < 0:
        return False
    txt, ico = ctypes.c_wchar_p, os.path.join(destino, "windows-bar.ico")
    try:
        method(enlace, 20, txt)(os.path.join(destino, "python", "pythonw.exe"))
        method(enlace, 11, txt)(argumentos)
        method(enlace, 9, txt)(destino)
        method(enlace, 17, txt, ctypes.c_int)(ico, 0)
        iid = GUID("0000010b-0000-0000-c000-000000000046")
        if method(enlace, 0, ctypes.c_void_p, ctypes.c_void_p)(ctypes.byref(iid), ctypes.byref(archivo)) < 0:
            return False
        return method(archivo, 6, txt, ctypes.c_int)(os.path.join(MENU, nombre + ".lnk"), 1) >= 0
    finally:
        for o in (archivo, enlace):
            if o:
                method(o, 2)()


def _existe(clave):
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CURRENT_USER, clave))
        return True
    except OSError:
        return False


def ficha(destino):
    """La entrada de Configuración > Aplicaciones, o su versión si la puso el .exe."""
    with open(os.path.join(destino, "version.txt"), encoding="ascii") as f:
        version = f.read().strip()
    if _existe(CLAVE_EXE):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CLAVE_EXE, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "DisplayVersion", 0, winreg.REG_SZ, version)
            winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, f"{NOMBRE} {version}")
        return
    pyw, yo = os.path.join(destino, "python", "pythonw.exe"), os.path.join(destino, "barra", "instalado.py")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, CLAVE) as k:
        for n, v in (("DisplayName", NOMBRE), ("DisplayVersion", version), ("Publisher", "coricogit"),
                     ("InstallLocation", destino), ("DisplayIcon", os.path.join(destino, "windows-bar.ico")),
                     ("URLInfoAbout", "https://github.com/coricogit/windows-bar"),
                     ("UninstallString", f'"{pyw}" "{yo}" --desinstalar'),
                     ("QuietUninstallString", f'"{pyw}" "{yo}" --desinstalar --callado')):
            winreg.SetValueEx(k, n, 0, winreg.REG_SZ, v)
        for n in ("NoModify", "NoRepair"):
            winreg.SetValueEx(k, n, 0, winreg.REG_DWORD, 1)


def abrir(destino):
    subprocess.Popen([os.path.join(destino, "python", "pythonw.exe"), os.path.join(destino, "barra.pyw")], cwd=destino,
                     creationflags=0x208, close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)


# ----- las tres acciones -----

def instalar(destino=DESTINO, con_windows=True, abrirla=True):
    if sys.getwindowsversion().build < 22000:
        sys.exit("Windows Bar necesita Windows 11.")
    nueva = not os.path.exists(os.path.join(destino, "version.txt"))
    parar()
    poner(RAIZ, destino)
    ole32.CoInitializeEx(None, 2)
    barra = os.path.join(destino, "barra.pyw")
    acceso(NOMBRE, destino, f'"{barra}"')
    acceso(RESTAURAR, destino, f'"{os.path.join(destino, "barra", "vigilante.py")}" --restaurar')
    ficha(destino)
    if nueva and con_windows:
        arranque.poner(True, f'"{os.path.join(destino, "python", "pythonw.exe")}" "{barra}"')
    if abrirla:
        abrir(destino)


def actualizar(destino):
    """La lanza la propia barra, sin nadie delante. Siempre deja una abierta."""
    try:
        parar()
        poner(RAIZ, destino)
        ficha(destino)
        vigilante.anotar("actualizada")
    except Exception as e:
        vigilante.anotar(f"la actualización falló, sigue la versión de antes: {e!r}")
    abrir(destino)


def desinstalar(callado):
    MB = ctypes.windll.user32.MessageBoxW
    if not callado and MB(None, "¿Desinstalar Windows Bar? Volverá la barra de Windows. Tus ajustes se conservan.",
                          NOMBRE, 0x24) != 6:
        return
    os.chdir(os.environ["SystemRoot"])
    quitar()
    for n in (NOMBRE, RESTAURAR):
        try:
            os.remove(os.path.join(MENU, n + ".lnk"))
        except OSError:
            pass
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, CLAVE)
    except OSError:
        pass
    # Este Python está dentro de la carpeta: se borra en cuanto termine.
    if os.path.exists(os.path.join(RAIZ, "python", "pythonw.exe")) and completa(RAIZ):
        cmd = os.path.join(os.environ["SystemRoot"], "System32", "cmd.exe")
        subprocess.Popen(f'"{cmd}" /d /c "ping -n 4 127.0.0.1 >nul & rmdir /s /q "{RAIZ}""', creationflags=SUELTO & ~0x8,
                         close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--instalar" in a:
        instalar(a[a.index("--destino") + 1] if "--destino" in a else DESTINO, "--sin-arranque" not in a, "--no-abrir" not in a)
    elif "--actualizar" in a:
        actualizar(a[a.index("--actualizar") + 1])
    elif "--desinstalar" in a:
        desinstalar("--callado" in a)
    else:
        if "--parar" in a:
            parar()
        if "--arranque" in a:
            si = a[a.index("--arranque") + 1] == "si"
            if si or arranque.guardado() == arranque.orden():      # la de otra copia no se toca
                arranque.poner(si)
        if "--quitar" in a:
            quitar()
