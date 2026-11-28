"""El menú de ajustes (qml/Ajustes.qml): la barra en grande arriba, que prueba cada
opción al pasar el ratón o el teclado por ella, y debajo las opciones con su imagen.

Las imágenes y la vista previa salen de un «estudio»: una barra de mentira, fuera de
la pantalla (barra.pyw, preparar_vista), a la que se le ponen los ajustes con el
cambio de cada opción. Así nunca se toca la barra de verdad hasta que se pulsa. Las
miniaturas se guardan en disco por tema, gama y momento, y el estudio se cierra un
rato después de cerrar el menú (ocupa unos 30 MB).

Accesible (WCAG 2.1 AA): todo con teclado (Tab, flechas, Intro/Espacio, Esc), foco
visible, nombres y estados para el lector de pantalla, sin depender solo del color
(lo elegido lleva una marca), y el tamaño del texto de Windows.
"""
import copy
import hashlib
import json
import os
import sys
import threading
import time

from PySide6.QtCore import Property, QCoreApplication, QObject, QRect, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QImage

ESPERA_MS = 15                   # el estudio ya ha dibujado: grabWindow pinta en el momento
CALMA_S = 0.0                    # con su propio proceso, las miniaturas ya no estorban: sin pausa
RESPIRO_MS = 20                  # un respiro entre miniatura y miniatura
CIERRA_ESTUDIO_MS = 45_000
PLAZO_MS, PLAZO_ARRANQUE_MS = 8_000, 25_000      # sin respuesta en este tiempo: se da por colgado
MAX_MINIATURAS = 400


def aplicar(ajustes, cambios):
    """Una copia de `ajustes` con `cambios` [[ruta, valor], ...]; la ruta es "a" o "a.b"."""
    out = copy.deepcopy(ajustes)
    for ruta, valor in cambios:
        partes = ruta.split(".")
        d = out
        for p in partes[:-1]:
            d = d.setdefault(p, {})
        d[partes[-1]] = valor
    return out


def clave(cambios, contexto):
    """Nombre de archivo de una miniatura: cambia si cambian la opción o el tema, gama, momento..."""
    return hashlib.sha1(json.dumps([cambios, contexto], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]


def caja_visible(img, paso=2):
    """El rectángulo con algo dibujado (alfa > 20) de una QImage, o None."""
    img = img.convertToFormat(QImage.Format.Format_ARGB32)
    an, al = img.width(), img.height()
    xs = [x for x in range(0, an, paso) if any((img.pixel(x, y) >> 24) > 20 for y in range(0, al, 3))]
    ys = [y for y in range(al) if any((img.pixel(x, y) >> 24) > 20 for x in range(0, an, 6))]
    if not xs or not ys:
        return None
    return QRect(xs[0], ys[0], min(an, xs[-1] + paso) - xs[0], ys[-1] - ys[0] + 1)


def buscar_modulo(raiz, nombre):
    """El Modulo (qml/Modulo.qml) de ese nombre que se ve en la barra, o None."""
    pendientes = [raiz]
    while pendientes:
        it = pendientes.pop()
        if it.property("nombre") == nombre and it.width() > 0 and it.height() > 0 and it.isVisible():
            return it
        pendientes.extend(it.childItems())
    return None


def pintar(barra, panel, pedido, listo):
    """En el proceso del estudio: pone en `barra` los ajustes de `pedido` y, cuando ha
    dibujado, llama a `listo(QImage)` recortada a su módulo («~inicio»: una franja)."""
    barra.ajustes = pedido["ajustes"]
    barra.ajustes["posicion"] = "abajo"           # la vista previa, siempre en horizontal
    barra.ajustes["esconder"] = False
    barra.ajustes["animaciones"] = "ninguna"      # que la foto no pille nada a medio animar
    for k, v in pedido.get("extra", {}).items():
        setattr(barra, k, v)
    poner_reales(barra, panel, pedido.get("reales"))
    panel.view.setGeometry(-6000, -6000, 1920, barra.alto())
    barra._aplicar_tema(barra.ajustes["tema"])
    recorte = pedido.get("recorte", "")

    def foto():
        img = panel.view.grabWindow()
        if recorte:
            m = buscar_modulo(panel.view.rootObject(), recorte.lstrip("~"))
            if m is not None:
                r = m.mapRectToScene(m.boundingRect()).toAlignedRect()
                if recorte.startswith("~"):              # una franja de la barra, desde un poco antes
                    al = img.height()
                    r = QRect(max(0, r.x() - int(al * 1.2)), 0, al * 9, al)
                else:
                    r = r.adjusted(-4, 0, 4, 0)
                img = img.copy(r.intersected(img.rect()))
        elif pedido.get("ajustar"):                       # la vista previa: solo lo dibujado
            r = caja_visible(img, paso=4)
            if r is not None:
                img = img.copy(r)
        listo(img)
    QTimer.singleShot(ESPERA_MS, foto)


_REALES = {}                    # en el estudio: lo último puesto, para no rehacerlo en cada foto


def poner_reales(barra, panel, reales):
    """En el estudio: tus programas y tu bandeja en vez de los de ejemplo."""
    if not reales or _REALES.get("ultimo") == reales:
        return
    _REALES["ultimo"] = reales

    def url(ruta):
        if not ruta:
            return ""
        nombre = "real_" + os.path.basename(ruta)
        if barra.almacen.get(nombre) is None:
            img = QImage(ruta)
            if img.isNull():
                return ""
            barra.almacen.poner(nombre, img)
        return barra.almacen.url(nombre)
    if reales.get("tareas"):
        panel.tareas.poner([{**f, "icono": url(f.get("icono"))} for f in reales["tareas"]])
    if reales.get("bandeja") is not None:
        barra.tray.poner([{**f, "icono": url(f.get("icono"))} for f in reales["bandeja"]])


def servir(barra, panel, entrada=sys.stdin, salida=sys.stdout):
    """El proceso del estudio (barra.pyw --estudio): una petición JSON por línea en la
    entrada; por cada una, la imagen en su archivo y {"n", "ok"} en la salida. Se va al
    cerrarse la entrada. Lo devuelto hay que guardarlo mientras dure."""
    servidor = _Servidor(barra, panel, salida)
    servidor.vigilar(os.getppid())
    llega = _Llegada()
    llega.linea.connect(servidor.recibir)          # métodos de un QObject: se ejecutan en su hilo (el de Qt)
    llega.fin.connect(servidor.acabar)

    def leer():
        for linea in entrada:
            llega.linea.emit(linea)
        llega.fin.emit()
    threading.Thread(target=leer, daemon=True).start()
    return servidor, llega


class _Llegada(QObject):
    linea = Signal(str)
    fin = Signal()


class _Servidor(QObject):
    def __init__(self, barra, panel, salida):
        super().__init__()
        self.barra, self.panel, self.salida = barra, panel, salida
        self.cola, self.ocupado = [], False

    @Slot(str)
    def recibir(self, linea):
        self._ultimo = time.monotonic()
        try:
            self.cola.append(json.loads(linea))
        except ValueError:
            return
        self.siguiente()

    @Slot()
    def acabar(self):
        QCoreApplication.quit()

    def vigilar(self, padre, sin_uso_s=90):
        """Por si la barra se cierra de golpe y no llega el fin de la entrada: si el proceso
        que lo abrió ya no está, o lleva `sin_uso_s` sin pedir nada, se va."""
        import ctypes
        self._ultimo = time.monotonic()
        k = ctypes.windll.kernel32
        k.OpenProcess.restype = ctypes.c_void_p
        h = k.OpenProcess(0x00100000, False, padre)            # SYNCHRONIZE

        def mirar():
            muerto = not h or k.WaitForSingleObject(ctypes.c_void_p(h), 0) == 0
            if muerto or time.monotonic() - self._ultimo > sin_uso_s:
                QCoreApplication.quit()
        self._vigia = QTimer(self, interval=2000, timeout=mirar)
        self._vigia.start()

    def siguiente(self):
        if self.ocupado or not self.cola:
            return
        self.ocupado = True
        p = self.cola.pop(0)

        def listo(img, p=p):
            ok = bool(not img.isNull() and img.save(p["archivo"]))
            self.salida.write(json.dumps({"n": p["n"], "ok": ok}) + "\n")
            self.salida.flush()
            self.ocupado = False
            QTimer.singleShot(0, self.siguiente)
        try:
            pintar(self.barra, self.panel, p, listo)
        except Exception:
            listo(QImage())


class Estudio(QObject):
    """La barra de mentira donde se prueban las opciones, en su propio proceso
    (barra.pyw --estudio): así dibujar nunca congela el menú. `lanzar()` da el
    subprocess.Popen; `base()` da (ajustes, extra) de la barra de verdad."""
    _respuesta = Signal(str)

    def __init__(self, lanzar, base, carpeta):
        super().__init__()
        self._lanzar, self._base, self._carpeta = lanzar, base, carpeta
        self.proc = None
        self._cola, self._ocupado, self._n, self._esperando = [], False, 0, None
        self.tocado = 0.0                           # la última vez que se usó el menú (time.monotonic)
        self._respuesta.connect(self._llega)
        self._cerrar = QTimer(self, singleShot=True, interval=CIERRA_ESTUDIO_MS, timeout=self.cerrar)
        self._plazo = QTimer(self, singleShot=True, interval=8000, timeout=self._atascado)

    def pedir(self, cambios, recorte, listo, urgente=False, etiqueta=""):
        """Pinta con `cambios` y llama a `listo(QImage)`, recortado al módulo `recorte`
        («~inicio»: una franja de la barra a partir de ese módulo)."""
        self._cerrar.stop()
        if urgente:
            self._cola = [c for c in self._cola if not c[0]]        # la vista previa anterior ya no importa
            self._cola.insert(0, (True, cambios, recorte, listo, etiqueta))
        else:
            self._cola.append((False, cambios, recorte, listo, etiqueta))
        if not self._ocupado:
            self._ocupado = True
            QTimer.singleShot(0, self._siguiente)

    def antes(self, prefijo):
        """Lo de esa categoría primero (las miniaturas que se están mirando)."""
        urg = [c for c in self._cola if c[0]]
        resto = [c for c in self._cola if not c[0]]
        self._cola = urg + [c for c in resto if c[4].startswith(prefijo)] + [c for c in resto if not c[4].startswith(prefijo)]

    def vaciar(self):
        self._cola = []

    def soltar_luego(self):
        self._cerrar.start()

    def _vivo(self):
        if self.proc is None or self.proc.poll() is not None:
            self.proc = self._lanzar()
            threading.Thread(target=self._leer, args=(self.proc,), daemon=True).start()
        return self.proc

    def _leer(self, proc):
        try:
            for linea in proc.stdout:
                self._respuesta.emit(linea)
        except (OSError, ValueError):
            pass

    def _siguiente(self):
        if self._esperando is not None:
            return
        if not self._cola:
            self._ocupado = False
            return
        self._ocupado = True
        # Una miniatura (no urgente) mientras estás usando el menú: luego.
        if not self._cola[0][0] and time.monotonic() - self.tocado < CALMA_S:
            QTimer.singleShot(int(CALMA_S * 1000), self._siguiente)
            return
        urgente, cambios, recorte, listo, _ = self._cola.pop(0)
        try:
            base = self._base()
            ajustes, extra = base[0], base[1]
            reales = base[2] if len(base) > 2 else None
            self._n += 1
            # BMP: sin comprimir, para ir y volver deprisa (las miniaturas se guardan en PNG después).
            archivo = os.path.join(self._carpeta, f"_estudio_{id(self)}_{self._n}.bmp")
            pedido = {"n": self._n, "ajustes": aplicar(ajustes, cambios), "extra": extra, "recorte": recorte,
                      "archivo": archivo, "ajustar": urgente and not recorte, "reales": reales}
            linea = json.dumps(pedido) + "\n"            # en ASCII: da igual la codificación
        except (ValueError, TypeError):                # un dato que no se puede mandar: esta no
            QTimer.singleShot(0, self._siguiente)
            return
        arranca = self.proc is None or self.proc.poll() is not None
        try:
            proc = self._vivo()
            proc.stdin.write(linea)
            proc.stdin.flush()
        except OSError:                                # el proceso se fue: otro, en un momento
            self.proc = None
            self._cola.insert(0, (urgente, cambios, recorte, listo, ""))
            QTimer.singleShot(500, self._siguiente)
            return
        self._esperando = (self._n, archivo, listo, urgente)
        # Recién abierto tarda más (Python y Qt cargando; tras encender el equipo, mucho más).
        self._plazo.start(PLAZO_ARRANQUE_MS if arranca else PLAZO_MS)

    @Slot(str)
    def _llega(self, linea):
        try:
            r = json.loads(linea)
        except ValueError:
            return
        if self._esperando is None or r.get("n") != self._esperando[0]:
            return
        self._plazo.stop()
        _, archivo, listo, urgente = self._esperando
        self._esperando = None
        img = QImage(archivo) if r.get("ok") else QImage()
        try:
            os.remove(archivo)
        except OSError:
            pass
        if not img.isNull():
            try:
                listo(img)
            except Exception:
                pass
        siguiente_urgente = bool(self._cola) and self._cola[0][0]
        QTimer.singleShot(0 if siguiente_urgente else RESPIRO_MS, self._siguiente)

    def _atascado(self):
        """No contestó a tiempo: se cierra y la siguiente petición abre otro."""
        self._esperando = None
        self.cerrar()
        QTimer.singleShot(0, self._siguiente)

    def cerrar(self):
        if self.proc is not None:
            try:
                self.proc.stdin.close()
            except (OSError, ValueError):
                pass
            proc = self.proc
            QTimer.singleShot(3000, lambda: proc.poll() is None and proc.kill())
        self.proc = None


class Menu(QObject):
    """Lo que ve qml/Ajustes.qml como `menu`."""
    datosCambio = Signal()
    previaCambio = Signal()
    miniaturaCambio = Signal(str, str)          # id de la opción, url
    cerrarPedido = Signal()
    pulsado = Signal(object)                    # la opción pulsada (con sus funciones)

    def __init__(self, datos, estudio, carpeta, almacen, fabrica=None):
        """`datos()` da el menú con funciones de Python (barra.pyw, _datos_menu). `estudio`
        hace la vista previa y `fabrica` las miniaturas: en dos procesos, la vista previa
        nunca espera a que acabe una miniatura."""
        super().__init__()
        self._datos_py, self.estudio, self.carpeta, self.almacen = datos, estudio, carpeta, almacen
        self.fabrica = fabrica or estudio
        self._datos, self._acciones, self._probando = {}, {}, None
        self._previa, self._contexto, self._pendientes = "", [], set()
        os.makedirs(carpeta, exist_ok=True)

    # ----- datos para QML -----
    def refrescar(self, contexto):
        """`contexto`: lo que cambia todas las miniaturas (tema, gama, momento...)."""
        self._contexto = contexto
        crudo = self._datos_py()
        self._acciones = {}
        cats = []
        for ci, cat in enumerate(crudo["categorias"]):
            secciones = []
            for si, sec in enumerate(cat["secciones"]):
                ops = []
                for oi, o in enumerate(sec["opciones"]):
                    ident = f"{ci}.{si}.{oi}"
                    self._acciones[ident] = o
                    q = {k: v for k, v in o.items() if k not in ("hacer", "cambios", "recorte", "cambios_miniatura")}
                    q["id"] = ident
                    q["prueba"] = "cambios" in o
                    if sec.get("tipo") == "imagenes" and "cambios" in o and not q.get("imagen") and not o.get("sin_miniatura"):
                        q["imagen"] = self._miniatura(ident, o)
                    ops.append(q)
                secciones.append({**{k: v for k, v in sec.items() if k != "opciones"}, "opciones": ops})
            cats.append({**{k: v for k, v in cat.items() if k != "secciones"}, "secciones": secciones})
        rapidos = []
        for ri, o in enumerate(crudo["rapidos"]):
            ident = f"r.{ri}"
            self._acciones[ident] = o
            rapidos.append({**{k: v for k, v in o.items() if k != "hacer"}, "id": ident})
        self._datos = {**{k: v for k, v in crudo.items() if k not in ("categorias", "rapidos")},
                       "categorias": cats, "rapidos": rapidos}
        self.datosCambio.emit()

    datos = Property("QVariantMap", lambda self: self._datos, notify=datosCambio)
    previa = Property(str, lambda self: self._previa, notify=previaCambio)

    def _miniatura(self, ident, o):
        nombre = clave([o["cambios"], o.get("cambios_miniatura", []), o.get("recorte", "")], self._contexto) + ".png"
        ruta = os.path.join(self.carpeta, nombre)
        if os.path.exists(ruta):
            return QUrl.fromLocalFile(ruta).toString()
        if nombre in self._pendientes:
            return ""
        self._pendientes.add(nombre)

        def listo(img, ruta=ruta, ident=ident, o=o, nombre=nombre):
            self._pendientes.discard(nombre)
            img = self._encuadre(img, o)
            if not img.isNull() and img.save(ruta):
                self.miniaturaCambio.emit(ident, QUrl.fromLocalFile(ruta).toString() + "?" + str(int(time.time())))
        self.fabrica.pedir(o["cambios"] + o.get("cambios_miniatura", []), o.get("recorte", ""), listo, etiqueta=ident)
        return ""

    @staticmethod
    def _encuadre(img, o):
        """Sin recorte: lo dibujado, y de una barra larga, su principio."""
        if o.get("recorte") and not o["recorte"].startswith("~"):
            return img
        if o.get("recorte"):                     # franja: solo quitar lo transparente de arriba y abajo
            r = caja_visible(img)
            return img.copy(QRect(0, r.y(), img.width(), r.height())) if r is not None else img
        r = caja_visible(img)
        if r is None:
            return img
        an = min(r.width(), int(r.height() * 9))
        return img.copy(QRect(r.x(), r.y(), an, r.height()))

    def limpiar(self):
        """Que la carpeta no crezca sin fin: fuera las más viejas."""
        try:
            fs = sorted((os.path.getmtime(os.path.join(self.carpeta, f)), f) for f in os.listdir(self.carpeta))
            for _, f in fs[:-MAX_MINIATURAS]:
                os.remove(os.path.join(self.carpeta, f))
        except OSError:
            pass

    # ----- lo que pide QML -----
    @Slot()
    def cerrar(self):
        self.cerrarPedido.emit()

    @Slot(str)
    def pulsar(self, ident):
        o = self._acciones.get(ident)
        if o and o.get("hacer"):
            self._probando = None
            o["hacer"]()
            self.pulsado.emit(o)

    @Slot(int)
    def categoria(self, ci):
        """Se está mirando esa categoría: sus miniaturas, primero."""
        self.fabrica.antes(f"{ci}.")

    @Slot(str)
    def probar(self, ident):
        """Pasar el ratón o el foco por una opción: la vista previa con ella."""
        o = self._acciones.get(ident)
        if not o or "cambios" not in o or ident == self._probando:
            return
        self._probando = ident
        self.estudio.pedir(o["cambios"], "", self._poner_previa, urgente=True)

    @Slot()
    def dejar(self):
        """Ya no hay opción a prueba: la vista previa con lo que hay."""
        if self._probando is None and self._previa:
            return
        self._probando = None
        self.estudio.pedir([], "", self._poner_previa, urgente=True)

    def _poner_previa(self, img):
        self.almacen.poner("menu_previa", img)             # ya viene recortada del estudio
        self._previa = self.almacen.url("menu_previa")
        self.previaCambio.emit()
