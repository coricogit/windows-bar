"""Las llamadas a Windows que necesita la barra (solo ctypes)."""
import ctypes
import os
import uuid
from ctypes import wintypes as w

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi")
shell32 = ctypes.WinDLL("shell32")
ole32 = ctypes.WinDLL("ole32")
gdi32 = ctypes.WinDLL("gdi32")

ENUMPROC = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
EVENTPROC = ctypes.WINFUNCTYPE(None, w.HANDLE, w.DWORD, w.HWND, w.LONG, w.LONG, w.DWORD, w.DWORD)
SHELL_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "ForegroundStaging",
                 "XamlExplorerHostIslandWindow", "MultitaskingViewFrame", "Windows.UI.Core.CoreWindow",
                 "LockScreenBackstopFrame"}


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", w.DWORD), ("rcMonitor", w.RECT), ("rcWork", w.RECT), ("dwFlags", w.DWORD)]


def _sig(lib, name, res, *args):
    f = getattr(lib, name)
    f.restype, f.argtypes = res, args


_P = ctypes.POINTER
_sig(user32, "EnumWindows", w.BOOL, ENUMPROC, w.LPARAM)
_sig(user32, "FindWindowExW", w.HWND, w.HWND, w.HWND, w.LPCWSTR, w.LPCWSTR)
_sig(user32, "GetWindowThreadProcessId", w.DWORD, w.HWND, _P(w.DWORD))
_sig(user32, "GetClassNameW", ctypes.c_int, w.HWND, w.LPWSTR, ctypes.c_int)
_sig(user32, "GetWindowTextW", ctypes.c_int, w.HWND, w.LPWSTR, ctypes.c_int)
_sig(user32, "GetWindowLongPtrW", ctypes.c_ssize_t, w.HWND, ctypes.c_int)
_sig(user32, "GetClassLongPtrW", ctypes.c_size_t, w.HWND, ctypes.c_int)
_sig(user32, "GetWindow", w.HWND, w.HWND, w.UINT)
_sig(user32, "GetForegroundWindow", w.HWND)
_sig(user32, "SetForegroundWindow", w.BOOL, w.HWND)
_sig(user32, "IsWindowVisible", w.BOOL, w.HWND)
_sig(user32, "IsWindow", w.BOOL, w.HWND)
_sig(user32, "IsIconic", w.BOOL, w.HWND)
_sig(user32, "ShowWindowAsync", w.BOOL, w.HWND, ctypes.c_int)
_sig(user32, "PostMessageW", w.BOOL, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
_sig(user32, "SendMessageTimeoutW", ctypes.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM, w.UINT, w.UINT,
     _P(ctypes.c_size_t))
_sig(user32, "AllowSetForegroundWindow", w.BOOL, w.DWORD)
_sig(user32, "MonitorFromWindow", w.HANDLE, w.HWND, w.DWORD)
_sig(user32, "GetMonitorInfoW", w.BOOL, w.HANDLE, _P(MONITORINFO))
_sig(user32, "GetWindowRect", w.BOOL, w.HWND, _P(w.RECT))
_sig(user32, "SystemParametersInfoW", w.BOOL, w.UINT, w.UINT, ctypes.c_void_p, w.UINT)
_sig(user32, "IsZoomed", w.BOOL, w.HWND)
_sig(user32, "SetWindowPos", w.BOOL, w.HWND, w.HWND, *[ctypes.c_int] * 4, w.UINT)
_sig(user32, "GetCursorPos", w.BOOL, _P(w.POINT))
_sig(user32, "keybd_event", None, w.BYTE, w.BYTE, w.DWORD, ctypes.c_size_t)
_sig(user32, "SetWinEventHook", w.HANDLE, w.DWORD, w.DWORD, w.HMODULE, EVENTPROC, w.DWORD, w.DWORD, w.DWORD)
_sig(kernel32, "OpenProcess", w.HANDLE, w.DWORD, w.BOOL, w.DWORD)
_sig(kernel32, "CloseHandle", w.BOOL, w.HANDLE)
_sig(kernel32, "TerminateProcess", w.BOOL, w.HANDLE, w.UINT)
_sig(kernel32, "QueryFullProcessImageNameW", w.BOOL, w.HANDLE, w.DWORD, w.LPWSTR, _P(w.DWORD))
_sig(dwmapi, "DwmGetWindowAttribute", ctypes.c_long, w.HWND, w.DWORD, ctypes.c_void_p, w.DWORD)
_sig(gdi32, "DeleteObject", w.BOOL, w.HGDIOBJ)


# ----- procesos y ventanas --------------------------------------------------

def pid_of(hwnd):
    pid = w.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def exe_of(pid):
    h = kernel32.OpenProcess(0x1000, False, pid)   # QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf, n = ctypes.create_unicode_buffer(1024), w.DWORD(1024)
        return buf.value if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)) else ""
    finally:
        kernel32.CloseHandle(h)


def terminate(pid):
    h = kernel32.OpenProcess(1, False, pid)
    if not h:
        return False
    try:
        return bool(kernel32.TerminateProcess(h, 1))
    finally:
        kernel32.CloseHandle(h)


def class_name(hwnd):
    buf = ctypes.create_unicode_buffer(128)
    user32.GetClassNameW(hwnd, buf, 128)
    return buf.value


def title(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def cloaked(hwnd):
    v = w.DWORD()
    dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(v), 4)
    return v.value != 0


def in_taskbar(hwnd):
    """¿La mostraría la barra de Windows?"""
    if not user32.IsWindowVisible(hwnd):
        return False
    ex = user32.GetWindowLongPtrW(hwnd, -20)
    if ex & 0x80 and not ex & 0x40000:                      # TOOLWINDOW sin APPWINDOW
        return False
    if ex & 0x08000000 and not ex & 0x40000:                # NOACTIVATE
        return False
    if user32.GetWindow(hwnd, 4) and not ex & 0x40000:      # tiene dueña
        return False
    return not cloaked(hwnd) and class_name(hwnd) not in SHELL_CLASSES and bool(title(hwnd))


def app_exe(hwnd):
    """El programa de la ventana; el de verdad si es una app de la Tienda."""
    pid = pid_of(hwnd)
    if class_name(hwnd) == "ApplicationFrameWindow":
        child = None
        while True:
            child = user32.FindWindowExW(hwnd, child, "Windows.UI.Core.CoreWindow", None)
            if not child:
                break
            if pid_of(child) != pid:
                return exe_of(pid_of(child))
    return exe_of(pid)


def clave_exe(exe):
    """Identifica un programa. Las apps de la Tienda cambian de carpeta al
    actualizarse: de ellas solo cuenta el nombre."""
    exe = exe.lower()
    return "tienda:" + os.path.basename(exe) if "\\windowsapps\\" in exe else exe


def de_la_tienda(hwnd, exe):
    return class_name(hwnd) == "ApplicationFrameWindow" or "\\windowsapps\\" in exe.lower()


def maximize(hwnd):
    user32.ShowWindowAsync(hwnd, 3)


def restore(hwnd):
    user32.ShowWindowAsync(hwnd, 9)


def windows():
    """Las ventanas de la barra, de la más reciente a la más antigua."""
    out, own = [], os.getpid()

    def each(hwnd, _):
        if pid_of(hwnd) != own and in_taskbar(hwnd):
            out.append(hwnd)
        return True
    user32.EnumWindows(ENUMPROC(each), 0)
    return out


def activate(hwnd):
    if user32.IsIconic(hwnd):
        user32.ShowWindowAsync(hwnd, 9)      # SW_RESTORE
    if not user32.SetForegroundWindow(hwnd):
        # Windows no deja quitar el primer plano sin una tecla de por medio.
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 2, 0)
        user32.SetForegroundWindow(hwnd)


def minimize(hwnd):
    # Como su propio botón: así Windows activa la siguiente ventana. Con
    # ShowWindowAsync la minimizada seguía siendo la activa.
    if user32.GetWindowLongW(hwnd, -16) & 0x20000 and user32.PostMessageW(hwnd, 0x112, 0xF020, 0):
        return                  # WS_MINIMIZEBOX; WM_SYSCOMMAND, SC_MINIMIZE
    user32.ShowWindowAsync(hwnd, 6)


def close(hwnd):
    user32.PostMessageW(hwnd, 0x112, 0xF060, 0)   # WM_SYSCOMMAND, SC_CLOSE


def watch(callback):
    """Llama a `callback()` al cambiar la ventana activa, minimizar u ocultar.
    Devuelve lo que hay que conservar vivo."""
    proc = EVENTPROC(lambda *a: callback())
    for lo, hi in ((0x3, 0x3), (0x16, 0x17), (0x8017, 0x8018)):
        user32.SetWinEventHook(lo, hi, None, proc, 0, 0, 2)   # OUTOFCONTEXT | SKIPOWNPROCESS
    return proc


# ----- la barra de Windows --------------------------------------------------

def taskbars():
    out = []
    for cls in ("Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
        h = None
        while True:
            h = user32.FindWindowExW(None, h, cls, None)
            if not h:
                break
            if os.path.basename(exe_of(pid_of(h))).lower() == "explorer.exe":
                out.append(h)
    return out


def hide_taskbars():
    for h in taskbars():
        if user32.IsWindowVisible(h):
            user32.ShowWindowAsync(h, 0)


def show_taskbars():
    for h in taskbars():
        user32.ShowWindowAsync(h, 8)      # SW_SHOWNA
    ajustar_area()
    recolocar_maximizadas()


def _info(hwnd):
    info = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
    user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(info))
    return info


def alto_reservado(barra, pantalla):
    """Lo que ocupa abajo la barra de Windows, o None si no está fija abajo.
    Ambos son (izquierda, arriba, derecha, abajo)."""
    alto = pantalla[3] - barra[1]
    fija = barra[0] == pantalla[0] and barra[2:] == pantalla[2:]
    return alto if fija and 20 <= alto <= 120 else None


def ajustar_area(margenes=None):
    """Deja libres esos píxeles en los bordes de cada pantalla (izquierda,
    arriba, derecha, abajo); sin `margenes`, lo que ocupa la barra de Windows.
    No se guarda: se pierde al cerrar sesión. No se avisa al sistema
    (SENDCHANGE) porque Explorer desharía el cambio; a cambio hay que recolocar
    aquí las ventanas maximizadas."""
    cambio = False
    for h in taskbars():
        info, r = _info(h), w.RECT()
        user32.GetWindowRect(h, ctypes.byref(r))
        m, t = info.rcMonitor, info.rcWork
        suyo = alto_reservado((r.left, r.top, r.right, r.bottom), (m.left, m.top, m.right, m.bottom))
        if suyo is None:
            continue
        izq, arr, der, aba = margenes or (0, 0, 0, suyo)
        nueva = (m.left + izq, m.top + arr, m.right - der, m.bottom - aba)
        if (t.left, t.top, t.right, t.bottom) != nueva:
            user32.SystemParametersInfoW(0x2F, 0, ctypes.byref(w.RECT(*nueva)), 0)   # SPI_SETWORKAREA
            cambio = True
    if cambio:
        recolocar_maximizadas()


def sitio_maximizada(ventana, area, pantalla):
    """Dónde debe quedar una ventana maximizada, o None si ya está bien o no
    sigue las reglas. Sobresale lo mismo por los cuatro lados; cuánto, se ve en
    los dos bordes opuestos que llegan hasta la pantalla."""
    sobra = None
    for i in (0, 1):
        s = pantalla[i] - ventana[i]
        if 0 <= s <= 16 and ventana[i + 2] - pantalla[i + 2] == s:
            sobra = s
            break
    if sobra is None:
        return None
    nueva = (area[0] - sobra, area[1] - sobra, area[2] + sobra, area[3] + sobra)
    return nueva if nueva != tuple(ventana) else None


def recolocar_maximizadas():
    def each(hwnd, _):
        if user32.IsZoomed(hwnd) and in_taskbar(hwnd) and not is_fullscreen(hwnd):
            r, i = w.RECT(), _info(hwnd)
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            a, m = i.rcWork, i.rcMonitor
            n = sitio_maximizada((r.left, r.top, r.right, r.bottom), (a.left, a.top, a.right, a.bottom),
                                 (m.left, m.top, m.right, m.bottom))
            if n is not None:
                # NOZORDER | NOACTIVATE | ASYNCWINDOWPOS
                user32.SetWindowPos(hwnd, None, n[0], n[1], n[2] - n[0], n[3] - n[1], 0x4014)
        return True
    user32.EnumWindows(ENUMPROC(each), 0)


# ----- pantallas ------------------------------------------------------------

def monitor_of(hwnd):
    """(izquierda, arriba, derecha, abajo) de su pantalla, en píxeles reales."""
    info = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
    user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(info))
    r = info.rcMonitor
    return r.left, r.top, r.right, r.bottom


def covers(rect, monitor):
    return (rect[0] <= monitor[0] and rect[1] <= monitor[1]
            and rect[2] >= monitor[2] and rect[3] >= monitor[3])


def is_fullscreen(hwnd):
    if not hwnd or not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd) or cloaked(hwnd):
        return False
    if pid_of(hwnd) == os.getpid() or class_name(hwnd) in SHELL_CLASSES:
        return False
    if user32.GetWindowLongPtrW(hwnd, -16) & 0xC00000 == 0xC00000:   # con título: solo maximizada
        return False
    r = w.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return covers((r.left, r.top, r.right, r.bottom), monitor_of(hwnd))


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", w.UINT), ("dwTime", w.DWORD)]


def segundos_inactivo():
    i = LASTINPUTINFO(cbSize=ctypes.sizeof(LASTINPUTINFO))
    user32.GetLastInputInfo(ctypes.byref(i))
    return ((kernel32.GetTickCount() - i.dwTime) & 0xFFFFFFFF) / 1000


# ----- teclas y bandeja -----------------------------------------------------

def press(*keys):
    for k in keys:
        user32.keybd_event(k, 0, 0, 0)
    for k in reversed(keys):
        user32.keybd_event(k, 0, 2, 0)


def tray_click(item, right):
    """Avisa al dueño de un icono de la bandeja de que se ha pulsado."""
    hwnd, uid, cb, version = item["hwnd"], item["uid"], item["callback"], item["version"]
    if not cb:
        return
    pos = w.POINT()
    user32.GetCursorPos(ctypes.byref(pos))
    user32.AllowSetForegroundWindow(pid_of(hwnd))
    for msg in tray_messages(right, version):
        if version >= 4:
            wp = (pos.x & 0xFFFF) | (pos.y & 0xFFFF) << 16
            lp = (msg & 0xFFFF) | (uid & 0xFFFF) << 16
        else:
            wp, lp = uid, msg
        user32.PostMessageW(hwnd, cb, wp, ctypes.c_ssize_t(lp).value)


def tray_messages(right, version):
    if right:
        return [0x204, 0x205] + ([0x7B] if version >= 3 else [])      # RBUTTON, CONTEXTMENU
    return [0x201, 0x202] + ([0x400] if version >= 3 else [])         # LBUTTON, NIN_SELECT


# ----- iconos ---------------------------------------------------------------

def window_hicon(hwnd):
    for kind in (1, 2, 0):           # grande, pequeño escalado, pequeño
        res = ctypes.c_size_t()
        ok = user32.SendMessageTimeoutW(hwnd, 0x7F, kind, 0, 2, 80, ctypes.byref(res))
        if ok and res.value:
            return res.value
    return user32.GetClassLongPtrW(hwnd, -14) or user32.GetClassLongPtrW(hwnd, -34)


class GUID(ctypes.Structure):
    _fields_ = [("b", ctypes.c_ubyte * 16)]

    def __init__(self, text):
        super().__init__((ctypes.c_ubyte * 16)(*uuid.UUID(text).bytes_le))


class PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", w.DWORD)]


class PROPVARIANT(ctypes.Structure):
    _fields_ = [("vt", w.WORD), ("r", w.WORD * 3), ("p", ctypes.c_void_p), ("q", ctypes.c_void_p)]


def method(obj, index, *types):
    """El método número `index` de una interfaz COM."""
    table = ctypes.cast(obj, _P(_P(ctypes.c_void_p)))[0]
    return lambda *a: ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *types)(table[index])(obj, *a)


def app_id(hwnd):
    """El AppUserModelID de una ventana, o ""."""
    store = ctypes.c_void_p()
    iid = GUID("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99")
    if shell32.SHGetPropertyStoreForWindow(w.HWND(hwnd), ctypes.byref(iid), ctypes.byref(store)) < 0:
        return ""
    try:
        key = PROPERTYKEY(GUID("9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3"), 5)
        var = PROPVARIANT()
        if method(store, 5, ctypes.c_void_p, ctypes.c_void_p)(ctypes.byref(key), ctypes.byref(var)) < 0:
            return ""
        text = ctypes.wstring_at(var.p) if var.vt == 31 and var.p else ""
        ole32.PropVariantClear(ctypes.byref(var))
        return text
    finally:
        method(store, 2)()


def store_icon(aumid, size=32):
    """HBITMAP del icono de una app de la Tienda, o None."""
    item, iid = ctypes.c_void_p(), GUID("bcc18b79-ba16-442f-80c4-8a59c30c463b")
    if shell32.SHCreateItemFromParsingName(ctypes.c_wchar_p("shell:AppsFolder\\" + aumid), None,
                                           ctypes.byref(iid), ctypes.byref(item)) < 0:
        return None
    try:
        bmp = w.HBITMAP()
        hr = method(item, 3, w.SIZE, ctypes.c_int, ctypes.c_void_p)(w.SIZE(size, size), 4, ctypes.byref(bmp))
        return bmp.value if hr >= 0 else None
    finally:
        method(item, 2)()
