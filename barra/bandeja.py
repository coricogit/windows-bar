"""Anfitrión de la bandeja: recibe los iconos que registran los programas.

Se ejecuta en su propio proceso, para que nada de lo que haga la barra pueda
bloquear a los programas que llaman a Shell_NotifyIcon. Crea una ventana
invisible de clase Shell_TrayWnd por delante de la de Explorer, anota los
iconos y reenvía cada mensaje a la barra real, que sigue al día. No inyecta
código en ningún proceso; al cerrarse, todo vuelve a ir a Explorer.

Salida: una línea JSON por cambio. Termina cuando se cierra su entrada
estándar (es decir, cuando muere la barra).
"""
import base64
import ctypes
import json
import os
import struct
import sys
import threading
from ctypes import wintypes as w

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM)

WM_DESTROY, WM_CLOSE, WM_COPYDATA, WM_TIMER = 0x02, 0x10, 0x4A, 0x113
NIM_ADD, NIM_MODIFY, NIM_DELETE, NIM_SETFOCUS, NIM_SETVERSION = range(5)
NIF_MESSAGE, NIF_ICON, NIF_TIP, NIF_STATE, NIF_GUID = 1, 2, 4, 8, 0x20
NIS_HIDDEN = 1
SIGNATURE = 0x34753423
ICON = 32

# Iconos del propio Windows (volumen, red, batería...): la barra trae los suyos.
SYSTEM_GUIDS = {f"7820ae{n}-23e3-4229-82c1-e41cb67d5b9c" for n in (73, 74, 75, 76, 77, 78, 82)}


class COPYDATASTRUCT(ctypes.Structure):
    _fields_ = [("dwData", ctypes.c_size_t), ("cbData", w.DWORD), ("lpData", ctypes.c_void_p)]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", w.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", w.HINSTANCE), ("hIcon", w.HICON),
                ("hCursor", w.HANDLE), ("hbrBackground", w.HBRUSH), ("lpszMenuName", w.LPCWSTR),
                ("lpszClassName", w.LPCWSTR)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", w.DWORD), ("biWidth", w.LONG), ("biHeight", w.LONG), ("biPlanes", w.WORD),
                ("biBitCount", w.WORD), ("biCompression", w.DWORD), ("biSizeImage", w.DWORD),
                ("biXPelsPerMeter", w.LONG), ("biYPelsPerMeter", w.LONG), ("biClrUsed", w.DWORD),
                ("biClrImportant", w.DWORD)]


def _sig(lib, name, res, *args):
    f = getattr(lib, name)
    f.restype, f.argtypes = res, args
    return f


_sig(user32, "DefWindowProcW", LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
_sig(user32, "CreateWindowExW", w.HWND, w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, *[ctypes.c_int] * 4,
     w.HWND, w.HMENU, w.HINSTANCE, w.LPVOID)
_sig(user32, "FindWindowExW", w.HWND, w.HWND, w.HWND, w.LPCWSTR, w.LPCWSTR)
_sig(user32, "GetWindowThreadProcessId", w.DWORD, w.HWND, ctypes.POINTER(w.DWORD))
_sig(user32, "SendMessageTimeoutW", LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM, w.UINT, w.UINT,
     ctypes.POINTER(ctypes.c_size_t))
_sig(user32, "SendNotifyMessageW", w.BOOL, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
_sig(user32, "PostMessageW", w.BOOL, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
_sig(user32, "SetWindowPos", w.BOOL, w.HWND, w.HWND, *[ctypes.c_int] * 4, w.UINT)
_sig(user32, "GetWindowRect", w.BOOL, w.HWND, ctypes.POINTER(w.RECT))
_sig(user32, "IsWindow", w.BOOL, w.HWND)
_sig(user32, "DestroyWindow", w.BOOL, w.HWND)
_sig(user32, "SetTimer", ctypes.c_size_t, w.HWND, ctypes.c_size_t, w.UINT, ctypes.c_void_p)
_sig(user32, "RegisterWindowMessageW", w.UINT, w.LPCWSTR)
_sig(user32, "ChangeWindowMessageFilterEx", w.BOOL, w.HWND, w.UINT, w.DWORD, ctypes.c_void_p)
_sig(user32, "DrawIconEx", w.BOOL, w.HDC, ctypes.c_int, ctypes.c_int, w.HICON, ctypes.c_int, ctypes.c_int,
     w.UINT, w.HBRUSH, w.UINT)
_sig(user32, "GetDC", w.HDC, w.HWND)
_sig(user32, "ReleaseDC", ctypes.c_int, w.HWND, w.HDC)
_sig(gdi32, "CreateCompatibleDC", w.HDC, w.HDC)
_sig(gdi32, "DeleteDC", w.BOOL, w.HDC)
_sig(gdi32, "CreateDIBSection", w.HBITMAP, w.HDC, ctypes.c_void_p, w.UINT, ctypes.POINTER(ctypes.c_void_p),
     w.HANDLE, w.DWORD)
_sig(gdi32, "SelectObject", w.HGDIOBJ, w.HDC, w.HGDIOBJ)
_sig(gdi32, "DeleteObject", w.BOOL, w.HGDIOBJ)
_sig(kernel32, "GetModuleHandleW", w.HMODULE, w.LPCWSTR)
_sig(kernel32, "OpenProcess", w.HANDLE, w.DWORD, w.BOOL, w.DWORD)
_sig(kernel32, "CloseHandle", w.BOOL, w.HANDLE)
_sig(kernel32, "QueryFullProcessImageNameW", w.BOOL, w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD))


def pid_of(hwnd):
    pid = w.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def exe_of(pid):
    h = kernel32.OpenProcess(0x1000, False, pid)
    if not h:
        return ""
    try:
        buf, n = ctypes.create_unicode_buffer(1024), w.DWORD(1024)
        return buf.value if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)) else ""
    finally:
        kernel32.CloseHandle(h)


def parse(data):
    """El mensaje de Shell_NotifyIcon, o None si no lo es. Los manejadores van
    en 32 bits aunque el programa sea de 64."""
    if len(data) < 32:
        return None
    sig, msg, size, hwnd, uid, flags, callback, hicon = struct.unpack_from("<8I", data)
    if sig != SIGNATURE:
        return None

    def text(off, chars):
        raw = data[off:off + chars * 2]
        return raw[:len(raw) & ~1].decode("utf-16-le", "replace").split("\0")[0]

    def dword(off):
        return struct.unpack_from("<I", data, off)[0] if len(data) >= off + 4 else 0

    out = {"msg": msg, "hwnd": hwnd, "uid": uid, "flags": flags, "callback": callback, "hicon": hicon,
           "tip": text(32, 128), "state": dword(288), "mask": dword(292), "version": dword(808), "guid": ""}
    if flags & NIF_GUID and len(data) >= 960:
        a, b, c, d = struct.unpack_from("<IHH8s", data, 944)
        out["guid"] = f"{a:08x}-{b:04x}-{c:04x}-{d[:2].hex()}-{d[2:].hex()}"
    return out


class Icons:
    """Los iconos que hay ahora. `apply` devuelve la clave si algo cambió."""

    def __init__(self):
        self.items = {}

    def apply(self, n):
        key = n["guid"] or f'{n["hwnd"]}:{n["uid"]}'
        if n["msg"] == NIM_DELETE:
            return key if self.items.pop(key, None) else None
        if n["msg"] not in (NIM_ADD, NIM_MODIFY, NIM_SETVERSION):
            return None
        it = self.items.get(key)
        if it is None:
            if n["msg"] == NIM_SETVERSION:
                return None
            it = self.items[key] = {"key": key, "hwnd": n["hwnd"], "uid": n["uid"], "guid": n["guid"],
                                    "callback": 0, "hicon": 0, "tip": "", "hidden": False, "version": 0}
        it["hwnd"], it["uid"] = n["hwnd"], n["uid"]
        if n["msg"] == NIM_SETVERSION:
            it["version"] = n["version"]
            return key
        if n["flags"] & NIF_MESSAGE:
            it["callback"] = n["callback"]
        if n["flags"] & NIF_ICON:
            it["hicon"] = n["hicon"]
        if n["flags"] & NIF_TIP:
            it["tip"] = n["tip"]
        if n["flags"] & NIF_STATE and n["mask"] & NIS_HIDDEN:
            it["hidden"] = bool(n["state"] & NIS_HIDDEN)
        return key


def icon_pixels(hicon):
    """El icono en BGRA de ICON x ICON, en base64."""
    if not hicon:
        return ""
    info = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), ICON, -ICON, 1, 32, 0, 0, 0, 0, 0, 0)
    screen = user32.GetDC(None)
    dc = gdi32.CreateCompatibleDC(screen)
    bits = ctypes.c_void_p()
    bmp = gdi32.CreateDIBSection(dc, ctypes.byref(info), 0, ctypes.byref(bits), None, 0)
    old = gdi32.SelectObject(dc, bmp)
    try:
        if not bits.value or not user32.DrawIconEx(dc, 0, 0, hicon, ICON, ICON, 0, None, 3):
            return ""
        raw = bytearray(ctypes.string_at(bits.value, ICON * ICON * 4))
        if not any(raw[3::4]):       # icono antiguo, sin canal alfa
            for i in range(0, len(raw), 4):
                if raw[i] or raw[i + 1] or raw[i + 2]:
                    raw[i + 3] = 255
        return base64.b64encode(bytes(raw)).decode()
    finally:
        gdi32.SelectObject(dc, old)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(dc)
        user32.ReleaseDC(None, screen)


class Host:
    def __init__(self, out):
        self.out = out
        self.icons = Icons()
        self.hwnd = None
        self._real = None

    def real(self):
        """La Shell_TrayWnd de Explorer."""
        if self._real and user32.IsWindow(self._real):
            return self._real
        h = None
        while True:
            h = user32.FindWindowExW(None, h, "Shell_TrayWnd", None)
            if not h:
                self._real = None
                return None
            if pid_of(h) != os.getpid():
                self._real = h
                return h

    def forward(self, msg, wp, lp):
        real, res = self.real(), ctypes.c_size_t()
        if not real:
            return 0
        user32.SendMessageTimeoutW(real, msg, wp, lp, 0x2, 3000, ctypes.byref(res))
        return res.value

    def emit(self, key):
        it = self.icons.items.get(key)
        if it is None:
            msg = {"op": "quitar", "key": key}
        else:
            exe = exe_of(pid_of(it["hwnd"]))
            msg = {"op": "poner", **it, "exe": exe, "pixels": icon_pixels(it["hicon"])}
        self.out.write(json.dumps(msg) + "\n")
        self.out.flush()

    def proc(self, hwnd, msg, wp, lp):
        try:
            if msg == WM_COPYDATA:
                cds = ctypes.cast(lp, ctypes.POINTER(COPYDATASTRUCT))[0]
                data = ctypes.string_at(cds.lpData, cds.cbData) if cds.lpData else b""
                res = self.forward(msg, wp, lp)
                if cds.dwData == 1:
                    n = parse(data)
                    if n and n["guid"] not in SYSTEM_GUIDS:
                        key = self.icons.apply(n)
                        if key:
                            self.emit(key)
                        if n["msg"] == NIM_ADD and key:
                            return 1     # Explorer dice que no si ya lo tenía
                return res
            if msg == WM_TIMER:
                self.tick()
                return 0
            if msg == WM_CLOSE:
                user32.DestroyWindow(hwnd)
                return 0
            if msg == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            if 0x400 <= msg < 0xC000:    # mensajes privados de la barra real
                return self.forward(msg, wp, lp)
        except Exception as e:
            print("bandeja:", repr(e), file=sys.stderr)
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    def tick(self):
        for key, it in list(self.icons.items.items()):
            if not user32.IsWindow(it["hwnd"]):       # el programa se cerró sin avisar
                del self.icons.items[key]
                self.emit(key)
        self.on_top()

    def on_top(self):
        r = w.RECT()
        if self.real():
            user32.GetWindowRect(self.real(), ctypes.byref(r))
        # SWP_NOACTIVATE; sigue sin ser visible
        user32.SetWindowPos(self.hwnd, w.HWND(-1), r.left, r.top, r.right - r.left, r.bottom - r.top, 0x10)

    def run(self):
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        self._proc = WNDPROC(self.proc)
        inst = kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW(lpfnWndProc=self._proc, hInstance=inst, lpszClassName="Shell_TrayWnd")
        if not user32.RegisterClassW(ctypes.byref(wc)):
            raise ctypes.WinError(ctypes.get_last_error())
        # WS_EX_TOPMOST | TOOLWINDOW | NOACTIVATE, WS_POPUP sin WS_VISIBLE
        self.hwnd = user32.CreateWindowExW(0x08000088, "Shell_TrayWnd", "", 0x80000000, 0, 0, 0, 0,
                                           None, None, inst, None)
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        user32.ChangeWindowMessageFilterEx(self.hwnd, WM_COPYDATA, 1, None)
        self.on_top()
        user32.SetTimer(self.hwnd, 1, 1000, None)
        threading.Thread(target=self._wait_stdin, daemon=True).start()
        # Pide a los programas que vuelvan a registrar sus iconos.
        user32.SendNotifyMessageW(w.HWND(0xFFFF), user32.RegisterWindowMessageW("TaskbarCreated"), 0, 0)
        msg = w.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.DispatchMessageW(ctypes.byref(msg))

    def _wait_stdin(self):
        try:
            while sys.stdin.readline():
                pass
        except (OSError, ValueError):
            pass
        user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)


if __name__ == "__main__":
    Host(sys.stdout).run()
