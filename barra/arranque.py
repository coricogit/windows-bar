"""Arrancar con Windows: una entrada en HKCU\\...\\Run, la misma que se ve en
Administrador de tareas > Aplicaciones de arranque."""
import os
import sys
import winreg

RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
APROBADAS = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
NOMBRE = "BarraTemas"
BARRA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "barra.pyw")


def orden():
    exe = sys.executable
    sin_consola = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return f'"{sin_consola if os.path.exists(sin_consola) else exe}" "{BARRA}"'


def _leer(clave, nombre):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, clave) as k:
            return winreg.QueryValueEx(k, nombre)[0]
    except OSError:
        return None


def desactivada(valor):
    """El Administrador de tareas marca las desactivadas con el primer byte impar."""
    return bool(valor) and bool(valor[0] & 1)


def guardado():
    return _leer(RUN, NOMBRE)


def activo():
    return guardado() == orden() and not desactivada(_leer(APROBADAS, NOMBRE))


def poner(si, que=""):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN, 0, winreg.KEY_SET_VALUE) as k:
        if si:
            winreg.SetValueEx(k, NOMBRE, 0, winreg.REG_SZ, que or orden())
        else:
            try:
                winreg.DeleteValue(k, NOMBRE)
            except FileNotFoundError:
                pass
    # Si se desactivó desde Windows, esa marca mandaría sobre la entrada.
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APROBADAS, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, NOMBRE)
    except OSError:
        pass


def decidir(querido, guardado_, propia, apagada):
    """Qué hacer con la entrada según lo que eligió el usuario ("si", "no" o "" si aún no se sabe).
    Devuelve (querido, volver_a_ponerla)."""
    if querido not in ("si", "no"):              # primera vez: se aprende de cómo está
        return ("si" if guardado_ == propia and not apagada else "no"), False
    if querido == "si":
        if guardado_ is None:                    # algo la borró: se pone otra vez
            return "si", True
        if guardado_ == propia and apagada:      # la apagó el usuario en el Administrador de tareas
            return "no", False
    return querido, False


def revisar(querido):
    """Vuelve a poner la entrada si se quería y desapareció. Devuelve (querido, si se puso)."""
    querido, poner_ = decidir(querido, guardado(), orden(), desactivada(_leer(APROBADAS, NOMBRE)))
    if poner_:
        poner(True)
    return querido, poner_
