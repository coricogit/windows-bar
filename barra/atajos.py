"""Los atajos de la barra de Windows (Win+número, Win+T, Win+B), para esta barra.

Explorer los tiene reservados y los aplicaría a su barra, que está oculta. Este
proceso aparte los intercepta: con entrada en bruto se entera de que se pulsa la
tecla Windows, y solo mientras está pulsada (o se elige con las flechas) pone un
gancho de teclado. Al escribir o jugar no hay gancho ninguno.

Escribe una línea JSON por atajo. Por su entrada recibe "si" o "no" (modo juego);
si se cierra, termina.
"""
import ctypes
import json
import queue
import sys
import threading
import time
from ctypes import wintypes as w

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, w.WPARAM, w.LPARAM)
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM)

WIN_IZQ, WIN_DER, MAYUS, CTRL, ALT = 0x5B, 0x5C, 0x10, 0x11, 0x12
MODIFICADORES = (WIN_IZQ, WIN_DER, MAYUS, CTRL, ALT, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5)
ATRAS, ADELANTE = (0x25, 0x26), (0x27, 0x28, 0x09)      # izquierda y arriba; derecha, abajo y tabulador
INTRO, ESPACIO, ESC, MENU = 0x0D, 0x20, 0x1B, 0x5D
NADIE = 0xE8              # tecla sin asignar: evita que al soltar Windows se abra Inicio
ESPERA = 6                # segundos eligiendo con las flechas sin tocar nada
WM_INPUT, WM_TIMER, WM_CLOSE, WM_DESTROY = 0xFF, 0x113, 0x10, 0x2


class Logica:
    """Qué hacer con cada tecla. `modo`: None, "tareas" o "bandeja" (eligiendo)."""

    def __init__(self):
        self.modo, self.hasta, self.tragadas = None, 0, set()

    def caducar(self, ahora):
        if self.modo and ahora > self.hasta:
            return self._salir()
        return None

    def _salir(self):
        self.modo = None
        return {"op": "cancelar"}

    def _mover(self, modo, paso, ahora):
        self.modo, self.hasta = modo, ahora + ESPERA
        return {"op": "mover", "lista": modo, "paso": paso}

    def tecla(self, vk, abajo, win, mayus, ctrl, alt, ahora):
        """(¿se la queda?, aviso para la barra o None)."""
        if not abajo:
            if vk in self.tragadas:
                self.tragadas.discard(vk)
                return True, None
            return False, None
        if vk in MODIFICADORES:
            return False, None
        repetida = vk in self.tragadas
        caduco = self.caducar(ahora)
        aviso, suya = caduco, False
        if win:
            if 0x30 <= vk <= 0x39:
                self.modo, suya = None, True
                aviso = None if repetida else {"op": "numero", "i": (vk - 0x31) % 10, "mayus": mayus, "ctrl": ctrl, "alt": alt}
            elif vk == ord("T") and not ctrl and not alt and (not mayus or self.modo == "tareas"):
                suya, aviso = True, self._mover("tareas", -1 if mayus else 1, ahora)
            elif vk == ord("B") and not ctrl and not alt and not mayus:
                suya, aviso = True, self._mover("bandeja", 1, ahora)
            elif self.modo:
                aviso = self._salir()
        elif self.modo:
            if vk in ATRAS or vk in ADELANTE:
                suya, aviso = True, self._mover(self.modo, -1 if vk in ATRAS or (vk == 0x09 and mayus) else 1, ahora)
            elif vk in (INTRO, ESPACIO, MENU):
                suya, aviso = True, {"op": "menu" if vk == MENU else "pulsar", "lista": self.modo}
                self.modo = None
            elif vk == ESC:
                suya, aviso = True, self._salir()
            else:
                aviso = self._salir()
        if suya or repetida:
            self.tragadas.add(vk)
        return suya or repetida, aviso


class KBD(ctypes.Structure):
    _fields_ = [("vk", w.DWORD), ("scan", w.DWORD), ("flags", w.DWORD), ("time", w.DWORD), ("extra", ctypes.c_size_t)]


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("pagina", w.USHORT), ("uso", w.USHORT), ("flags", w.DWORD), ("hwnd", w.HWND)]


class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [("tipo", w.DWORD), ("tam", w.DWORD), ("disp", w.HANDLE), ("wparam", w.WPARAM),
                ("make", w.USHORT), ("flags", w.USHORT), ("res", w.USHORT), ("vk", w.USHORT),
                ("msg", w.UINT), ("extra", w.ULONG)]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", w.UINT), ("proc", WNDPROC), ("a", ctypes.c_int), ("b", ctypes.c_int), ("inst", w.HINSTANCE),
                ("icon", w.HANDLE), ("cursor", w.HANDLE), ("brush", w.HANDLE), ("menu", w.LPCWSTR), ("nombre", w.LPCWSTR)]


user32.SetWindowsHookExW.argtypes = (ctypes.c_int, HOOKPROC, w.HINSTANCE, w.DWORD)
user32.SetWindowsHookExW.restype = w.HHOOK
user32.UnhookWindowsHookEx.argtypes = (w.HHOOK,)
user32.CallNextHookEx.argtypes = (w.HHOOK, ctypes.c_int, w.WPARAM, w.LPARAM)
user32.CallNextHookEx.restype = LRESULT
user32.DefWindowProcW.argtypes = (w.HWND, w.UINT, w.WPARAM, w.LPARAM)
user32.DefWindowProcW.restype = LRESULT
user32.CreateWindowExW.argtypes = (w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, w.HWND, w.HANDLE, w.HINSTANCE, ctypes.c_void_p)
user32.CreateWindowExW.restype = w.HWND
user32.GetRawInputData.argtypes = (w.HANDLE, w.UINT, ctypes.c_void_p, ctypes.POINTER(w.UINT), w.UINT)
user32.RegisterRawInputDevices.argtypes = (ctypes.POINTER(RAWINPUTDEVICE), w.UINT, w.UINT)
user32.SetTimer.argtypes = (w.HWND, ctypes.c_size_t, w.UINT, ctypes.c_void_p)
user32.KillTimer.argtypes = (w.HWND, ctypes.c_size_t)
user32.PostMessageW.argtypes = (w.HWND, w.UINT, w.WPARAM, w.LPARAM)
user32.GetAsyncKeyState.restype = ctypes.c_short
kernel32.GetModuleHandleW.restype = w.HMODULE
kernel32.GetModuleHandleW.argtypes = (w.LPCWSTR,)


def pulsada(vk):
    return user32.GetAsyncKeyState(vk) < 0


class Atajos:
    def __init__(self, salida):
        self.logica, self.salida = Logica(), salida
        self.gancho, self.activo, self.hwnd = None, True, None
        self.cola = queue.Queue()
        self._hook, self._proc = HOOKPROC(self._tecla), WNDPROC(self._mensaje)

    # La barra podría tardar en leer: escribir nunca debe frenar el gancho.
    def _escribir(self):
        while True:
            try:
                self.salida.write(json.dumps(self.cola.get()) + "\n")
                self.salida.flush()
            except (OSError, ValueError):
                return

    def _leer(self):
        try:
            for linea in sys.stdin:
                self.activo = linea.strip() != "no"
        except (OSError, ValueError):
            pass
        user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)

    def poner(self):
        if not self.gancho and self.activo:
            self.gancho = user32.SetWindowsHookExW(13, self._hook, kernel32.GetModuleHandleW(None), 0)
            user32.SetTimer(self.hwnd, 1, 250, None)

    def revisar(self):
        """Quita el gancho en cuanto no hace falta."""
        aviso = self.logica.caducar(time.monotonic())
        if aviso:
            self.cola.put(aviso)
        if not self.activo or not (pulsada(WIN_IZQ) or pulsada(WIN_DER) or self.logica.modo):
            if self.gancho:
                user32.UnhookWindowsHookEx(self.gancho)
            self.gancho = None
            self.logica.modo = None
            self.logica.tragadas.clear()
            user32.KillTimer(self.hwnd, 1)

    def _tecla(self, n, wp, lp):
        if n == 0 and self.activo:
            k = ctypes.cast(lp, ctypes.POINTER(KBD)).contents
            if k.vk != NADIE:
                win = pulsada(WIN_IZQ) or pulsada(WIN_DER)
                tragar, aviso = self.logica.tecla(k.vk, not k.flags & 0x80, win, pulsada(MAYUS), pulsada(CTRL),
                                                  pulsada(ALT), time.monotonic())
                if aviso:
                    self.cola.put(aviso)
                if tragar:
                    if win and not k.flags & 0x80:
                        user32.keybd_event(NADIE, 0, 0, 0)
                        user32.keybd_event(NADIE, 0, 2, 0)
                    return 1
        return user32.CallNextHookEx(None, n, wp, lp)

    def _mensaje(self, hwnd, msg, wp, lp):
        if msg == WM_INPUT:
            r, tam = RAWKEYBOARD(), w.UINT(ctypes.sizeof(RAWKEYBOARD))
            if user32.GetRawInputData(lp, 0x10000003, ctypes.byref(r), ctypes.byref(tam), 24) not in (0, 0xFFFFFFFF, -1):
                if r.vk in (WIN_IZQ, WIN_DER) and not r.flags & 1:
                    self.poner()
        elif msg == WM_TIMER:
            self.revisar()
        elif msg == WM_CLOSE:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    def correr(self):
        inst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW(proc=self._proc, inst=inst, nombre="BarraTemasAtajos")
        user32.RegisterClassW(ctypes.byref(wc))
        self.hwnd = user32.CreateWindowExW(0, "BarraTemasAtajos", "", 0, 0, 0, 0, 0, w.HWND(-3), None, inst, None)
        # Teclado, aunque el foco esté en otra ventana (RIDEV_INPUTSINK).
        d = RAWINPUTDEVICE(1, 6, 0x100, self.hwnd)
        if not self.hwnd or not user32.RegisterRawInputDevices(ctypes.byref(d), 1, ctypes.sizeof(d)):
            raise ctypes.WinError(ctypes.get_last_error())
        kernel32.SetPriorityClass(w.HANDLE(-1), 0x8000)       # por encima de lo normal
        for f in (self._leer, self._escribir):
            threading.Thread(target=f, daemon=True).start()
        msg = w.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.DispatchMessageW(ctypes.byref(msg))
        if self.gancho:
            user32.UnhookWindowsHookEx(self.gancho)


if __name__ == "__main__":
    Atajos(sys.stdout).correr()
