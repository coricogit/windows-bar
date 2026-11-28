"""Barras de frecuencias del sonido del equipo, al estilo de cava.

Proceso aparte, solo mientras suena música: captura lo que sale por los altavoces
(WASAPI en bucle; nunca el micrófono, y sin guardar nada), lo separa en bandas y
escribe una lista JSON de números de 0 a 100 por fotograma. Termina al cerrarse
su entrada.

    python cava.py FOTOGRAMAS_POR_SEGUNDO
"""
import array
import ctypes
import json
import math
import operator
import os
import sys
import threading
import time
from ctypes import wintypes as w

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from barra.win import GUID, method, ole32  # noqa: E402

BARRAS = 16
DESDE, HASTA = 50, 9000          # Hz
MAX_MUESTRAS = 2048
SUELO = 0.0015                   # por debajo es silencio: no se amplifica
CAMBIO = 2                       # de 100: lo que se nota (un píxel en una barra de 40-50 px)

producto = getattr(math, "sumprod", None) or (lambda a, b: sum(map(operator.mul, a, b)))


class Espectro:
    """Muestras a alturas de barra. Cada banda mira una ventana tan larga como
    pide su grosor: larga en los graves, corta y varias veces en los agudos."""

    def __init__(self, frecuencia):
        self.frecuencia = frecuencia
        self.muestras = [0.0] * MAX_MUESTRAS
        self.barras, self.tope = [0.0] * BARRAS, SUELO
        paso = (HASTA / DESDE) ** (1 / BARRAS)
        self.bandas = []
        for i in range(BARRAS):
            f = DESDE * paso ** (i + 0.5)
            ancho = f * (paso - 1)
            n = max(128, min(MAX_MUESTRAS, round(frecuencia * 2.5 / ancho)))
            hann = [0.5 - 0.5 * math.cos(2 * math.pi * k / n) for k in range(n)]
            g = 2 * math.pi * f / frecuencia
            norma = 2 / sum(hann) * (f / 1000) ** 0.35       # los agudos llevan menos energía
            veces = max(1, min(4, MAX_MUESTRAS // 2 // n))
            self.bandas.append((n, veces, [h * math.cos(g * k) * norma for k, h in enumerate(hann)],
                                [h * math.sin(g * k) * norma for k, h in enumerate(hann)]))

    def anadir(self, nuevas):
        if nuevas:
            self.muestras = (self.muestras + nuevas[-MAX_MUESTRAS:])[-MAX_MUESTRAS:]

    def fuerzas(self):
        out = []
        for n, veces, c, s in self.bandas:
            e = 0.0
            for v in range(veces):
                fin = MAX_MUESTRAS - v * n
                x = self.muestras[fin - n:fin]
                e = max(e, producto(x, c) ** 2 + producto(x, s) ** 2)
            out.append(math.sqrt(e))
        return out

    def fotograma(self, dt):
        """Las barras, de 0 a 100: suben rápido y caen con suavidad."""
        fuerzas = self.fuerzas()
        mas = max(fuerzas)
        # La sensibilidad se ajusta sola al volumen.
        self.tope = max(SUELO, mas, self.tope * math.exp(-dt / 4))
        for i, f in enumerate(fuerzas):
            quiere = min(1.0, (f / self.tope) ** 0.75) if f > SUELO / 8 else 0.0
            b = self.barras[i]
            self.barras[i] = b + (quiere - b) * min(1, dt * 28) if quiere > b else max(quiere, b - dt * (0.6 + 2.2 * b))
        return [round(b * 100) for b in self.barras]


def a_mono(datos, canales, saltos, real):
    """Una de cada `saltos` muestras, con sus canales sumados."""
    a = array.array("f" if real else "h", datos)
    paso = canales * saltos
    izq = a[0::paso]
    if canales > 1:
        der = a[1::paso]
        return [(x + y) * 0.5 for x, y in zip(izq, der)] if real else [(x + y) / 65536 for x, y in zip(izq, der)]
    return list(izq) if real else [x / 32768 for x in izq]


class Captura:
    """Lo que suena por la salida predeterminada."""

    def __init__(self):
        self.objetos, self.cliente, self.captura = [], None, None
        try:
            self._abrir()
        except Exception:
            self.cerrar()
            raise

    def _hr(self, hr):
        if hr < 0:
            raise OSError(f"audio: {hr & 0xFFFFFFFF:#x}")

    @staticmethod
    def _salida():
        enum, dev = ctypes.c_void_p(), ctypes.c_void_p()
        clsid, iid = GUID("bcde0395-e52f-467c-8e3d-c4579291692e"), GUID("a95664d2-9614-4f35-a746-de8db63617e6")
        if ole32.CoCreateInstance(ctypes.byref(clsid), None, 23, ctypes.byref(iid), ctypes.byref(enum)) < 0:
            raise OSError("audio: sin enumerador")
        hr = method(enum, 4, ctypes.c_int, ctypes.c_int, ctypes.c_void_p)(0, 1, ctypes.byref(dev))
        method(enum, 2)()
        if hr < 0:
            raise OSError("audio: sin salida")
        return dev

    @staticmethod
    def _id(dev):
        p = ctypes.c_void_p()
        if method(dev, 5, ctypes.c_void_p)(ctypes.byref(p)) < 0:
            return ""
        texto = ctypes.wstring_at(p.value)
        ole32.CoTaskMemFree(p)
        return texto

    def _abrir(self):
        dev = self._salida()
        self.objetos.append(dev)
        self.ident = self._id(dev)
        self.cliente, fmt = ctypes.c_void_p(), ctypes.c_void_p()
        iid = GUID("1cb9ad4c-dbfa-4c32-b178-c2f568a703b2")
        self._hr(method(dev, 3, ctypes.c_void_p, w.DWORD, ctypes.c_void_p, ctypes.c_void_p)(
            ctypes.byref(iid), 23, None, ctypes.byref(self.cliente)))
        self.objetos.append(self.cliente)
        self._hr(method(self.cliente, 8, ctypes.c_void_p)(ctypes.byref(fmt)))
        try:
            cab = ctypes.string_at(fmt.value, 18)
            tipo, self.canales = int.from_bytes(cab[0:2], "little"), int.from_bytes(cab[2:4], "little")
            ritmo, bits = int.from_bytes(cab[4:8], "little"), int.from_bytes(cab[14:16], "little")
            self.bloque = int.from_bytes(cab[12:14], "little")
            if tipo == 0xFFFE:
                tipo = int.from_bytes(ctypes.string_at(fmt.value + 24, 2), "little")
            self.real = tipo == 3
            if (tipo, bits) not in ((3, 32), (1, 16)):
                raise OSError("audio: formato desconocido")
            self.saltos = max(1, round(ritmo / 24000))
            self.frecuencia = ritmo / self.saltos
            # Compartido, en bucle, con 200 ms de margen.
            self._hr(method(self.cliente, 3, ctypes.c_int, w.DWORD, ctypes.c_longlong, ctypes.c_longlong, ctypes.c_void_p,
                            ctypes.c_void_p)(0, 0x20000, 2_000_000, 0, fmt, None))
        finally:
            ole32.CoTaskMemFree(fmt)
        self.captura = ctypes.c_void_p()
        iid = GUID("c8adbd64-e71e-48a0-a4de-185c395cd317")
        self._hr(method(self.cliente, 14, ctypes.c_void_p, ctypes.c_void_p)(ctypes.byref(iid), ctypes.byref(self.captura)))
        self.objetos.append(self.captura)
        self._hr(method(self.cliente, 10)())
        self._quedan = method(self.captura, 5, ctypes.c_void_p)
        self._coger = method(self.captura, 3, *[ctypes.c_void_p] * 5)
        self._soltar = method(self.captura, 4, w.UINT)

    def sigue(self):
        """¿La salida predeterminada es todavía esta?"""
        dev = self._salida()
        igual = self._id(dev) == self.ident
        method(dev, 2)()
        return igual

    def leer(self):
        out, n = [], w.UINT()
        while True:
            self._hr(self._quedan(ctypes.byref(n)))
            if not n.value:
                return out
            p, cuantas, flags = ctypes.c_void_p(), w.UINT(), w.DWORD()
            self._hr(self._coger(ctypes.byref(p), ctypes.byref(cuantas), ctypes.byref(flags), None, None))
            if flags.value & 2:                # silencio
                out += [0.0] * (cuantas.value // self.saltos)
            elif cuantas.value:
                out += a_mono(ctypes.string_at(p.value, cuantas.value * self.bloque), self.canales, self.saltos, self.real)
            self._hr(self._soltar(cuantas))

    def cerrar(self):
        if self.captura:
            method(self.cliente, 11)()
        for o in reversed(self.objetos):
            if o:
                method(o, 2)()
        self.objetos, self.captura = [], None


def correr(fps):
    ole32.CoInitializeEx(None, 0)
    fin = threading.Event()

    def esperar():
        try:
            while sys.stdin.readline():
                pass
        except (OSError, ValueError):
            pass
        fin.set()
    threading.Thread(target=esperar, daemon=True).start()
    cap = esp = None
    antes = revisado = time.perf_counter()
    ultimo, fallos = None, 0
    siguiente = time.perf_counter()
    # Por plazos: el reloj de Windows va a saltos de 16 ms y se compensa solo.
    while True:
        siguiente = max(siguiente + 1 / fps, time.perf_counter() - 0.1)
        if fin.wait(max(0.001, siguiente - time.perf_counter() - 0.004)):
            break
        ahora = time.perf_counter()
        dt, antes = min(0.2, ahora - antes), ahora
        try:
            if cap is None:
                cap = Captura()
                esp = Espectro(cap.frecuencia)
                revisado = ahora
            nuevas = cap.leer()
            # Si nada suena no llegan muestras: cuentan como silencio.
            esp.anadir(nuevas or [0.0] * int(dt * cap.frecuencia))
            fallos = 0
            if ahora - revisado > 3:
                revisado = ahora
                if not cap.sigue():
                    raise OSError("cambió la salida")
        except OSError:
            if cap:
                cap.cerrar()
            cap, fallos = None, fallos + 1
            if fin.wait(min(5, 0.5 * fallos)):
                break
            continue
        f = esp.fotograma(dt)
        if ultimo is None or any(abs(a - b) >= CAMBIO for a, b in zip(f, ultimo)) or (max(f) == 0) != (max(ultimo) == 0):
            ultimo = f
            print(json.dumps(f), flush=True)
    if cap:
        cap.cerrar()


if __name__ == "__main__":
    try:
        correr(max(5, min(60, int(sys.argv[1]))))
    except (OSError, ValueError, IndexError):
        pass
