"""Lo que suena ahora (Spotify, navegador...), por la sesión multimedia de Windows.

Habla con Windows directamente (WinRT con ctypes), sin librerías: así todo lo que
se instala va firmado por su autor y Smart App Control no tiene qué bloquear.
"""
import ctypes
import queue
import threading
import time

from .win import GUID, method

combase = ctypes.WinDLL("combase")
shcore = ctypes.WinDLL("shcore")
GESTOR = "Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager"
IID_GESTOR = "2050c4ee-11a0-57de-aed7-c97c70338245"        # ...SessionManagerStatics
IID_ASYNC = "00000036-0000-0000-c000-000000000046"         # IAsyncInfo
SONANDO = 4
ORDENES = {"pausa": 20, "siguiente": 16, "anterior": 17}   # su sitio en la interfaz de la sesión
NADA = {"titulo": "", "artista": "", "sonando": False}
IID_ISTREAM = "0000000c-0000-0000-c000-000000000046"
MAX_PORTADA = 4 * 1024 * 1024      # una carátula no pesa más; si sí, algo va mal

combase.WindowsGetStringRawBuffer.restype = ctypes.c_void_p
combase.WindowsGetStringRawBuffer.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
combase.WindowsDeleteString.argtypes = (ctypes.c_void_p,)
combase.WindowsCreateString.argtypes = (ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_void_p)
combase.RoGetActivationFactory.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
shcore.CreateStreamOverRandomAccessStream.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)


def _bien(hr):
    if hr < 0:
        raise OSError(f"multimedia: {hr & 0xFFFFFFFF:#x}")


class Objeto:
    """Una interfaz COM que se suelta sola."""

    def __init__(self, p):
        self.p = p

    def __bool__(self):
        return bool(self.p)

    def __del__(self):
        if self.p:
            method(self.p, 2)()
            self.p = None

    def pedir(self, indice):
        """El objeto que devuelve ese método sin argumentos."""
        out = ctypes.c_void_p()
        _bien(method(self.p, indice, ctypes.c_void_p)(ctypes.byref(out)))
        return Objeto(out)

    def entero(self, indice):
        out = ctypes.c_int()
        _bien(method(self.p, indice, ctypes.c_void_p)(ctypes.byref(out)))
        return out.value

    def texto(self, indice):
        h = ctypes.c_void_p()
        _bien(method(self.p, indice, ctypes.c_void_p)(ctypes.byref(h)))
        if not h:
            return ""
        try:
            return ctypes.wstring_at(combase.WindowsGetStringRawBuffer(h, None))
        finally:
            combase.WindowsDeleteString(h)

    def esperar(self, limite=3):
        """Espera a esta operación asíncrona."""
        info, iid = ctypes.c_void_p(), GUID(IID_ASYNC)
        _bien(method(self.p, 0, ctypes.c_void_p, ctypes.c_void_p)(ctypes.byref(iid), ctypes.byref(info)))
        info, fin = Objeto(info), time.monotonic() + limite
        while True:
            estado = info.entero(7)
            if estado == 1:
                return self
            if estado != 0 or time.monotonic() > fin:
                raise OSError("multimedia: sin respuesta")
            time.sleep(0.01)

    def resultado(self):
        return self.esperar().pedir(8)


def abrir_gestor():
    h, f, iid = ctypes.c_void_p(), ctypes.c_void_p(), GUID(IID_GESTOR)
    _bien(combase.WindowsCreateString(GESTOR, len(GESTOR), ctypes.byref(h)))
    try:
        _bien(combase.RoGetActivationFactory(h, ctypes.byref(iid), ctypes.byref(f)))
    finally:
        combase.WindowsDeleteString(h)
    return Objeto(f).pedir(6).resultado()          # RequestAsync


def leer(gestor):
    s = gestor.pedir(6)                            # GetCurrentSession
    if not s:
        return dict(NADA)
    p = s.pedir(7).resultado()                     # TryGetMediaPropertiesAsync
    if not p:
        return dict(NADA)
    return {"titulo": p.texto(6), "artista": p.texto(9), "sonando": s.pedir(9).entero(7) == SONANDO}


def portada(gestor):
    """Los bytes de la carátula de lo que suena (PNG o JPEG), o b"" si no tiene.
    Thumbnail (15) → OpenReadAsync (6) → un IStream de COM con
    CreateStreamOverRandomAccessStream, que se lee con Read (3)."""
    s = gestor.pedir(6)
    if not s:
        return b""
    p = s.pedir(7).resultado()
    if not p:
        return b""
    ref = p.pedir(15)                              # get_Thumbnail
    if not ref:
        return b""
    flujo_winrt = ref.pedir(6).resultado()         # OpenReadAsync
    if not flujo_winrt:
        return b""
    out, iid = ctypes.c_void_p(), GUID(IID_ISTREAM)
    _bien(shcore.CreateStreamOverRandomAccessStream(flujo_winrt.p, ctypes.byref(iid), ctypes.byref(out)))
    flujo = Objeto(out)
    leer_trozo = method(flujo.p, 3, ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p)
    datos, trozo, n = bytearray(), ctypes.create_string_buffer(65536), ctypes.c_ulong()
    while len(datos) < MAX_PORTADA:
        if leer_trozo(trozo, len(trozo), ctypes.byref(n)) < 0 or not n.value:
            break
        datos += trozo.raw[:n.value]
    return bytes(datos) if len(datos) < MAX_PORTADA else b""


def ordenar(gestor, nombre):
    s = gestor.pedir(6)
    if s and nombre in ORDENES:
        s.pedir(ORDENES[nombre]).esperar()


class Musica:
    def __init__(self, avisar):
        """`avisar(dict)` se llama desde otro hilo cuando algo cambia."""
        self.avisar = avisar
        self.pausada = False         # modo juego: no consulta
        self._ultimo = None
        self._portada_de, self._portada, self._intentos = None, b"", 0
        self._cola = queue.Queue()
        threading.Thread(target=self._hilo, daemon=True).start()

    def _hilo(self):
        combase.RoInitialize(1)      # en este hilo, multihilo
        gestor, fallos = None, 0
        while True:
            nombre = None
            try:
                nombre = self._cola.get(timeout=1.5)
            except queue.Empty:
                pass
            if self.pausada and not nombre:
                continue
            try:
                gestor = gestor or abrir_gestor()
                if nombre:
                    ordenar(gestor, nombre)
                datos = leer(gestor)
                datos["portada"] = self._caratula(gestor, datos)
                fallos = 0
            except Exception:        # la sesión se cerró a mitad de la consulta
                gestor, datos, fallos = None, dict(NADA), fallos + 1
                if fallos > 5:
                    time.sleep(min(60, fallos))
            if datos != self._ultimo:
                self._ultimo = datos
                self.avisar(datos)

    def _caratula(self, gestor, datos):
        """La de la canción de ahora; se pide al cambiar de canción y, si aún no
        estaba (Spotify la pone un poco después del título), unas veces más."""
        clave = (datos["titulo"], datos["artista"])
        if not datos["titulo"]:
            self._portada_de, self._portada = clave, b""
            return b""
        if clave != self._portada_de:
            self._portada_de, self._portada, self._intentos = clave, b"", 0
        if not self._portada and self._intentos < 4:
            self._intentos += 1
            try:
                self._portada = portada(gestor)
            except Exception:
                self._portada = b""
        return self._portada

    def orden(self, nombre):
        """"pausa", "siguiente" o "anterior"."""
        self._cola.put(nombre)
