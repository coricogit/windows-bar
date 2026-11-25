"""Barra de tareas con temas para Windows 11.

    pythonw barra.pyw                  reemplaza la barra de Windows
    py barra.pyw --vista CARPETA       guarda una imagen de cada tema, sin tocar nada
    py barra.pyw --segundos 20         se cierra sola (para pruebas)

Solo oculta la barra de Explorer; barra/vigilante.py la devuelve si esto se
cierra o se cuelga. Salida de emergencia: Ctrl+Alt+Mayús+B.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import threading
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from PySide6.QtCore import (Property, QAbstractListModel, QByteArray, QFileInfo, QLockFile, QModelIndex,  # noqa: E402
                            QObject, QPoint, QRect, QSize, Qt, QTimer, QUrl, Signal, Slot)
from PySide6.QtGui import QAction, QActionGroup, QColor, QCursor, QGuiApplication, QIcon, QImage, QPainter  # noqa: E402
from PySide6.QtQuick import QQuickImageProvider, QQuickView, QQuickWindow, QSGRendererInterface  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileIconProvider, QMenu  # noqa: E402

from barra import (ajustes as cfg, bandeja, cielo, claudito, musica, panel_claude, sesiones, sistema, temas,  # noqa: E402
                   vidrio, vista as previa, win)

DATOS = os.path.join(os.environ["LOCALAPPDATA"], "barra-temas")
ALTO = temas.NORMAL
SIN_CONSOLA = 0x08000000
TIENDA = "shell:AppsFolder\\"
ANCLADOS = os.path.join(os.environ["APPDATA"], "Microsoft", "Internet Explorer", "Quick Launch",
                        "User Pinned", "TaskBar")
RUTA_AJUSTES = os.path.join(DATOS, "ajustes.json")


def registrar(que):
    import traceback
    try:
        ruta = os.path.join(DATOS, "barra.log")
        modo = "w" if os.path.exists(ruta) and os.path.getsize(ruta) > 200_000 else "a"
        with open(ruta, modo, encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + que + "\n")
            if sys.exc_info()[0]:
                f.write(traceback.format_exc())
    except OSError:
        pass


class Lista(QAbstractListModel):
    """Lista de diccionarios con clave "key"; solo avisa de lo que cambia."""

    def __init__(self, roles, parent=None):
        super().__init__(parent)
        self._roles = {Qt.ItemDataRole.UserRole + i: r for i, r in enumerate(roles)}
        self.filas = []

    def roleNames(self):
        return {k: QByteArray(v.encode()) for k, v in self._roles.items()}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.filas)

    def data(self, index, role):
        if 0 <= index.row() < len(self.filas):
            return self.filas[index.row()].get(self._roles.get(role))
        return None

    def poner(self, nuevas):
        claves = {f["key"] for f in nuevas}
        for i in range(len(self.filas) - 1, -1, -1):
            if self.filas[i]["key"] not in claves:
                self.beginRemoveRows(QModelIndex(), i, i)
                del self.filas[i]
                self.endRemoveRows()
        for i, f in enumerate(nuevas):
            j = next((j for j in range(i, len(self.filas)) if self.filas[j]["key"] == f["key"]), None)
            if j is None:
                self.beginInsertRows(QModelIndex(), i, i)
                self.filas.insert(i, f)
                self.endInsertRows()
                continue
            if j != i:
                self.beginMoveRows(QModelIndex(), j, j, QModelIndex(), i)
                self.filas.insert(i, self.filas.pop(j))
                self.endMoveRows()
            if self.filas[i] != f:
                self.filas[i] = f
                self.dataChanged.emit(self.index(i), self.index(i))


class Iconos(QQuickImageProvider):
    """Los iconos para QML: image://iconos/<nombre>/<revisión>."""

    def __init__(self, almacen):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.almacen = almacen

    def requestImage(self, ident, size, requested):
        img = self.almacen.get(ident.rsplit("/", 1)[0])
        if img is None or img.isNull():
            img = QImage(32, 32, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
        return img


class Almacen:
    """Guarda cada icono una vez y le da una revisión para refrescar QML."""

    def __init__(self):
        self.imagenes, self.rev, self._crudo = {}, {}, {}

    def get(self, nombre):
        return self.imagenes.get(nombre)

    def url(self, nombre):
        return f"image://iconos/{nombre}/{self.rev.get(nombre, 0)}" if nombre in self.imagenes else ""

    def poner(self, nombre, img):
        self.imagenes[nombre] = img
        self.rev[nombre] = self.rev.get(nombre, 0) + 1

    def poner_pixeles(self, nombre, b64):
        if b64 and self._crudo.get(nombre) != b64:
            self._crudo[nombre] = b64
            n = bandeja.ICON
            self.poner(nombre, QImage(base64.b64decode(b64), n, n, n * 4, QImage.Format.Format_ARGB32).copy())

    def de_archivo(self, ruta):
        nombre = "exe-" + ruta.lower().replace("\\", "_").replace(":", "").replace("/", "_").replace(" ", "_")
        if nombre not in self.imagenes:
            pm = QFileIconProvider().icon(QFileInfo(ruta)).pixmap(QSize(32, 32))
            if pm.isNull():
                return ""
            self.poner(nombre, pm.toImage())
        return nombre

    def de_app(self, ident):
        """El icono de una app de la Tienda, por su identificador."""
        nombre = "app-" + "".join(ch if ch.isalnum() else "_" for ch in ident)
        if nombre not in self.imagenes:
            bmp = win.store_icon(ident)
            img = QImage.fromHBITMAP(bmp) if bmp else QImage()
            if bmp:
                win.gdi32.DeleteObject(bmp)
            if img.isNull():
                return ""
            self.poner(nombre, img)
        return nombre

    def de_fijo(self, f):
        return self.de_app(f["ruta"][len(TIENDA):]) if f["ruta"].startswith(TIENDA) else self.de_archivo(f["exe"])

    def de_ventana(self, hwnd, exe):
        """El icono propio de la ventana, el de la app de la Tienda o el del programa."""
        nombre = f"ventana-{hwnd}"
        if nombre in self.imagenes:
            return nombre
        if win.class_name(hwnd) == "ApplicationFrameWindow" or "\\WindowsApps\\" in exe:
            ident = win.app_id(hwnd)
            bmp = win.store_icon(ident) if ident else None
            if bmp:
                img = QImage.fromHBITMAP(bmp)
                win.gdi32.DeleteObject(bmp)
                if not img.isNull():
                    self.poner(nombre, img)
                    return nombre
        hicon = win.window_hicon(hwnd)
        if hicon:
            self.poner_pixeles(nombre, bandeja.icon_pixels(hicon))
            if nombre in self.imagenes:
                return nombre
        return self.de_archivo(exe) if exe else ""

    def olvidar_ventanas(self, vivas):
        for n in [n for n in self.imagenes if n.startswith("ventana-") and int(n[8:]) not in vivas]:
            self.imagenes.pop(n)
            self._crudo.pop(n, None)


def anclados():
    """[{"clave", "exe", "nombre", "ruta"}] de la barra de Windows."""
    out = []
    try:
        nombres = sorted(os.listdir(ANCLADOS))
    except OSError:
        return out
    for n in nombres:
        if n.lower().endswith(".lnk"):
            ruta = os.path.join(ANCLADOS, n)
            exe = QFileInfo(ruta).symLinkTarget().replace("/", "\\")
            if not exe.lower().endswith(".exe"):       # el Explorador no apunta a ningún archivo
                exe = os.path.join(os.environ["WINDIR"], "explorer.exe")
            out.append({"clave": win.clave_exe(exe), "exe": exe, "nombre": n[:-4], "ruta": ruta})
    return out


# ---------------------------------------------------------------------------

class Barra(QObject):
    """Lo que ve QML como `barra`."""
    temaCambio = Signal()
    datosCambio = Signal()
    claudeCambio = Signal()
    musicaCambio = Signal()
    animarCambio = Signal()
    tituloCambio = Signal()
    ropaCambio = Signal()
    momentoCambio = Signal()
    _musica = Signal(object)
    _bandeja = Signal(object)
    _uso = Signal(object)
    _ventana_claude = Signal(object)

    def __init__(self, app, vista=False):
        super().__init__()
        self.app, self.vista = app, vista
        self.almacen = Almacen()
        self.temas = temas.cargar()
        self.ajustes = cfg.normalizar(cfg.leer(RUTA_AJUSTES), self.temas, temas.FORMATOS)
        self.paneles = []
        self.tray = Lista(["key", "icono", "tip"], self)
        self._tray = {}
        self._camaleon, self._camaleon_imagen = {}, None
        self._elegido = None
        self._datos = {"cpu": 0, "ram": 0, "gpu": -1, "volumen": 0, "silencio": False}
        self._claude = {"modo": "sleep", "texto": ""}
        self._ropa = {"gorro": "", "traje": ""}
        self._cancion = dict(musica.NADA)
        self._animar = True
        self._titulo = ""
        self._momento = self._que_momento()
        self._historia = {"cpu": [], "ram": [], "gpu": []}
        self._plena = {}
        self.cpu, self.gpu, self.vol = sistema.Cpu(), sistema.Gpu(), sistema.Volume()
        self.claudito = claudito.Claudito()
        self.de_windows = anclados()
        self.fijos = cfg.lista_fijos(self.ajustes, self.de_windows)
        self.previa = None
        self.panel_claude = None
        self._uso_datos, self._uso_hora, self._uso_hilo = None, 0, None
        self._uso.connect(self._set_uso)
        self._ventana_claude.connect(lambda h: win.activate(h))
        self._sitio_claude = None
        self._t_claude = QTimer(self, singleShot=True, interval=350, timeout=self._mostrar_claude)
        self._centrado = temas.windows_centrado()
        self.fondo = vidrio.fondo = vidrio.Fondo()
        self.temaCambio.connect(self._zonas_vidrio)
        self.animarCambio.connect(self._zonas_vidrio)
        self._apuntado = None
        self._t_previa = QTimer(self, singleShot=True, interval=380, timeout=self._mostrar_previa)
        self._musica.connect(self._set_musica)
        self._bandeja.connect(self._set_bandeja)
        self.musica = None
        self._aplicar_tema(self._tema_que_toca())

    def arrancar(self):
        self.musica = musica.Musica(self._musica.emit)
        self._t_sis = QTimer(self, interval=2000, timeout=self._sistema)
        self._t_cl = QTimer(self, interval=500, timeout=self._leer_claude)
        self._t_ropa = QTimer(self, interval=5000, timeout=self._leer_ropa)
        self._t_ropa.start()
        self._leer_ropa()
        self._t_tema = QTimer(self, interval=10000, timeout=self._revisar_tema)
        self._t_ven = QTimer(self, interval=1000, timeout=self.actualizar_ventanas)
        self._t_pronto = QTimer(self, interval=60, singleShot=True, timeout=self.actualizar_ventanas)
        for t in (self._t_sis, self._t_cl, self._t_tema, self._t_ven):
            t.start()
        self._gancho = win.watch(self._t_pronto.start)
        self._sistema()
        self._leer_claude()
        self.actualizar_ventanas()

    # ----- ajustes y temas -----
    def _guardar(self):
        if not self.vista:
            cfg.guardar(RUTA_AJUSTES, self.ajustes)

    def _tema_que_toca(self):
        a = self.ajustes
        exe = os.path.basename(win.exe_of(win.pid_of(win.user32.GetForegroundWindow()))).lower()
        tema = a["por_programa"].get(exe) if isinstance(a["por_programa"], dict) else None
        if not tema and a["auto"]:
            tema = a["tema_dia"] if a["dia"] <= time.localtime().tm_hour < a["noche"] else a["tema_noche"]
        tema = tema or a["tema"]
        return tema if tema in self.temas else next(iter(self.temas))

    @staticmethod
    def _que_momento():
        h = time.localtime()
        return cielo.momento(h.tm_hour + h.tm_min / 60, h.tm_mon)

    def _poner_momento(self, m):
        if m != self._momento:
            self._momento = m
            self.momentoCambio.emit()
            self.temaCambio.emit()

    # "noche", "amanecer", "dia" o "atardecer"
    momento = Property(str, lambda self: self._momento, notify=momentoCambio)

    def _revisar_tema(self):
        self._poner_momento(self._que_momento())
        toca = self._tema_que_toca()
        if toca != self._elegido:
            self._aplicar_tema(toca)
        elif self.temas[toca]["dinamico"]:
            self._actualizar_camaleon()

    def _aplicar_tema(self, ident):
        self._elegido = ident
        if self.temas[ident]["dinamico"]:
            self._actualizar_camaleon(avisar=False)
        self.temaCambio.emit()

    def _actualizar_camaleon(self, avisar=True):
        ruta = temas.imagen_fondo(any("wallpaper" in os.path.basename(v["exe"]).lower()
                                      for v in self._tray.values()) or self.vista)
        marca = (ruta, os.path.getmtime(ruta) if ruta else 0)
        if marca == self._camaleon_imagen:
            return
        self._camaleon_imagen = marca
        img = QImage(ruta).scaled(40, 40) if ruta else QImage()
        pix = [QColor(img.pixel(x, y)).getRgb()[:3] for x in range(img.width()) for y in range(img.height())]
        self._camaleon = temas.paleta(pix)
        if avisar:
            self.temaCambio.emit()

    def _get_tema(self):
        t = self.temas[self._elegido]
        if t["dinamico"]:
            t = {**t, "colores": {**t["colores"], **self._camaleon}}
        t = temas.con_momento(t, self._momento)
        t = temas.con_formato(t, self.ajustes["formatos"].get(self._elegido, "tema"))
        al = self.ajustes["alineacion"]
        return temas.con_alineacion(t, self._centrado if al == "windows" else al == "centro")

    def _zonas_vidrio(self):
        """Qué trozos del fondo hacen falta: los de las barras a la vista."""
        if self.vista:
            return
        t = self._get_tema()
        activo = bool(t["vidrio"] or t["adapta"]) and self._animar
        zonas = [p.zona_real() for p in self.paneles] if activo else []
        self.fondo.poner(zonas, self.ajustes["vidrio"], activo and bool(zonas))

    def _set_vidrio(self, nivel):
        self.ajustes["vidrio"] = nivel
        self._guardar()
        self._zonas_vidrio()

    def _set_alineacion(self, a):
        self.ajustes["alineacion"] = a
        self._guardar()
        self.temaCambio.emit()

    tema = Property("QVariantMap", _get_tema, notify=temaCambio)

    @Slot(str)
    def elegir(self, ident):
        self.ajustes.update(tema=ident, auto=False)
        self._guardar()
        self._aplicar_tema(self._tema_que_toca())

    def alto(self):
        return temas.alto_total(self._get_tema())

    def _set_formato(self, f):
        self.ajustes["formatos"][self._elegido] = f
        self._guardar()
        self.temaCambio.emit()

    def _formato_para_todos(self):
        f = self.ajustes["formatos"].get(self._elegido, "tema")
        self.ajustes["formatos"] = {t: f for t in self.temas}
        self._guardar()

    pincel = Property(bool, lambda self: self.ajustes["pincel"], notify=temaCambio)

    def _set_pincel(self, si):
        self.ajustes["pincel"] = si
        self._guardar()
        self.temaCambio.emit()

    @Slot(int)
    def girar_tema(self, paso):
        ids = list(self.temas)
        self.elegir(ids[(ids.index(self._elegido) + paso) % len(ids)])

    # ----- sistema, música, Claudito -----
    def _sistema(self):
        if not self._animar:          # modo juego
            return
        v = self.vol.read()
        g = self.gpu.percent()
        uso = {"cpu": self.cpu.percent(), "ram": sistema.ram_percent(), "gpu": -1 if g is None else g}
        for k, n in uso.items():
            self._historia[k] = (self._historia[k] + [n])[-24:]
        self._set_datos({**uso, "historia": dict(self._historia),
                         "volumen": v[0] if v else 0, "silencio": v[1] if v else True})

    def _set_datos(self, d):
        if d != self._datos:
            self._datos = d
            self.datosCambio.emit()

    datos = Property("QVariantMap", lambda self: self._datos, notify=datosCambio)

    def _set_musica(self, d):
        self._cancion = d
        self.musicaCambio.emit()

    cancion = Property("QVariantMap", lambda self: self._cancion, notify=musicaCambio)

    def _leer_claude(self):
        if self.claudito.disponible and self._animar:
            d = self.claudito.leer()
            if self.panel_claude and self.panel_claude.isVisible():
                self.panel_claude.poner(self.claudito.sesiones, self._uso_datos)
            if d and d != self._claude:
                self._claude = d
                self.claudeCambio.emit()

    def _leer_ropa(self):
        r = self.claudito.ropa()
        if r != self._ropa:
            self._ropa = r
            self.ropaCambio.emit()

    ropa = Property("QVariantMap", lambda self: self._ropa, notify=ropaCambio)
    claude = Property("QVariantMap", lambda self: self._claude, notify=claudeCambio)
    personaje = Property(str, lambda self: QUrl.fromLocalFile(claudito.PERSONAJE).toString()
                         if self.claudito.disponible else "", constant=True)
    mes = Property(int, lambda self: time.localtime().tm_mon, notify=momentoCambio)
    # Falso en modo juego: nada se anima ni se consulta.
    animar = Property(bool, lambda self: self._animar, notify=animarCambio)

    # ----- Claudito interactivo -----
    @Slot(float, float)
    def claude_entrar(self, x, y):
        self._quitar_previa()
        self._sitio_claude = (x, y)
        self._t_claude.start()

    @Slot()
    def claude_salir(self):
        self._sitio_claude = None
        self._t_claude.stop()
        if self.panel_claude:
            self.panel_claude.pronto()

    def _mostrar_claude(self):
        if not self._sitio_claude:
            return
        x, y = self._sitio_claude
        if not self.panel_claude:
            self.panel_claude = panel_claude.Panel(self.ir_a_claude)
        pantalla = QGuiApplication.screenAt(QPoint(round(x), round(y))) or self.app.primaryScreen()
        g = pantalla.geometry()
        self.panel_claude.mostrar(self.claudito.sesiones, self._uso_datos, x, g.y() + g.height() - self.alto(), g,
                                  self._get_tema())
        self._pedir_uso()

    def _pedir_uso(self):
        if time.monotonic() - self._uso_hora < 30 and self._uso_datos or self._uso_hilo and self._uso_hilo.is_alive():
            return
        self._uso_hilo = threading.Thread(target=self._calcular_uso, daemon=True)
        self._uso_hilo.start()

    def _calcular_uso(self):
        try:
            r = subprocess.run([sys.executable.replace("pythonw.exe", "python.exe"),
                                os.path.join(AQUI, "barra", "uso.py")], capture_output=True, text=True, timeout=60,
                               creationflags=SIN_CONSOLA)
            self._uso.emit(json.loads(r.stdout))
        except (OSError, ValueError, subprocess.TimeoutExpired, RuntimeError):
            pass                      # se queda el último dato

    def _set_uso(self, d):
        self._uso_datos, self._uso_hora = d, time.monotonic()
        if self.panel_claude and self.panel_claude.isVisible():
            self.panel_claude.poner(self.claudito.sesiones, d)

    @Slot()
    @Slot(str)
    def ir_a_claude(self, sesion=""):
        """Trae al frente la ventana de esa sesión, o de la que te necesita."""
        if self.panel_claude:
            self.panel_claude.hide()
        lista = self.claudito.sesiones
        sesion = sesion or self.claudito.actual or (lista[0]["id"] if lista else "")

        def buscar():
            pid = sesiones.pid_de(sesion) if sesion else None
            h = sesiones.ventana_de(pid) if pid else None
            if h:
                self._ventana_claude.emit(h)
        threading.Thread(target=buscar, daemon=True).start()

    titulo = Property(str, lambda self: self._titulo, notify=tituloCambio)

    # ----- ventanas -----
    def actualizar_ventanas(self):
        try:
            self._actualizar_ventanas()
        except Exception:
            registrar("ventanas")

    def _actualizar_ventanas(self):
        centrado = temas.windows_centrado()
        if centrado != self._centrado:
            self._centrado = centrado
            self.temaCambio.emit()
        activa = win.user32.GetForegroundWindow()
        hwnds = win.windows()
        self.almacen.olvidar_ventanas(set(hwnds))
        info = []
        for h in sorted(hwnds):            # orden estable, no el de uso
            exe = win.app_exe(h)
            info.append({"hwnd": h, "exe": exe, "titulo": win.title(h), "activa": h == activa,
                         "minimizada": bool(win.user32.IsIconic(h)), "pantalla": win.monitor_of(h),
                         "icono": self.almacen.url(self.almacen.de_ventana(h, exe))})
        titulo = next((i["titulo"] for i in info if i["activa"]), "")
        if titulo != self._titulo:
            self._titulo = titulo
            self.tituloCambio.emit()
        for p in self.paneles:
            p.poner_ventanas(info, self.fijos)
        if self.previa and self.previa.hwnd and self.previa.hwnd not in hwnds:
            self.previa.ocultar()
        if self.ajustes["modo_juego"] and not self.vista:
            self._modo_juego(activa)

    def _modo_juego(self, activa):
        """Oculta la barra en las pantallas con algo a pantalla completa."""
        if win.is_fullscreen(activa):
            self._plena[win.monitor_of(activa)] = activa
        elif activa and win.class_name(activa) not in win.SHELL_CLASSES:
            self._plena.pop(win.monitor_of(activa), None)
        for mon, h in list(self._plena.items()):
            if not win.is_fullscreen(h) or win.monitor_of(h) != mon:
                del self._plena[mon]
        for p in self.paneles:
            p.mostrar(p.pantalla_real() not in self._plena)
        if self._plena:
            self._quitar_previa()
            self.claude_salir()
        animar = not self._plena
        if animar != self._animar:
            self._animar = animar
            if self.musica:
                self.musica.pausada = not animar
            self.animarCambio.emit()

    def _fila(self, clave):
        for p in self.paneles:
            for f in p.tareas.filas:
                if f["key"] == clave:
                    return f
        return None

    @Slot(str, bool)
    def pulsar_tarea(self, clave, nueva):
        self._quitar_previa()
        f = self._fila(clave)
        if not f:
            return
        if f["hwnd"] and not nueva:
            h = int(f["hwnd"])
            if f["activa"]:
                win.minimize(h)
            else:
                win.activate(h)
        else:
            self._abrir(f)

    def _entrada(self, f):
        """Lo necesario para anclar o volver a abrir el programa de una fila."""
        ruta = f["ruta"]
        if not ruta and f["hwnd"] and win.de_la_tienda(int(f["hwnd"]), f["exe"]):
            ident = win.app_id(int(f["hwnd"]))
            ruta = TIENDA + ident if "!" in ident else ""
        nombre = os.path.splitext(os.path.basename(f["exe"]))[0]
        return {"clave": win.clave_exe(f["exe"]), "exe": f["exe"], "nombre": nombre, "ruta": ruta}

    def _abrir(self, f):
        e = self._entrada(f)
        try:
            os.startfile(e["ruta"] or e["exe"])
        except OSError:
            registrar("abrir " + str(e["exe"]))

    # ----- menú de una ventana -----
    @Slot(str)
    def menu_tarea(self, clave):
        self._quitar_previa()
        QTimer.singleShot(0, lambda: self._menu_tarea(clave))

    def _menu_tarea(self, clave):
        f = self._fila(clave)
        if f:
            self._abrir_menu(self._crear_menu_tarea(f))

    def _crear_menu_tarea(self, f):
        m = self._nuevo_menu()
        e = self._entrada(f)
        nombre = QAction(e["nombre"], m)
        nombre.setEnabled(False)
        m.addAction(nombre)
        m.addSeparator()
        m.addAction("Abrir otra ventana" if f["hwnd"] else "Abrir", lambda: self._abrir(f))
        if any(x["clave"] == e["clave"] for x in self.fijos):
            m.addAction("Desanclar de esta barra", lambda: self._anclar(e, False))
        elif e["exe"]:
            m.addAction("Anclar a esta barra", lambda: self._anclar(e, True))
        if f["hwnd"]:
            h = int(f["hwnd"])
            m.addSeparator()
            if win.user32.IsIconic(h) or win.user32.IsZoomed(h):
                m.addAction("Restaurar", lambda: win.restore(h))
            if not win.user32.IsIconic(h):
                m.addAction("Minimizar", lambda: win.minimize(h))
            if not win.user32.IsZoomed(h):
                m.addAction("Maximizar", lambda: win.maximize(h))
            m.addSeparator()
            m.addAction("Cerrar ventana", lambda: win.close(h))
            todas = [i for i in win.windows() if win.clave_exe(win.app_exe(i)) == e["clave"]]
            if len(todas) > 1:
                m.addAction(f"Cerrar las {len(todas)} ventanas", lambda: [win.close(i) for i in todas])
        return m

    def _anclar(self, e, si):
        claves = [x["clave"] for x in self.de_windows]
        if si:
            cfg.fijar(self.ajustes, e, claves)
        else:
            cfg.soltar(self.ajustes, e["clave"], claves)
        self._guardar()
        self.fijos = cfg.lista_fijos(self.ajustes, self.de_windows)
        self.actualizar_ventanas()

    # ----- vista previa -----
    @Slot(str, float, float)
    def apuntar(self, clave, x, y):
        """El ratón entró en un botón; (x, y) es su borde de arriba, global."""
        self._apuntado = (clave, x, y)
        self._t_previa.start(80 if self.previa and self.previa.isVisible() else 380)

    @Slot(str)
    def soltar(self, clave):
        if self._apuntado and self._apuntado[0] == clave:
            self._apuntado = None
            self._t_previa.stop()
            if self.previa:
                self.previa.pronto()

    def _mostrar_previa(self):
        if not self._apuntado:
            return
        clave, x, y = self._apuntado
        f = self._fila(clave)
        if not f or not f["hwnd"] or not win.user32.IsWindow(int(f["hwnd"])):
            if self.previa:
                self.previa.ocultar()
            return
        if not self.previa:
            self.previa = previa.Vista(win.activate, win.close)
        pantalla = QGuiApplication.screenAt(QPoint(round(x), round(y))) or self.app.primaryScreen()
        g = pantalla.geometry()
        self.previa.mostrar(int(f["hwnd"]), f["titulo"], x, g.y() + g.height() - self.alto(), g, self._get_tema())

    def _quitar_previa(self):
        self._apuntado = None
        self._t_previa.stop()
        if self.previa:
            self.previa.ocultar()

    # ----- bandeja -----
    def _set_bandeja(self, m):
        if m["op"] == "quitar":
            self._tray.pop(m["key"], None)
        else:
            nombre = "tray-" + m["key"]
            self.almacen.poner_pixeles(nombre, m.pop("pixels"))
            self._tray[m["key"]] = {**m, "icono": self.almacen.url(nombre)}
        self.tray.poner([{"key": k, "icono": v["icono"],
                          "tip": v["tip"] or os.path.splitext(os.path.basename(v["exe"]))[0]}
                         for k, v in self._tray.items() if not v["hidden"] and v["icono"]])

    @Slot(str, bool)
    def pulsar_bandeja(self, clave, derecho):
        if clave in self._tray:
            win.tray_click(self._tray[clave], derecho)

    # ----- botones -----
    @Slot(str)
    def accion(self, que):
        teclas = {"inicio": (0x5B,), "buscar": (0x5B, 0x53), "rapidos": (0x5B, 0x41), "avisos": (0x5B, 0x4E),
                  "menu_inicio": (0x5B, 0x58), "silencio": (0xAD,), "menos": (0xAE,), "mas": (0xAF,)}
        if que in teclas:
            win.press(*teclas[que])
            if que in ("silencio", "menos", "mas"):
                QTimer.singleShot(120, self._sistema)
        elif self.musica:
            self.musica.orden(que)

    @Slot()
    def menu(self):
        self._quitar_previa()
        QTimer.singleShot(0, lambda: self._abrir_menu(self._crear_menu()))

    def _nuevo_menu(self):
        m = QMenu()
        c = self._get_tema()["colores"]
        opaco = QColor(c["fondo"])
        opaco.setAlpha(255)
        m.setStyleSheet(f"QMenu{{background:{opaco.name()};color:{QColor(c['texto']).name()};padding:6px;"
                        f"border:1px solid {QColor(c['acento']).name()};}}"
                        f"QMenu::item{{padding:6px 26px 6px 22px;}}"
                        f"QMenu::item:selected{{background:{QColor(c['acento']).name()};color:{opaco.name()};}}"
                        f"QMenu::separator{{height:1px;background:{QColor(c['tenue']).name()};margin:5px 8px;}}"
                        f"QMenu::item:disabled{{color:{QColor(c['tenue']).name()};}}")
        return m

    def _submenu(self, m, titulo, opciones, actual, poner):
        sub = m.addMenu(titulo)
        sub.setStyleSheet(m.styleSheet())
        grupo = QActionGroup(sub)
        for k, nombre in opciones.items():
            a = QAction(nombre, sub, checkable=True, checked=k == actual)
            a.triggered.connect(lambda _=False, k=k: poner(k))
            grupo.addAction(a)
            sub.addAction(a)
        return sub

    def _crear_menu(self):
        m = self._nuevo_menu()
        grupo = QActionGroup(m)
        for ident, t in self.temas.items():
            a = QAction(t["nombre"], m, checkable=True, checked=ident == self._elegido)
            a.triggered.connect(lambda _=False, i=ident: self.elegir(i))
            grupo.addAction(a)
            m.addAction(a)
        m.addSeparator()
        sub = self._submenu(m, "Formato de " + self.temas[self._elegido]["nombre"], temas.FORMATOS,
                            self.ajustes["formatos"].get(self._elegido, "tema"), self._set_formato)
        sub.addSeparator()
        sub.addAction("Usar este en todos los temas", self._formato_para_todos)
        self._submenu(m, "Posición de los iconos", temas.ALINEACIONES, self.ajustes["alineacion"], self._set_alineacion)
        if self._get_tema()["vidrio"]:
            self._submenu(m, "Transparencia del vidrio", vidrio.NOMBRES, self.ajustes["vidrio"], self._set_vidrio)
        auto = QAction("Cambiar según la hora", m, checkable=True, checked=bool(self.ajustes["auto"]))
        auto.triggered.connect(self._set_auto)
        m.addAction(auto)
        juego = QAction("Modo juego (ocultar a pantalla completa)", m, checkable=True,
                        checked=bool(self.ajustes["modo_juego"]))
        juego.triggered.connect(self._set_juego)
        m.addAction(juego)
        pincel = QAction("Mostrar el pincel", m, checkable=True, checked=self.ajustes["pincel"])
        pincel.triggered.connect(self._set_pincel)
        m.addAction(pincel)
        m.addSeparator()
        m.addAction("Administrador de tareas", lambda: win.press(0x11, 0x10, 0x1B))
        m.addAction("Configuración de Windows", lambda: win.press(0x5B, 0x49))
        m.addSeparator()
        m.addAction("Salir y volver a la barra de Windows", self.app.quit)
        return m

    def _abrir_menu(self, m):
        QTimer.singleShot(0, lambda: win.user32.SetForegroundWindow(int(m.winId())))
        pos = QCursor.pos()
        alto = m.sizeHint().height()
        pantalla = QGuiApplication.screenAt(pos)
        if pantalla:
            pos.setY(pantalla.geometry().bottom() - self.alto() - alto)
        m.exec(pos)

    def _set_auto(self, si):
        self.ajustes["auto"] = si
        self._guardar()
        self._aplicar_tema(self._tema_que_toca())

    def _set_juego(self, si):
        self.ajustes["modo_juego"] = si
        self._guardar()
        if not si:
            self._plena.clear()
            for p in self.paneles:
                p.mostrar(True)
            self._animar = True
            self.animarCambio.emit()


class Panel:
    """La barra de una pantalla."""

    def __init__(self, barra, pantalla, primaria):
        self.barra, self.pantalla, self.primaria = barra, pantalla, primaria
        self.tareas = Lista(["key", "titulo", "icono", "activa", "minimizada", "abierta", "hwnd", "exe", "ruta"])
        v = self.view = QQuickView()
        v.setFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
                   | Qt.WindowType.WindowDoesNotAcceptFocus | Qt.WindowType.NoDropShadowWindowHint)
        v.setColor(QColor(Qt.GlobalColor.transparent))
        v.setTitle("Barra de temas")
        v.engine().addImageProvider("iconos", Iconos(barra.almacen))
        ctx = v.rootContext()
        for nombre, valor in (("barra", barra), ("tareas", self.tareas), ("bandeja", barra.tray)):
            ctx.setContextProperty(nombre, valor)
        ctx.setContextProperty("esPrimaria", primaria)
        v.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        if pantalla:
            v.setScreen(pantalla)
            self.colocar()
            pantalla.geometryChanged.connect(lambda *_: self.colocar())
            barra.temaCambio.connect(self.colocar)
        v.setSource(QUrl.fromLocalFile(os.path.join(AQUI, "qml", "Barra.qml")))

    def colocar(self):
        g = self.pantalla.geometry()
        alto = self.barra.alto()
        self.view.setGeometry(QRect(g.x(), g.y() + g.height() - alto, g.width(), alto))

    def pantalla_real(self):
        return win.monitor_of(int(self.view.winId()))

    def zona_real(self):
        """(x, y, ancho, alto) en píxeles, como los da Qt."""
        g = self.pantalla.geometry()
        return g.x(), g.y() + g.height() - ALTO, g.width(), ALTO

    def mostrar(self, si):
        if self.view.isVisible() != si:
            self.view.setVisible(si)
        elif si:          # otra ventana "siempre encima" pudo taparla
            win.user32.SetWindowPos(win.w.HWND(int(self.view.winId())), win.w.HWND(-1), 0, 0, 0, 0, 0x13)

    def poner_ventanas(self, info, fijos):
        if not self.primaria and self.pantalla:
            mia = self.pantalla_real()
            info = [i for i in info if i["pantalla"] == mia]
            fijos = []
        filas, usadas = [], set()

        def fila(i):
            return {"key": str(i["hwnd"]), "titulo": i["titulo"], "icono": i["icono"], "activa": i["activa"],
                    "minimizada": i["minimizada"], "abierta": True, "hwnd": str(i["hwnd"]), "exe": i["exe"],
                    "ruta": ""}

        for x in fijos:
            suyas = [i for i in info if win.clave_exe(i["exe"]) == x["clave"]]
            usadas.update(i["hwnd"] for i in suyas)
            if suyas:
                filas.extend(fila(i) for i in suyas)
            else:
                filas.append({"key": "fijo-" + x["clave"], "titulo": x["nombre"], "activa": False,
                              "minimizada": False, "icono": self.barra.almacen.url(self.barra.almacen.de_fijo(x)),
                              "abierta": False, "hwnd": "", "exe": x["exe"], "ruta": x["ruta"]})
        filas.extend(fila(i) for i in info if i["hwnd"] not in usadas)
        self.tareas.poner(filas)


# ---------------------------------------------------------------------------

def lanzar(*args):
    return subprocess.Popen([sys.executable.replace("pythonw.exe", "python.exe"), *args], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                            creationflags=SIN_CONSOLA)


class Reemplazo(QObject):
    """Oculta la barra de Windows mientras el vigilante esté vivo."""

    def __init__(self, barra):
        super().__init__(barra)
        self.barra = barra
        self.activo = True
        self.vigilante = self.tray = None
        self._fallos = 0
        self._timer = QTimer(self, interval=1000, timeout=self.latido)

    def empezar(self):
        self._vigilar()
        self._bandeja()
        self._timer.start()
        self.barra.temaCambio.connect(self.ajustar)
        self.latido()

    def _vigilar(self):
        self.vigilante = lanzar(os.path.join(AQUI, "barra", "vigilante.py"), str(os.getpid()))
        linea = self.vigilante.stdout.readline()
        if '"atajo": true' not in linea:
            registrar("vigilante sin atajo: " + repr(linea))

    def _bandeja(self):
        self.tray = lanzar(os.path.join(AQUI, "barra", "bandeja.py"))

        def leer(proc):
            for linea in proc.stdout:
                try:
                    self.barra._bandeja.emit(json.loads(linea))
                except (ValueError, RuntimeError):
                    pass
        threading.Thread(target=leer, args=(self.tray,), daemon=True).start()

    def latido(self):
        if not self.activo:
            return
        if self.vigilante.poll() is not None:
            self._fallos += 1
            if self._fallos > 2:            # sin vigilante no se oculta nada
                registrar("el vigilante no aguanta: se cierra la barra")
                self.barra.app.quit()
                return
            self._vigilar()
        try:
            self.vigilante.stdin.write("latido\n")
            self.vigilante.stdin.flush()
        except OSError:
            return
        if self.tray.poll() is not None and self._fallos <= 2:
            self._fallos += 1
            self._bandeja()
        win.hide_taskbars()
        self.ajustar()

    def ajustar(self):
        """En compacto, las ventanas maximizadas ganan el espacio que sobra."""
        if self.activo:
            alto = self.barra.alto()
            win.ajustar_area(alto if alto != ALTO else None)

    def parar(self):
        self.activo = False
        self._timer.stop()
        for p in (self.tray, self.vigilante):
            try:
                p.stdin.close()
                p.wait(3)
            except (OSError, subprocess.TimeoutExpired, AttributeError):
                pass
        win.show_taskbars()


def hacer_vista(app, carpeta):
    """Una imagen por tema con datos de ejemplo, fuera de la pantalla."""
    os.makedirs(carpeta, exist_ok=True)
    barra = Barra(app, vista=True)
    barra._datos = {"cpu": 23, "ram": 58, "gpu": 41, "volumen": 64, "silencio": False,
                    "historia": {"cpu": [12, 18, 35, 22, 60, 41, 30, 23], "ram": [55, 56, 58, 57, 58],
                                 "gpu": [10, 80, 72, 35, 41]}}
    barra._cancion = {"titulo": "Canción de ejemplo", "artista": "Artista", "sonando": True}
    barra._titulo = "Documento sin título - Bloc de notas"
    barra._leer_ropa()
    barra._claude = {"modo": "idle", "texto": "Construyendo…"}
    exes = [os.path.join(os.environ["WINDIR"], n) for n in ("explorer.exe", "notepad.exe", "regedit.exe")]
    g = app.primaryScreen().geometry()
    barra.fondo.zonas = [(g.x(), g.y() + g.height() - ALTO, g.width(), ALTO)]
    barra.fondo.leer()
    panel = Panel(barra, None, True)
    panel.tareas.poner([{"key": str(i), "titulo": os.path.basename(e), "activa": i == 1, "minimizada": False,
                         "icono": barra.almacen.url(barra.almacen.de_archivo(e)), "abierta": i != 2, "hwnd": "",
                         "exe": e, "ruta": ""} for i, e in enumerate(exes)])
    barra.tray.poner([{"key": e, "icono": barra.almacen.url(barra.almacen.de_archivo(e)), "tip": e} for e in exes])
    panel.view.setGeometry(-6000, -6000, 1920, ALTO)
    panel.view.show()
    for e in panel.view.errors():
        print("QML:", e.toString())
    casos = [(t, f, a, m) for t in barra.temas for f in ("tema", "islas_compactas") for a in ("izquierda", "centro")
             for m in (cielo.MOMENTOS if barra.temas[t]["momentos"] and (f, a) == ("tema", "centro") else ("dia",))]

    def siguiente(i):
        if i:
            img = panel.view.grabWindow()
            fondo = QImage(img.width(), ALTO + 24, QImage.Format.Format_RGB32)
            fondo.fill(QColor("#4A6B8A"))
            p = QPainter(fondo)
            _, f = barra.fondo.franja(g.x() + 1, g.y() + g.height() - 2)
            if f:
                p.drawImage(QPoint(0, 24 + ALTO - f["nitida"].height()), f["nitida"])
            p.drawImage(QPoint(0, 24), img)
            p.end()
            fondo.save(os.path.join(carpeta, "-".join(casos[i - 1]) + ".png"))
        if i == len(casos):
            app.quit()
            return
        barra.ajustes["formatos"] = {casos[i][0]: casos[i][1]}
        barra.ajustes["alineacion"] = casos[i][2]
        barra._poner_momento(casos[i][3])
        barra._aplicar_tema(casos[i][0])
        QTimer.singleShot(900, lambda: siguiente(i + 1))

    siguiente(0)
    app.exec()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vista")
    ap.add_argument("--segundos", type=int)
    args = ap.parse_args()
    os.makedirs(DATOS, exist_ok=True)
    # Dibuja con el procesador: son 48 px de alto y así no le quita nada a los juegos.
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)
    QQuickStyle.setStyle("Basic")
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    vidrio.registrar_tipo()
    if args.vista:
        hacer_vista(app, args.vista)
        return 0
    candado = QLockFile(os.path.join(DATOS, "barra.lock"))
    if not candado.tryLock(100):
        return 1
    with open(os.path.join(DATOS, "pid.json"), "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid()}, f)
    barra = Barra(app)
    for s in app.screens():
        barra.paneles.append(Panel(barra, s, s == app.primaryScreen()))
    errores = [e.toString() for p in barra.paneles for e in p.view.errors()]
    if errores:                       # no ocultar la de Windows si la nuestra no se ve
        registrar("\n".join(errores))
        print("\n".join(errores))
        return 2

    def pantallas(*_):
        for p in barra.paneles:
            barra.temaCambio.disconnect(p.colocar)
            p.view.close()
        barra.paneles[:] = [Panel(barra, s, s == app.primaryScreen()) for s in app.screens()]
        barra._zonas_vidrio()
        for p in barra.paneles:
            p.view.show()

    app.screenAdded.connect(lambda *_: QTimer.singleShot(800, pantallas))
    app.screenRemoved.connect(lambda *_: QTimer.singleShot(800, pantallas))
    for p in barra.paneles:
        p.view.show()
    reemplazo = Reemplazo(barra)
    app.aboutToQuit.connect(reemplazo.parar)
    barra.arrancar()
    barra._zonas_vidrio()
    reemplazo.empezar()
    if args.segundos:
        QTimer.singleShot(args.segundos * 1000, app.quit)
    try:
        return app.exec()
    finally:
        reemplazo.parar()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        registrar("la barra se cerró")
        raise
