"""Ventanas que piden atención: lo que en la barra de Windows es el botón naranja.

Un programa llama a FlashWindowEx (Discord con un mensaje, una descarga que
acaba, un juego que termina de cargar) y Windows se lo cuenta a las ventanas
registradas con RegisterShellHookWindow. Aquí hay una ventana invisible propia
para eso: no se inyecta nada en ningún proceso. Sus mensajes llegan por el bucle
de Qt, en el hilo principal.
"""
import ctypes
from ctypes import wintypes as w

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32")
LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM)

HSHELL_WINDOWDESTROYED, HSHELL_WINDOWACTIVATED, HSHELL_RUDEAPPACTIVATED, HSHELL_FLASH = 2, 4, 0x8004, 0x8006
CLASE = "BarraTemasAtencion"


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", w.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", w.HINSTANCE), ("hIcon", w.HICON), ("hCursor", w.HANDLE), ("hbrBackground", w.HBRUSH),
                ("lpszMenuName", w.LPCWSTR), ("lpszClassName", w.LPCWSTR)]


def _sig(dll, name, res, *args):
    f = getattr(dll, name)
    f.restype, f.argtypes = res, list(args)


_sig(user32, "DefWindowProcW", LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
_sig(user32, "RegisterClassW", w.ATOM, ctypes.POINTER(WNDCLASSW))
_sig(user32, "CreateWindowExW", w.HWND, w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, *[ctypes.c_int] * 4,
     w.HWND, w.HMENU, w.HINSTANCE, w.LPVOID)
_sig(user32, "DestroyWindow", w.BOOL, w.HWND)
_sig(user32, "RegisterShellHookWindow", w.BOOL, w.HWND)
_sig(user32, "DeregisterShellHookWindow", w.BOOL, w.HWND)
_sig(user32, "RegisterWindowMessageW", w.UINT, w.LPCWSTR)
_sig(kernel32, "GetModuleHandleW", w.HMODULE, w.LPCWSTR)


def que_paso(codigo):
    """"pide", "activa", "cerrada" o None, según el código del mensaje del shell."""
    if codigo == HSHELL_FLASH:
        return "pide"
    if codigo in (HSHELL_WINDOWACTIVATED, HSHELL_RUDEAPPACTIVATED):
        return "activa"
    if codigo == HSHELL_WINDOWDESTROYED:
        return "cerrada"
    return None


class Atencion:
    """Lleva la cuenta de qué ventanas piden atención; `al_pedir(hwnd)` avisa de una nueva."""

    def __init__(self, al_pedir, al_cambiar):
        self.piden = set()
        self._al_pedir, self._al_cambiar = al_pedir, al_cambiar
        self._mensaje = user32.RegisterWindowMessageW("SHELLHOOK")
        self._proc = WNDPROC(self._wndproc)          # vivo mientras exista la ventana
        inst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW(lpfnWndProc=self._proc, hInstance=inst, lpszClassName=CLASE)
        user32.RegisterClassW(ctypes.byref(wc))      # si ya estaba (una barra anterior en este proceso), sirve igual
        # WS_EX_TOOLWINDOW, WS_POPUP y sin mostrar: no sale en ningún sitio.
        self.hwnd = user32.CreateWindowExW(0x80, CLASE, "", 0x80000000, 0, 0, 0, 0, None, None, inst, None)
        self.ok = bool(self.hwnd and user32.RegisterShellHookWindow(self.hwnd))

    def _wndproc(self, hwnd, msg, wp, lp):
        if msg == self._mensaje:
            try:
                self.recibir(que_paso(wp), int(lp or 0))
            except Exception:
                pass
            return 0
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    def recibir(self, que, ventana):
        if not que or not ventana:
            return
        if que == "pide":
            if ventana not in self.piden:
                self.piden.add(ventana)
                self._al_pedir(ventana)
                self._al_cambiar()
        elif ventana in self.piden:          # activada o cerrada: ya está atendida
            self.piden.discard(ventana)
            self._al_cambiar()

    def olvidar(self, vivas):
        """Quita las que ya no existen o que están delante."""
        quedan = {h for h in self.piden if h in vivas}
        if quedan != self.piden:
            self.piden = quedan
            self._al_cambiar()

    def cerrar(self):
        if self.hwnd:
            user32.DeregisterShellHookWindow(self.hwnd)
            user32.DestroyWindow(self.hwnd)
            self.hwnd = None
