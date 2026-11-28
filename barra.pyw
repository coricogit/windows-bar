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

from PySide6.QtCore import (Property, QAbstractListModel, QByteArray, QEvent, QFileInfo, QLockFile, QModelIndex,  # noqa: E402
                            QObject, QPoint, QRect, QSize, Qt, QTimer, QUrl, Signal, Slot)
from PySide6.QtGui import QAction, QColor, QCursor, QGuiApplication, QIcon, QImage, QPainter  # noqa: E402
from PySide6.QtQml import QQmlComponent, QQmlContext, QQmlEngine  # noqa: E402
from PySide6.QtQuick import QQuickImageProvider, QQuickView, QQuickWindow, QSGRendererInterface  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileIconProvider, QInputDialog, QMenu, QMessageBox, QWidget  # noqa: E402

from barra import (reposo, actualizar, ajustes as cfg, apps as apps_inicio, arranque, audio, atencion, buscador, encaje, bandeja, calendario, cielo, claudito, conectar, iconos, isla, musica, panel_claude, paneles, programas, red, saltos, selector, sesiones, sistema, sitio, temas, tiempo,  # noqa: E402
                   vidrio, vista as previa, win)

DATOS = os.path.join(os.environ["LOCALAPPDATA"], "barra-temas")
ALTO = temas.NORMAL
SIN_CONSOLA = 0x08000000
INACTIVO = 90      # segundos sin teclado ni ratón
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


_vistos = {}


def anotar_errores():
    """Con pythonw no hay consola: los errores de Python van a barra.log (cada uno, como mucho una vez
    por minuto) y, si el proceso cae de golpe, faulthandler deja dónde estaba en barra-fallo.log."""
    import faulthandler
    import traceback

    def anotar(tipo, valor, tb, donde=""):
        texto = "".join(traceback.format_exception(tipo, valor, tb))
        ahora = time.monotonic()
        if ahora - _vistos.get(texto, -1e9) < 60:
            return
        if len(_vistos) > 100:
            _vistos.clear()
        _vistos[texto] = ahora
        try:
            with open(os.path.join(DATOS, "barra.log"), "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + "error" + donde + "\n" + texto)
        except OSError:
            pass

    sys.excepthook = anotar
    threading.excepthook = lambda a: anotar(a.exc_type, a.exc_value, a.exc_traceback, f" en el hilo {a.thread.name if a.thread else '?'}")
    try:
        anotar_errores.fallo = open(os.path.join(DATOS, "barra-fallo.log"), "w", encoding="utf-8")
        faulthandler.enable(anotar_errores.fallo, all_threads=True)
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

    @Slot(int, int)
    def mover(self, de, a):
        """Cambia una fila de sitio (arrastrando)."""
        n = len(self.filas)
        if de == a or not (0 <= de < n and 0 <= a < n):
            return
        self.beginMoveRows(QModelIndex(), de, de, QModelIndex(), a + 1 if a > de else a)
        self.filas.insert(a, self.filas.pop(de))
        self.endMoveRows()

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
        self._hechos = {}            # (icono, lado): reducidos y adaptados al tema

    def requestImage(self, ident, size, requested):
        nombre, _, rev = ident.rpartition("/")
        img = self.almacen.get(nombre)
        if img is None or img.isNull():
            img = QImage(32, 32, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            return img
        _, _, estilo = rev.partition("~")
        # Se guardan a 64 px: se reducen al tamaño al que se dibujan, con buen filtro
        # (el pixel art hace su propia reducción) y, ya pequeños, se adaptan al tema.
        lado = max(requested.width(), requested.height()) if requested.isValid() else 0
        if not (0 < lado < max(img.width(), img.height())) or estilo.startswith("p"):
            lado = 0
        if not estilo and not lado:
            return img
        clave = (ident, lado)
        if clave not in self._hechos:
            if len(self._hechos) > 400:
                self._hechos.clear()
            if lado:
                img = img.scaled(lado, lado, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self._hechos[clave] = iconos.adaptar(img, estilo) if estilo else img
        return self._hechos[clave]


def imagen_de_hbitmap(bmp):
    """QImage de un HBITMAP de icono, derecha y con su transparencia (ver win.pixeles_dib)."""
    px = win.pixeles_dib(bmp)
    if px is None:
        return QImage.fromHBITMAP(bmp)
    an, al, datos = px
    # Sin ningún alfa es un mapa de bits opaco: con alfa 0 se vería vacío. Con alfa,
    # Windows lo da unas veces premultiplicado y otras no: si algún color pasa de su
    # alfa, no lo está (y tratarlo como si lo estuviera deja puntos de colores en el borde).
    alfa = datos[3::4]
    if not any(alfa):
        formato = QImage.Format.Format_RGB32
    elif any(max(datos[i:i + 3]) > alfa[i >> 2] for i in range(0, len(datos), 4)):
        formato = QImage.Format.Format_ARGB32
    else:
        formato = QImage.Format.Format_ARGB32_Premultiplied
    return QImage(datos, an, al, an * 4, formato).copy()


TAM_ICONO = 64            # se guardan a 64 px; QML pide cada uno al tamaño al que lo dibuja
# Programas que hacen de anfitrión de otros (o que ponen a cada ventana su icono,
# como las aplicaciones web de los navegadores): ahí manda el icono de la ventana.
ANFITRIONES = {"python.exe", "pythonw.exe", "py.exe", "pyw.exe", "java.exe", "javaw.exe", "rundll32.exe",
               "dllhost.exe", "mmc.exe", "applicationframehost.exe", "chrome.exe", "msedge.exe", "brave.exe",
               "vivaldi.exe", "opera.exe", "cmd.exe", "conhost.exe", "powershell.exe", "pwsh.exe"}


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
            bmp = win.shell_icon(ruta, TAM_ICONO)
            img = imagen_de_hbitmap(bmp) if bmp else QImage()
            if bmp:
                win.gdi32.DeleteObject(bmp)
            if img.isNull():
                pm = QFileIconProvider().icon(QFileInfo(ruta)).pixmap(QSize(TAM_ICONO, TAM_ICONO))
                if pm.isNull():
                    return ""
                img = pm.toImage()
            self.poner(nombre, img)
        return nombre

    def de_app(self, ident):
        """El icono de una app de la Tienda, por su identificador."""
        nombre = "app-" + "".join(ch if ch.isalnum() else "_" for ch in ident)
        if nombre not in self.imagenes:
            bmp = win.store_icon(ident, TAM_ICONO)
            img = imagen_de_hbitmap(bmp) if bmp else QImage()
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
            bmp = win.store_icon(ident, TAM_ICONO) if ident else None
            if bmp:
                img = imagen_de_hbitmap(bmp)
                win.gdi32.DeleteObject(bmp)
                if not img.isNull():
                    self.poner(nombre, img)
                    return nombre
        if exe and os.path.basename(exe).lower() not in ANFITRIONES:
            hecho = self.de_archivo(exe)         # el del .exe, a 64 px: el de la ventana suele ser de 32
            if hecho:
                return hecho
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
            exe = programas.principal(exe)
            out.append({"clave": win.clave_exe(exe), "exe": exe, "nombre": programas.nombre(exe), "ruta": ruta})
    return out


# ---------------------------------------------------------------------------

class Barra(QObject):
    """Lo que ve QML como `barra`."""
    temaCambio = Signal()
    datosCambio = Signal()
    cuentaCambio = Signal()
    concentracionCambio = Signal()
    claudeCambio = Signal()
    musicaCambio = Signal()
    animarCambio = Signal()
    escritorioCambio = Signal()
    tituloCambio = Signal()
    ropaCambio = Signal()
    momentoCambio = Signal()
    ritmoCambio = Signal()
    bandejaCambio = Signal()
    seleccionCambio = Signal()
    tiempoCambio = Signal()
    cavaCambio = Signal()
    _cava = Signal(object)
    _atajo = Signal(object)
    _tiempo = Signal(object)
    _ciudad = Signal(object)
    _musica = Signal(object)
    _bandeja = Signal(object)
    _uso = Signal(object)
    _ventana_claude = Signal(object)
    _apps = Signal(object)

    def __init__(self, app, vista=False):
        super().__init__()
        self.app, self.vista = app, vista
        self.almacen = Almacen()
        self.temas = temas.cargar()
        self.ajustes = cfg.normalizar(cfg.leer(RUTA_AJUSTES), self.temas, temas.FORMATOS)
        if not vista and cfg.reparar_fijados(self.ajustes, apps_inicio.leer):
            cfg.guardar(RUTA_AJUSTES, self.ajustes)
        self.paneles = []
        self.escritorios = win.Escritorios()
        self._escritorio = (1, 1)
        self.tray = Lista(["key", "icono", "tip", "oculto"], self)
        self._tray = {}
        self._abierta, self._ocultos = False, 0      # la flecha de la bandeja
        self._camaleon, self._camaleon_imagen, self._tono_fondo = {}, None, None
        self._pix_fondo = []
        self._inactivo, self.selector, self.motor, self._vueltas = False, None, None, 0
        self._oculto, self._luz = False, reposo.ENCHUFE      # nadie ve la barra; con qué corriente va
        self._elegido, self.novedades = None, None
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
        self.red, self._red, self._vuelta_red = red.Red(), {}, 0
        self.claudito = claudito.Claudito()
        self._personaje = claudito.copia_personaje(os.path.join(DATOS, "claudito")) if self.claudito.disponible else ""
        self.de_windows = anclados()
        self.fijos = cfg.lista_fijos(self.ajustes, self.de_windows)
        self.previa = None
        self._calendario = None
        # Isla dinámica: lo último visto de cada cosa, para avisar solo de cambios.
        self._isla = self._ult_cancion = self._modo_claude = self._red_antes = self._bat_antes = None
        self._portada_cruda, self._aviso_cancion = b"", None
        self._concentrado, self._concentrado_por_pomodoro = False, False
        self.atencion = self.encaje = None
        # Buscador (barra/buscador.py): las apps del menú Inicio se leen en un hilo y se guardan un rato.
        self._buscador = self.atajo_buscar = None
        self._ventanas_info = []                 # las abiertas, para el buscador
        self._mic_antes = []                     # quién usaba el micrófono en la vuelta anterior
        self._cuenta, self._t_cuenta = None, None    # el temporizador
        self._apps_lista, self._apps_hora, self._apps_hilo, self._iconos_apps = [], 0.0, None, {}
        self._orden = {}            # cuándo se vio cada programa
        self._arrastre = 0          # desde cuándo se arrastra un botón; 0 si no
        self._ids = {}              # ventana -> identificador de app de la Tienda
        self.panel_claude = None
        self._uso_datos, self._uso_hora, self._uso_hilo = None, 0, None
        self._uso.connect(self._set_uso)
        self._ventana_claude.connect(lambda h: win.activate(h))
        self._sitio_claude = None
        self._t_claude = QTimer(self, singleShot=True, interval=350, timeout=self._mostrar_claude)
        self._centrado, self._apariencia = temas.windows_centrado(), temas.apariencia_windows()
        self.fondo = vidrio.fondo = vidrio.Fondo()
        self.temaCambio.connect(self._zonas_vidrio)
        self.animarCambio.connect(self._zonas_vidrio)
        self._apuntado, self._previa_desde = None, 0
        self._t_previa = QTimer(self, singleShot=True, interval=380, timeout=self._mostrar_previa)
        self._seleccion = ""        # lo elegido con el teclado: "t:" y una fila, o "b:" y un icono
        self._clima, self._hilo_tiempo = dict(tiempo.NADA), None
        self._barras = [0] * 16
        self._cava.connect(self._set_cava)
        self._atajo.connect(self._hacer_atajo)
        self._apps.connect(self._apps_leidas)
        self._tiempo.connect(self._set_tiempo)
        self._ciudad.connect(self._set_ciudad)
        self._musica.connect(self._set_musica)
        self._bandeja.connect(self._set_bandeja)
        self.musica = None
        self._aplicar_tema(self._tema_que_toca())

    def arrancar(self):
        self.musica = musica.Musica(self._musica.emit)
        self._t_sis = QTimer(self, interval=2000, timeout=self._sistema)
        self._t_cl = QTimer(self, interval=900, timeout=self._leer_claude)
        self._t_ropa = QTimer(self, interval=5000, timeout=self._leer_ropa)
        self._t_ropa.start()
        self._leer_ropa()
        self._t_tema = QTimer(self, interval=10000, timeout=self._revisar_tema)
        self._t_ven = QTimer(self, interval=1200, timeout=self.actualizar_ventanas)
        self._t_pronto = QTimer(self, interval=60, singleShot=True, timeout=self.actualizar_ventanas)
        for t in (self._t_sis, self._t_cl, self._t_tema, self._t_ven):
            t.start()
        if not self.vista:
            self._t_arranque = QTimer(self, interval=5 * 60 * 1000, timeout=self._vigilar_arranque)
            self._t_arranque.start()
            QTimer.singleShot(30_000, self._vigilar_arranque)
        self._t_tiempo = QTimer(self, interval=20 * 60 * 1000, timeout=self._pedir_tiempo)
        self._t_tiempo.start()
        QTimer.singleShot(3000, self._pedir_tiempo)
        self._gancho = win.watch(self._t_pronto.start)
        if not self.vista:
            try:
                self.encaje = encaje.EncajeAbajo(lambda: self._get_tema()["colores"]["acento"])
                if not self.encaje.ok:
                    registrar("sin encaje abajo en pantallas verticales (SetWinEventHook)")
                self.paneles_windows = paneles.Paneles(self._donde_panel)
                if not self.paneles_windows.ok:
                    registrar("sin paneles de Windows junto a la barra (SetWinEventHook)")
                self.atencion = atencion.Atencion(self._pide_atencion, self._t_pronto.start)
                if not self.atencion.ok:
                    registrar("sin aviso de ventanas que piden atención (RegisterShellHookWindow)")
            except Exception:
                registrar("atención")
            try:
                self.atajo_buscar = buscador.Atajo(self.abrir_buscador)
                self._poner_atajo_buscar()
                self.animarCambio.connect(self._poner_atajo_buscar)
                QTimer.singleShot(20_000, self._leer_apps)      # para que la primera vez ya esté
            except Exception:
                registrar("atajo del buscador")
        self._t_raton = QTimer(self, interval=120, timeout=self._vigilar_raton)
        if self.ajustes["esconder"]:
            self._t_raton.start()
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
        else:
            self._actualizar_camaleon()

    def _aplicar_tema(self, ident):
        self._elegido = ident
        self._actualizar_camaleon(avisar=False)
        self.temaCambio.emit()

    def _necesita_fondo(self):
        t = self.temas[self._elegido]
        return t["dinamico"] or t["vidrio"] or t["adapta"] or t["translucida"] or self.ajustes["icono"] == "fondo"

    def _actualizar_camaleon(self, avisar=True):
        if not self._necesita_fondo():
            return
        ruta = temas.imagen_fondo(any("wallpaper" in os.path.basename(v["exe"]).lower()
                                      for v in self._tray.values()) or self.vista)
        marca = (ruta, os.path.getmtime(ruta) if ruta else 0)
        if marca == self._camaleon_imagen:
            return
        self._camaleon_imagen = marca
        img = QImage(ruta).scaled(40, 40) if ruta else QImage()
        pix = [QColor(img.pixel(x, y)).getRgb()[:3] for x in range(img.width()) for y in range(img.height())]
        self._pix_fondo = pix
        self._camaleon = temas.paleta(pix)
        self._tono_fondo = self._camaleon.pop("tono", None)
        if avisar:
            self.temaCambio.emit()

    def _get_tema(self):
        t = self.temas[self._elegido]
        if t["dinamico"]:
            t = {**t, "colores": {**t["colores"], **self._camaleon}}
        t = temas.con_momento(t, self._momento)
        t = temas.con_variante(t, self.ajustes["variantes"].get(self._elegido, "tema"))
        t = temas.con_integrado(t, self.ajustes["integrado"])
        detras = temas.brillo_de_lado(self._pix_fondo, self.ajustes["posicion"]) if t["translucida"] else 0
        t = temas.con_windows_y_opacidad(t, self._apariencia, self.ajustes["formatos"].get(self._elegido, "tema"),
                                         self.ajustes["opacidad"], detras)
        t = temas.con_posicion(t, self.ajustes["posicion"])
        # Lo elegido en Widgets manda sobre el formato y la posición.
        t = temas.con_widgets(t, self.ajustes["disenos"], self.ajustes["sistema"], self.ajustes["claudito"])
        t = temas.con_concentracion(t, self._concentrado)
        t = iconos.con_iconos(t, self.ajustes["iconos"])
        t = temas.con_icono(t, self._tono_fondo if self.ajustes["icono"] == "fondo" or t["vidrio"] or t["adapta"] else None)
        t = temas.con_busqueda(t, self.ajustes["barra_busqueda"] and not self.vista)
        t = temas.con_vista_tareas(t, self.ajustes["vista_tareas"])
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

    def _set_opacidad(self, n):
        self.ajustes["opacidad"] = n
        self._guardar()
        self._actualizar_camaleon(avisar=False)
        self.temaCambio.emit()

    def _set_iconos(self, cual):
        self.ajustes["iconos"] = cual
        self._guardar()
        self.temaCambio.emit()

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

    def sitio(self, x, y):
        """Función que coloca una ventanita junto a la barra, frente a ese punto."""
        g = (QGuiApplication.screenAt(QPoint(round(x), round(y))) or self.app.primaryScreen()).geometry().getRect()
        t = self._get_tema()
        hueco = temas.forma_menus(t, self.ajustes["menus"])[1]
        return lambda an, al: sitio.colocar(t["lado"], (x, y), an, al, g, self.alto(), hueco)

    def _donde_panel(self, hwnd, rect):
        """Para barra/paneles.py: (lado, pantalla, barra) en píxeles físicos de la pantalla
        de ese panel de Windows, o None si allí la barra no está a un lado."""
        lado = self.ajustes["posicion"]
        if lado not in ("izquierda", "derecha"):
            return None
        cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
        for p in self.paneles:
            s = p.pantalla
            f = s.devicePixelRatio()
            g = s.geometry()
            pant = (round(g.x() * f), round(g.y() * f), round((g.x() + g.width()) * f), round((g.y() + g.height()) * f))
            if pant[0] <= cx < pant[2] and pant[1] <= cy < pant[3]:
                x, y, an, al = p.zona_real()
                return lado, pant, (round(x * f), round(y * f), round((x + an) * f), round((y + al) * f))
        return None

    def esquinas_menus(self):
        return temas.forma_menus(self._get_tema(), self.ajustes["menus"])[0]

    def _set_menus(self, modo):
        self.ajustes["menus"] = modo
        self._guardar()

    def _set_posicion(self, lado):
        self.ajustes["posicion"] = lado
        self._guardar()
        self._quitar_previa()
        self.temaCambio.emit()
        if self.selector and self.selector.isVisible():
            pos = self.selector.geometry().center()          # que no quede debajo de la barra
            self.selector.abrir(self.sitio(pos.x(), pos.y()))

    @Slot()
    def mover_al_raton(self):
        """Se soltó la barra tras arrastrarla: al lado más cercano."""
        pos = QCursor.pos()
        g = (QGuiApplication.screenAt(pos) or self.app.primaryScreen()).geometry().getRect()
        lado = sitio.mas_cerca((pos.x(), pos.y()), g)
        if lado != self.ajustes["posicion"]:
            QTimer.singleShot(0, lambda: self._set_posicion(lado))

    def alto(self):
        return temas.alto_total(self._get_tema())

    def _set_formato(self, f):
        self.ajustes["formatos"][self._elegido] = f
        self._guardar()
        self.temaCambio.emit()

    def _set_variante(self, v):
        self.ajustes["variantes"][self._elegido] = v
        self._guardar()
        self._actualizar_camaleon(avisar=False)
        self.temaCambio.emit()

    def _variante_para_todos(self):
        v = self.ajustes["variantes"].get(self._elegido, "tema")
        self.ajustes["variantes"] = {t: v for t in self.temas}
        self._guardar()

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
        if self._vuelta_red % 3 == 0:            # cada 6 s: cuesta unos 7 ms
            try:
                r, b = self.red.leer(), red.bateria()
                self._red = {"red": red.glifo_red(r), "redTexto": self._texto_red(r),
                             "bateria": red.glifo_bateria(*b) if b else "", "bateriaPct": b[0] if b else -1,
                             "cargando": bool(b and b[1])}
                self._avisos_red(r, b)
            except Exception:
                registrar("red")
        self._vuelta_red += 1
        self._set_datos({**uso, "microfono": self._microfono(), "historia": dict(self._historia) if self.temas[self._elegido]["medidor"] == "onda" else {},
                         "volumen": v[0] if v else 0, "silencio": v[1] if v else True, **self._red})

    def _microfono(self):
        """Los programas que graban del micrófono, por su nombre; avisa en la isla del que empieza."""
        try:
            exes = audio.grabando()
        except Exception:
            registrar("micrófono")
            return []
        nombres = {i["exe"].lower(): i["nombre"] for i in self._ventanas_info}
        quien = []
        for e in exes:
            p = programas.principal(e)
            quien.append(nombres.get(p.lower()) or os.path.splitext(os.path.basename(p))[0])
        quien = list(dict.fromkeys(quien))
        for n in quien:
            if n not in self._mic_antes:
                self._avisar({"icono": "", "tipo": "aviso", "importante": True, "titulo": "Micrófono en uso", "detalle": n,
                              "hacer": lambda: os.startfile("ms-settings:privacy-microphone")})
        self._mic_antes = quien
        return quien

    @staticmethod
    def _texto_red(r):
        if r["tipo"] == "no":
            return "Sin conexión"
        nombre = r["nombre"] + (f" ({r['senal']} %)" if r["tipo"] == "wifi" else "")
        return nombre + ("" if r["internet"] else " · sin internet")

    def _set_datos(self, d):
        if d != self._datos:
            self._datos = d
            self.datosCambio.emit()

    datos = Property("QVariantMap", lambda self: self._datos, notify=datosCambio)

    # ----- temporizador (se pone desde el buscador: «10 min», «pomodoro») -----
    def _empezar_cuenta(self, segundos, pomodoro=False, fase="trabajo", descanso=0):
        if pomodoro and self.ajustes["concentrar_pomodoro"]:
            if fase == "trabajo" and not self._concentrado:
                self._concentrado_por_pomodoro = True
                self.concentrarse(True)
            elif fase != "trabajo" and self._concentrado_por_pomodoro:
                self.concentrarse(False, avisar=False)        # ya sale «Pomodoro hecho»
        self._cuenta = {"fin": time.monotonic() + segundos, "total": segundos, "pomodoro": pomodoro, "fase": fase,
                        "descanso": descanso, "hecho": 0.0}
        if self._t_cuenta is None:
            self._t_cuenta = QTimer(self)
            self._t_cuenta.setInterval(1000)
            self._t_cuenta.timeout.connect(self._tic_cuenta)
        self._t_cuenta.start()
        self._tic_cuenta()

    def _tic_cuenta(self):
        c = self._cuenta
        if not c:
            self._t_cuenta.stop()
            return
        ahora = time.monotonic()
        if c["hecho"]:                           # «¡Tiempo!» se queda un rato y se va
            if ahora - c["hecho"] > 10:
                self._cuenta = None
                self._t_cuenta.stop()
            self.cuentaCambio.emit()
            return
        if c["fin"] - ahora > 0:
            self.cuentaCambio.emit()
            return
        try:
            import winsound
            winsound.MessageBeep(0x40)
        except Exception:
            pass
        if c["pomodoro"] and c["fase"] == "trabajo" and c["descanso"]:
            self._avisar({"icono": "", "tipo": "ok", "importante": True, "titulo": "Pomodoro hecho", "detalle": buscador.duracion(c["descanso"]) + " de descanso"})
            self._empezar_cuenta(c["descanso"], True, "descanso")
            return
        if self._concentrado_por_pomodoro:
            self.concentrarse(False, avisar=False)            # ya sale el del temporizador
        titulo = "Descanso terminado" if c["fase"] == "descanso" else "Temporizador"
        self._avisar({"icono": "", "tipo": "ok", "importante": True, "titulo": titulo, "detalle": buscador.duracion(c["total"]) + " cumplidos"})
        c["hecho"] = ahora
        self.cuentaCambio.emit()

    @Slot()
    def parar_cuenta(self):
        if self._concentrado_por_pomodoro:
            self.concentrarse(False)
        self._cuenta = None
        if self._t_cuenta:
            self._t_cuenta.stop()
        self.cuentaCambio.emit()

    def _get_cuenta(self):
        c = self._cuenta
        if not c:
            return {}
        if c["hecho"]:
            return {"texto": "¡Tiempo!", "fase": c["fase"], "hecho": True, "parte": 1}
        queda = max(0, round(c["fin"] - time.monotonic()))
        h, r = divmod(queda, 3600)
        texto = f"{h}:{r // 60:02d}:{r % 60:02d}" if h else f"{r // 60}:{r % 60:02d}"
        return {"texto": texto, "fase": c["fase"], "hecho": False, "parte": 1 - queda / c["total"],
                "pomodoro": c["pomodoro"]}

    cuenta = Property("QVariantMap", _get_cuenta, notify=cuentaCambio)

    # ----- modo concentración -----
    @Slot(bool)
    def concentrarse(self, si, avisar=True):
        """Esconde lo que distrae (temas.con_concentracion) y la isla solo avisa de lo importante.
        `avisar`: False cuando ya sale otro aviso (el del pomodoro) que no hay que tapar."""
        if si == self._concentrado:
            return
        if not si:
            self._concentrado_por_pomodoro = False
        if avisar:
            self._avisar({"icono": "", "tipo": "info", "importante": True,
                          "titulo": "Concentración" if si else "Fin de la concentración",
                          "detalle": "Solo avisos importantes" if si else "Todo vuelve a la barra"})
        self._concentrado = si
        self.concentracionCambio.emit()
        self.temaCambio.emit()

    concentrado = Property(bool, lambda self: self._concentrado, notify=concentracionCambio)

    def _set_concentrar_pomodoro(self, si):
        self.ajustes["concentrar_pomodoro"] = si
        self._guardar()

    def _set_musica(self, d):
        d = dict(d)
        crudo = d.pop("portada", b"")
        if crudo != self._portada_cruda:          # la carátula, una vez por canción
            self._portada_cruda = crudo
            img = QImage.fromData(crudo) if crudo else QImage()
            if img.isNull():
                self.almacen.imagenes.pop("portada", None)
            else:
                self.almacen.poner("portada", img.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                         Qt.TransformationMode.SmoothTransformation))
        d["portada"] = self.almacen.url("portada")
        self._cancion = d
        self.musicaCambio.emit()
        if d.get("titulo") and d.get("sonando"):
            clave = (d["titulo"], d.get("artista", ""))
            if self._ult_cancion is not None and clave != self._ult_cancion:
                self._aviso_cancion = clave
                self._avisar(self._aviso_musica(d))
            self._ult_cancion = clave
        # Si la carátula llega después del aviso (Spotify), la isla la recoge.
        if crudo and self._isla and self._isla.isVisible() and self._aviso_cancion == (d["titulo"], d.get("artista", "")):
            self._avisar(self._aviso_musica(d))

    def _aviso_musica(self, d):
        """El de una canción: con su carátula y, al pasar el ratón, anterior, pausa y siguiente."""
        return {"icono": "", "tipo": "musica", "titulo": d["titulo"], "detalle": d.get("artista", ""),
                "imagen": self.almacen.get("portada"), "sonando": d.get("sonando", False),
                "controles": self.musica.orden}

    # ----- ventanas que piden atención (barra/atencion.py) -----
    def _pide_atencion(self, h):
        if h == win.user32.GetForegroundWindow():
            self.atencion.piden.discard(h)
            return
        exe = programas.principal(win.app_exe(h))
        nombre, titulo = self._nombre(h, exe), win.title(h)
        try:
            imagen = self.almacen.get(self.almacen.de_ventana(h, win.app_exe(h)))
        except Exception:
            imagen = None
        self._avisar({"icono": "", "tipo": "aviso", "imagen": imagen, "titulo": nombre or titulo or "Un programa te llama",
                      "detalle": titulo if titulo != nombre else "", "hacer": lambda: win.activate(h)})

    # ----- buscador (barra/buscador.py) -----
    def _poner_atajo_buscar(self):
        """Alt+Espacio mientras el buscador esté puesto; en modo juego se suelta, para no quitárselo al juego."""
        if self.atajo_buscar:
            quiere = self.ajustes["buscador"] and self._animar
            if self.atajo_buscar.poner(quiere) != quiere and quiere:
                registrar("Alt+Espacio ya lo usa otro programa: el buscador sigue en el clic central de Inicio")

    def _set_integrado(self, si):
        self.ajustes["integrado"] = si
        self._guardar()
        self._actualizar_camaleon(avisar=False)
        self.temaCambio.emit()

    def _set_vista_tareas(self, si):
        self.ajustes["vista_tareas"] = si
        self._guardar()
        self.temaCambio.emit()

    def _set_pantallas(self, modo):
        self.ajustes["pantallas"] = modo
        self._guardar()
        self._quitar_previa()
        self.actualizar_ventanas()

    def _set_barra_busqueda(self, si):
        self.ajustes["barra_busqueda"] = si
        self._guardar()
        self.temaCambio.emit()

    def _set_buscador(self, si):
        self.ajustes["buscador"] = si
        self._guardar()
        self._poner_atajo_buscar()

    def _leer_apps(self):
        if self._apps_hilo and self._apps_hilo.is_alive():
            return
        def leer():
            try:
                self._apps.emit(apps_inicio.leer())
            except Exception:
                registrar("apps del menú Inicio")
        self._apps_hilo = threading.Thread(target=leer, daemon=True)
        self._apps_hilo.start()

    def _apps_leidas(self, lista):
        self._apps_lista, self._apps_hora = lista, time.monotonic()
        if self._buscador:
            self._buscador.poner_apps(lista)

    def _icono_resultado(self, r):
        if r["tipo"] == "ventana":               # image://iconos/<nombre>/<revisión>
            partes = r.get("icono", "").split("/")
            return self.almacen.get(partes[3]) if len(partes) > 3 else None
        if r["tipo"] != "app":
            return None
        if r["id"] not in self._iconos_apps:
            nombre = self.almacen.de_app(r["id"])
            self._iconos_apps[r["id"]] = self.almacen.get(nombre) if nombre else None
        return self._iconos_apps[r["id"]]

    def _usado(self, r):
        if r["tipo"] == "concentracion":
            self.concentrarse(not self._concentrado)
            return
        if r["tipo"] == "temporizador":
            if r["pomodoro"]:                    # sus minutos se quedan para la próxima vez
                self.ajustes["pomodoro"] = [r["segundos"] // 60, r["descanso"] // 60]
                self._guardar()
            self._empezar_cuenta(r["segundos"], r["pomodoro"], descanso=r.get("descanso", 0))
            return
        if r["tipo"] != "app":
            return
        usos = self.ajustes["lanzados"]
        usos[r["id"]] = usos.get(r["id"], 0) + 1
        if len(usos) > 200:                      # solo los más usados
            self.ajustes["lanzados"] = dict(sorted(usos.items(), key=lambda x: -x[1])[:150])
        self._guardar()

    @Slot()
    def abrir_buscador(self, texto=""):
        if self.vista or not self.paneles:
            return
        if self._buscador is None:
            self._buscador = buscador.Buscador(self._icono_resultado, self._usado)
        elif not texto and (self._buscador.isVisible() or time.monotonic() - self._buscador.cerrado < 0.3):
            self._buscador.hide()
            return
        if not self._apps_lista or time.monotonic() - self._apps_hora > 30:
            self._leer_apps()                    # al momento con la lista vieja; la nueva llega sola
        self._quitar_previa()
        p = next((x for x in self.paneles if x.primaria), self.paneles[0])
        x, y, an, al = p.zona_real()
        ventanas = [{"id": str(i["hwnd"]), "nombre": i["nombre"], "titulo": i["titulo"], "icono": i["icono"]}
                    for i in self._ventanas_info]
        self._buscador.mostrar(self.sitio(x + an / 2, y + al / 2), self._get_tema(), self._apps_lista,
                               self.ajustes["lanzados"], ventanas, self.ajustes["pomodoro"], texto)

    # ----- isla dinámica -----
    def _avisar(self, aviso):
        if not self.ajustes["isla"] or self.vista or self._plena or not self._animar or not self.paneles:
            return
        if self._concentrado and not aviso.get("importante"):
            return
        try:
            p = next((x for x in self.paneles if x.primaria), self.paneles[0])
            x, y, an, al = p.zona_real()
            if self._isla is None:
                self._isla = isla.Isla()
            self._isla.avisar(aviso, self.sitio(x + an / 2, y + al / 2), self._get_tema())
        except Exception:
            registrar("isla")

    def _set_isla(self, si):
        self.ajustes["isla"] = si
        self._guardar()
        if not si and self._isla:
            self._isla.hide()

    def _avisos_red(self, r, b):
        antes, self._red_antes = self._red_antes, (r["tipo"], r["internet"], r["nombre"])
        if antes is not None and antes != self._red_antes:
            if r["internet"]:
                self._avisar({"icono": red.glifo_red(r), "tipo": "ok",
                              "titulo": "Conectado", "detalle": r["nombre"]})
            else:
                self._avisar({"icono": red.glifo_red(r), "tipo": "error",
                              "titulo": "Sin internet" if r["tipo"] != "no" else "Sin conexión", "detalle": r["nombre"]})
        bat, self._bat_antes = self._bat_antes, b
        if b and bat:
            if b[1] and not bat[1]:
                self._avisar({"icono": red.glifo_bateria(*b), "tipo": "ok",
                              "titulo": "Cargando", "detalle": f"{b[0]} %"})
            elif not b[1] and b[0] <= 20 < bat[0]:
                self._avisar({"icono": red.glifo_bateria(*b), "tipo": "error", "importante": True,
                              "titulo": "Batería baja", "detalle": f"Queda un {b[0]} %"})

    cancion = Property("QVariantMap", lambda self: self._cancion, notify=musicaCambio)

    def _leer_claude(self):
        if self.claudito.disponible and self._animar:
            d = self.claudito.leer()
            if self.panel_claude and self.panel_claude.isVisible():
                self.panel_claude.poner(self.claudito.sesiones, self._uso_datos)
            if d and d != self._claude:
                self._claude = d
                self.claudeCambio.emit()
            if d:
                modo, self._modo_claude = self._modo_claude, d.get("modo")
                if modo is not None and d.get("modo") == "waiting" and modo != "waiting":
                    self._avisar({"icono": "", "tipo": "info", "importante": True, "titulo": "Claude te espera", "detalle": d.get("texto", ""),
                                  "hacer": lambda: self.ir_a_claude()})

    def _leer_ropa(self):
        r = self.claudito.ropa()
        if r != self._ropa:
            self._ropa = r
            self.ropaCambio.emit()

    ropa = Property("QVariantMap", lambda self: self._ropa, notify=ropaCambio)
    claude = Property("QVariantMap", lambda self: self._claude, notify=claudeCambio)
    personaje = Property(str, lambda self: QUrl.fromLocalFile(self._personaje).toString()
                         if self.claudito.disponible else "", constant=True)
    mes = Property(int, lambda self: time.localtime().tm_mon, notify=momentoCambio)
    def _set_animaciones(self, a):
        self.ajustes["animaciones"] = a
        self._guardar()
        self.ritmoCambio.emit()

    # Milisegundos entre fotogramas de los fondos, y si se mueven.
    ritmo = Property(int, lambda self: reposo.ritmo(self.ajustes["animaciones"], self._luz), notify=ritmoCambio)
    mover = Property(bool, lambda self: reposo.mover(self._animar, self.ajustes["animaciones"], self._inactivo,
                                                     self._oculto, self._luz), notify=ritmoCambio)

    # Cada cuántas décimas de segundo se redibuja Claudito.
    paso = Property(int, lambda self: reposo.paso(self.ajustes["animaciones"], self._inactivo, self._oculto, self._luz),
                    notify=ritmoCambio)

    def _ver_inactividad(self):
        """Tras un rato sin tocar nada, con la pantalla bloqueada o la barra escondida, los dibujos se paran;
        con batería van más despacio."""
        estado = (win.segundos_inactivo() > INACTIVO,
                  win.pantalla_bloqueada() or bool(self.paneles) and all(p.escondida for p in self.paneles),
                  reposo.corriente(red.bateria_estado()))
        if estado != (self._inactivo, self._oculto, self._luz):
            self._inactivo, self._oculto, self._luz = estado
            self.ritmoCambio.emit()

    # El escritorio virtual en el que estás y cuántos hay.
    escritorio = Property("QVariantMap", lambda self: {"n": self._escritorio[0], "total": self._escritorio[1]},
                          notify=escritorioCambio)

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
        self.panel_claude.mostrar(self.claudito.sesiones, self._uso_datos, self.sitio(x, y), self._get_tema())
        self._pedir_uso()

    def _pedir_uso(self):
        if time.monotonic() - self._uso_hora < 30 and self._uso_datos or not self.claudito.disponible or self._uso_hilo and self._uso_hilo.is_alive():
            return
        self._uso_hilo = threading.Thread(target=self._calcular_uso, daemon=True)
        self._uso_hilo.start()

    def _calcular_uso(self):
        try:
            r = subprocess.run([sys.executable.replace("pythonw.exe", "python.exe"),
                                os.path.join(AQUI, "barra", "uso.py")], capture_output=True, text=True, timeout=180,
                               stdin=subprocess.DEVNULL, creationflags=SIN_CONSOLA)
            if r.returncode:
                raise ValueError(r.stderr[-1500:])
            self._uso.emit(json.loads(r.stdout))
        except (OSError, ValueError, subprocess.TimeoutExpired) as e:
            if not self._uso_datos:             # si ya había un dato, se queda
                registrar(f"uso de Claude: {e}")
                self._uso.emit({"error": True})
        except RuntimeError:
            pass                                # la barra se está cerrando

    def _set_uso(self, d):
        self._uso_datos, self._uso_hora = d, time.monotonic() - (25 if d.get("error") else 0)
        if self.panel_claude and self.panel_claude.isVisible():
            self.panel_claude.poner(self.claudito.sesiones, d)

    def _boton_conectar(self):
        """Solo si no está conectado: el Claudito completo ya lo conecta al instalarse."""
        if not conectar.hay_claude_code():
            return []
        avisos = conectar.estado()["avisos"]
        if avisos == "no":
            return [{"texto": "Conectar Claude Code", "hacer": lambda: QTimer.singleShot(0, self._conectar)}]
        return [{"texto": "Desconectar Claude Code", "hacer": self._desconectar}] if avisos == "nuestra" else []

    def _aviso(self, texto, botones=QMessageBox.StandardButton.Ok):
        d = QMessageBox(QMessageBox.Icon.Information, "Claudito", texto, botones)
        d.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        QTimer.singleShot(0, lambda: win.user32.SetForegroundWindow(int(d.winId())))
        return QMessageBox.StandardButton(d.exec())

    def _conectar(self):
        b = QMessageBox.StandardButton
        if self._aviso("Para que Claudito vea tus sesiones y los límites del plan, se añaden sus avisos y su línea de estado "
                       "al settings.json de Claude Code (si ya tienes otra línea de estado, se respeta). Antes se guarda una "
                       "copia, settings.json.claudito-backup, y se quita en este mismo menú o al desinstalar.\n\n¿Conectar?",
                       b.Yes | b.No) != b.Yes:
            return
        fallo = conectar.conectar()
        self._uso_datos = None
        self._aviso("No se pudo conectar:\n" + fallo if fallo else
                    "Conectado. Las sesiones nuevas de Claude Code lo usarán; en una ya abierta, escribe /hooks una vez.")

    def _desconectar(self):
        conectar.desconectar()
        self._uso_datos = None

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
        visto = temas.windows_centrado(), temas.apariencia_windows()
        if visto != (self._centrado, self._apariencia):
            self._centrado, self._apariencia = visto
            self.temaCambio.emit()
        activa = win.user32.GetForegroundWindow()
        self._vueltas += 1
        if not self.vista:
            self._ver_inactividad()
        todas = win.windows()
        self.almacen.olvidar_ventanas(set(todas))
        piden = set()
        if self.atencion:
            self.atencion.olvidar(set(todas) - {activa})
            piden = self.atencion.piden
        hwnds = self.escritorios.filtrar(todas)       # las de otros escritorios virtuales, no
        e = win.escritorio_actual()
        if e != self._escritorio:
            self._escritorio = e
            self.escritorioCambio.emit()
        info = []
        self._ids = {h: i for h, i in self._ids.items() if h in todas}
        for z, h in enumerate(hwnds):            # de la más reciente a la más antigua
            exe = programas.principal(win.app_exe(h))
            info.append({"hwnd": h, "exe": exe, "titulo": win.title(h), "z": z,
                         "activa": h == activa and not win.user32.IsIconic(h),
                         "clave": win.clave_exe(exe), "nombre": self._nombre(h, exe),
                         "minimizada": bool(win.user32.IsIconic(h)), "pantalla": win.monitor_of(h), "atencion": h in piden,
                         "icono": self.almacen.url(self.almacen.de_ventana(h, exe))})
        self._ventanas_info = info
        titulo = next((i["titulo"] for i in info if i["activa"]), "")
        if titulo != self._titulo:
            self._titulo = titulo
            self.tituloCambio.emit()
        for p in self.paneles:
            p.poner_ventanas(info, self.fijos)
        if self.previa and self.previa.hwnds:
            self.previa.quitar_muertas(hwnds)
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
            p.mostrar(p.pantalla_real() not in self._plena, self._vueltas % 4 == 0)
        if self._plena:
            self._quitar_previa()
            self.claude_salir()
        animar = not self._plena
        if animar != self._animar:
            self._animar = animar
            if self.musica:
                self.musica.pausada = not animar
            self.animarCambio.emit()
            self.ritmoCambio.emit()

    def _id_tienda(self, h, exe):
        """El identificador de app de la ventana, si es de la Tienda."""
        if h not in self._ids:
            i = ""
            if win.de_la_tienda(h, exe):      # Windows Terminal no lo pone en la ventana: el del proceso
                i = win.app_id(h) or win.app_id_proceso(win.pid_of(h))
            self._ids[h] = i if "!" in i else ""
        return self._ids[h]

    def _nombre(self, h, exe):
        i = self._id_tienda(h, exe)
        return (programas.nombre_tienda(i) if i else "") or programas.nombre(exe)

    def _fila(self, clave):
        for p in self.paneles:
            for f in p.tareas.filas:
                if f["key"] == clave:
                    return f
        return None

    @Slot(str, bool)
    def pulsar_tarea(self, clave, nueva):
        f = self._fila(clave)
        if not f:
            return
        if not f["hwnd"] or nueva:
            self._quitar_previa()
            self._abrir(f)
        elif f["cuenta"] > 1:
            # Varias: se enseñan para elegir; otro clic las esconde.
            if self.previa and self.previa.isVisible() and self.previa.clave == clave and not self._t_previa.isActive():
                if time.monotonic() - self._previa_desde > 0.6:
                    self._quitar_previa()
            elif self._apuntado:
                self._t_previa.stop()
                self._mostrar_previa()
        else:
            self._quitar_previa()
            h = int(f["hwnd"])
            if f["activa"]:
                win.minimize(h)
            else:
                win.activate(h)

    @Slot(str, int, bool, result=int)
    def rodar_tarea(self, clave, paso, ventanas):
        """La rueda sube o baja el volumen del programa (si tiene sonido abierto) y
        devuelve el nuevo, para enseñarlo; si no, o con Mayús, pasa por sus ventanas (y da -1)."""
        f = self._fila(clave)
        if f and f["exe"] and not ventanas:
            try:
                nivel = audio.cambiar_volumen(f["exe"], -5 * paso)
            except Exception:
                registrar("volumen de " + f["exe"])
                nivel = None
            if nivel is not None:
                return nivel
        if f and f["cuenta"] > 1:
            vs = f["ventanas"]
            activa = win.user32.GetForegroundWindow()
            i = (vs.index(activa) + paso) % len(vs) if activa in vs else vs.index(int(f["hwnd"]))
            win.activate(vs[i])
        return -1

    def _entrada(self, f):
        """Lo necesario para anclar o volver a abrir el programa de una fila."""
        ruta = f["ruta"]
        if not ruta and f["hwnd"]:
            i = self._id_tienda(int(f["hwnd"]), f["exe"])
            ruta = TIENDA + i if i else ""
        return {"clave": win.clave_exe(f["exe"]), "exe": f["exe"], "nombre": f["nombre"], "ruta": ruta}

    def _abrir(self, f, modo="open"):
        e = self._entrada(f)
        try:
            os.startfile(e["ruta"] or e["exe"], modo)
        except OSError:
            registrar("abrir " + str(e["exe"]))

    # ----- archivos arrastrados encima -----
    @Slot(str)
    def archivo_encima(self, clave):
        """Un archivo lleva un rato sobre el botón: su ventana pasa delante
        para poder soltarlo dentro, como en la barra de Windows."""
        f = self._fila(clave)
        if f and f["hwnd"]:
            self._quitar_previa()
            win.activate(int(f["hwnd"]))

    @Slot(str, "QVariantList")
    def soltar_archivos(self, clave, urls):
        """Soltados sobre el botón: se abren con ese programa."""
        f = self._fila(clave)
        if not f:
            return
        e = self._entrada(f)
        rutas = [os.path.normpath(QUrl(u).toLocalFile()) for u in urls if QUrl(u).isLocalFile()]
        como = programas.abrir_con(e["exe"], e["ruta"], rutas)
        try:
            if como and como[0] == "exe":
                subprocess.Popen(como[1], cwd=os.path.dirname(como[1][0]), close_fds=True)
            elif como:
                win.shell32.ShellExecuteW(None, "open", como[1], subprocess.list2cmdline(rutas), None, 1)
            elif f["hwnd"]:
                win.activate(int(f["hwnd"]))
        except OSError:
            registrar("soltar en " + str(e["exe"]))

    # ----- arrastrar botones -----
    def arrastrando(self):
        return bool(self._arrastre) and time.monotonic() - self._arrastre < 30      # por si se perdiera el final

    @Slot()
    def empezar_arrastre(self):
        self._quitar_previa()
        self._arrastre = time.monotonic()

    @Slot(QObject)
    def terminar_arrastre(self, lista):
        if not self._arrastre:
            return
        self._arrastre = 0
        claves = list(dict.fromkeys(f["clave"] for f in lista.filas))
        self.ajustes["orden"] = cfg.fusionar_orden(self.ajustes["orden"], claves)
        self._guardar()
        self.actualizar_ventanas()

    def _olvidar_orden(self):
        self.ajustes["orden"] = []
        self._guardar()
        self.actualizar_ventanas()

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
        if self._poner_saltos(m, f, e):
            m.addSeparator()
        if f["cuenta"] > 1:
            for h, t in list(zip(f["ventanas"], f["titulos"]))[:12]:
                corto = t if len(t) <= 48 else t[:47] + "…"
                m.addAction(corto.replace("&", "&&"), lambda h=h: win.activate(h))
            m.addSeparator()
        m.addAction("Abrir otra ventana" if f["hwnd"] else "Abrir", lambda: self._abrir(f))
        if any(x["clave"] == e["clave"] for x in self.fijos):
            m.addAction("Desanclar de esta barra", lambda: self._anclar(e, False))
        elif e["exe"]:
            m.addAction("Anclar a esta barra", lambda: self._anclar(e, True))
        vs = list(f["ventanas"])
        if len(vs) == 1:
            h = vs[0]
            m.addSeparator()
            if win.user32.IsIconic(h) or win.user32.IsZoomed(h):
                m.addAction("Restaurar", lambda: win.restore(h))
            if not win.user32.IsIconic(h):
                m.addAction("Minimizar", lambda: win.minimize(h))
            if not win.user32.IsZoomed(h):
                m.addAction("Maximizar", lambda: win.maximize(h))
            m.addSeparator()
            m.addAction("Cerrar ventana", lambda: win.close(h))
        elif vs:
            m.addSeparator()
            m.addAction("Minimizar todas", lambda: [win.minimize(h) for h in vs])
            m.addSeparator()
            m.addAction(f"Cerrar las {len(vs)} ventanas", lambda: [win.close(h) for h in vs])
        return m

    def _poner_saltos(self, m, f, e):
        """La lista de saltos del programa: sus tareas y los recientes."""
        try:
            appid = saltos.id_de_ventana(int(f["hwnd"])) if f["hwnd"] else saltos.id_de_acceso(e["ruta"]) if e["ruta"] else ""
            grupos = saltos.tareas(appid)
            if saltos.mostrar_recientes():
                vistos = saltos.recientes(appid, 6)
                if vistos:
                    grupos.insert(0, ("Recientes", [{"reciente": r} for r in vistos]))
        except Exception:
            registrar("lista de saltos")
            return False
        for nombre, cosas in grupos:
            cabeza = QAction(nombre or "Tareas", m)
            cabeza.setEnabled(False)
            m.addAction(cabeza)
            for c in cosas[:10]:
                if "reciente" in c:
                    r = c["reciente"]
                    texto = os.path.basename(r.rstrip("\\")) or r
                    m.addAction(texto.replace("&", "&&"), lambda r=r: self._abrir_reciente(e, r))
                else:
                    m.addAction(c["titulo"].replace("&", "&&"), lambda c=c: self._lanzar_tarea(c))
        return bool(grupos)

    def _abrir_reciente(self, e, ruta):
        como = programas.abrir_con(e["exe"], e["ruta"], [ruta])
        try:
            if como and como[0] == "exe":
                subprocess.Popen(como[1], cwd=os.path.dirname(como[1][0]), close_fds=True)
            else:
                os.startfile(ruta)
        except OSError:
            registrar("abrir reciente " + ruta)

    def _lanzar_tarea(self, c):
        r = win.shell32.ShellExecuteW(None, "open", c["ruta"], c["args"] or None, c["carpeta"] or None, 1)
        if r <= 32:
            registrar(f"tarea {c['titulo']}: {r}")

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
        if self._arrastre:
            return
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
        ventanas = [(h, t) for h, t in zip(f["ventanas"], f["titulos"]) if win.user32.IsWindow(h)] if f else []
        if not ventanas:
            if self.previa:
                self.previa.ocultar()
            return
        if not self.previa:
            self.previa = previa.Vista(win.activate, win.close)
        self._previa_desde = time.monotonic()
        pantalla = QGuiApplication.screenAt(QPoint(round(x), round(y))) or self.app.primaryScreen()
        ancho = pantalla.geometry().width() - 24 - (self.alto() if self._get_tema()["vertical"] else 0)
        self.previa.mostrar(clave, ventanas, self.sitio(x, y), ancho, self._get_tema())

    def _quitar_previa(self):
        self._apuntado = None
        self._t_previa.stop()
        if self.previa:
            self.previa.ocultar()

    # ----- atajos de teclado (barra/atajos.py) -----
    seleccion = Property(str, lambda self: self._seleccion, notify=seleccionCambio)

    def _seleccionar(self, que):
        if que != self._seleccion:
            self._seleccion = que
            self.seleccionCambio.emit()

    def _principal(self):
        return next((p for p in self.paneles if p.primaria), None)

    def _hacer_atajo(self, m):
        p = self._principal()
        if not p:
            return
        op = m.get("op")
        if op == "numero":
            self._seleccionar("")
            if m["i"] < len(p.tareas.filas):
                self._atajo_numero(p.tareas.filas[m["i"]], m)
        elif op == "mover":
            b = m["lista"] == "bandeja"
            if b:
                self.abrir_bandeja(True)
            pre, filas = ("b:", self.tray.filas) if b else ("t:", p.tareas.filas)
            claves = [pre + f["key"] for f in filas]
            if claves:
                i = claves.index(self._seleccion) + m["paso"] if self._seleccion in claves else (0 if m["paso"] > 0 else -1)
                self._seleccionar(claves[i % len(claves)])
        elif op in ("pulsar", "menu") and self._seleccion:
            clave, derecho = self._seleccion[2:], op == "menu"
            if self._seleccion.startswith("b:"):
                self.pulsar_bandeja(clave, derecho)
            elif derecho:
                self._menu_elegida(clave)
            else:
                f = self._fila(clave)
                if f:
                    self._atajo_numero(f, {})
            self._seleccionar("")
        else:
            self._seleccionar("")

    def _atajo_numero(self, f, m):
        """Como en Windows: abre, trae al frente, minimiza, o pasa por sus ventanas."""
        self._quitar_previa()
        if m.get("alt"):
            self._seleccionar("t:" + f["key"])        # así se sabe dónde está el botón
            QTimer.singleShot(60, lambda: (self._menu_elegida(f["key"]), self._seleccionar("")))
        elif m.get("mayus"):
            self._abrir(f, "runas" if m.get("ctrl") else "open")
        elif not f["hwnd"]:
            self._abrir(f)
        elif f["cuenta"] > 1 and not m.get("ctrl"):
            vs, activa = f["ventanas"], win.user32.GetForegroundWindow()
            win.activate(vs[(vs.index(activa) + 1) % len(vs)] if activa in vs else int(f["hwnd"]))
        elif f["activa"] and not m.get("ctrl"):
            win.minimize(int(f["hwnd"]))
        else:
            win.activate(int(f["hwnd"]))

    def _menu_elegida(self, clave):
        f, a = self._fila(clave), self._apuntado
        if f:
            self._quitar_previa()
            self._abrir_menu(self._crear_menu_tarea(f), a[1:] if a and a[0] == clave else None)

    # ----- visualizador (barra/cava.py) -----
    cava = Property("QVariantList", lambda self: self._barras, notify=cavaCambio)
    conCava = Property(bool, lambda self: self.ajustes["cava"], notify=temaCambio)

    def _set_cava(self, b):
        if isinstance(b, list) and b != self._barras:
            self._barras = b
            self.cavaCambio.emit()

    def _poner_cava(self, si):
        self.ajustes["cava"] = si
        self._guardar()
        self.temaCambio.emit()
        self.musicaCambio.emit()

    def fps_cava(self):
        """Fotogramas por segundo del visualizador; 0 si ahora no toca."""
        if not (self.ajustes["cava"] and self._cancion["sonando"] and self._animar):
            return 0
        # Sin el visualizador en la barra (concentración, o un tema sin música), ni capturar ni calcular.
        if self._concentrado or not any("musica" in g for grupos in self._get_tema()["modulos"].values() for g in grupos):
            return 0
        return reposo.fps_cava(self.ajustes["animaciones"], self._oculto, self._luz)

    # ----- widgets y tiempo -----
    widgets = Property(bool, lambda self: self.ajustes["widgets"], notify=temaCambio)
    medidores = Property("QVariantList", lambda self: self.ajustes["medidores"], notify=temaCambio)
    medidoresMini = Property(bool, lambda self: self.ajustes["medidores_mini"], notify=temaCambio)

    def _set_medidores_mini(self):
        self.ajustes["medidores_mini"] = not self.ajustes["medidores_mini"]
        self._guardar()
        self.temaCambio.emit()

    def _set_widget(self, cual, diseno):
        """Una fila de la pestaña Widgets: "no" lo apaga; si no, lo enciende con ese diseño."""
        si = diseno != "no"
        llave = {"clima": "widgets", "medidor": "sistema", "cava": "cava"}[cual]
        self.ajustes[llave] = si
        if si:
            self.ajustes["disenos"][cual] = diseno
        self._guardar()
        self.temaCambio.emit()
        self.musicaCambio.emit()
        if cual == "clima":
            self._pedir_tiempo()

    def _set_claudito(self, si):
        self.ajustes["claudito"] = si
        self._guardar()
        self.temaCambio.emit()

    def _set_claudito_modo(self, modo):
        self.ajustes["claudito"] = modo != "no"
        if modo != "no":
            self.ajustes["disenos"]["claudito"] = modo
        self._guardar()
        self.temaCambio.emit()

    def _set_diseno(self, cual, k):
        self.ajustes["disenos"][cual] = k
        self._guardar()
        self.temaCambio.emit()

    def _set_con_oculto(self, cual, llave, k):
        self.ajustes[llave] = k != "no"
        if k != "no":
            self.ajustes["disenos"][cual] = k
        self._guardar()
        self.temaCambio.emit()

    def _set_medidor(self, m):
        a = self.ajustes["medidores"]
        quedan = [x for x in ("cpu", "ram", "gpu") if (x in a) != (x == m)]
        if quedan:                       # al menos uno; para ninguno, «Oculto»
            self.ajustes["medidores"] = quedan
            self._guardar()
            self.temaCambio.emit()

    def _pestana_widgets(self):
        a = self.ajustes

        def fila(cual, encendido):
            actual = a["disenos"].get(cual, "tema") if encendido else "no"
            opciones = {"no": "Oculto", **temas.DISENOS[cual]}
            return [{"texto": n, "elegido": k == actual, "hacer": lambda k=k: self._set_widget(cual, k)} for k, n in opciones.items()]

        def eleccion(cual, por_defecto):
            actual = a["disenos"].get(cual, por_defecto)
            return [{"texto": n, "elegido": k == actual, "hacer": lambda k=k: self._set_diseno(cual, k)}
                    for k, n in temas.DISENOS[cual].items()]

        def con_oculto(cual, llave, por_defecto):
            actual = a["disenos"].get(cual, por_defecto) if a[llave] else "no"
            return [{"texto": n, "elegido": k == actual, "hacer": lambda k=k: self._set_con_oculto(cual, llave, k)}
                    for k, n in {"no": "Oculto", **temas.DISENOS[cual]}.items()]

        filas = [("Tiempo", fila("clima", a["widgets"])),
                 ("CPU, RAM y GPU", fila("medidor", a["sistema"])),
                 ("Música", fila("cava", a["cava"]))]
        if self.claudito.disponible:
            actual = a["disenos"].get("claudito", "tema") if a["claudito"] else "no"
            filas.append(("Claudito", [{"texto": n, "elegido": k == actual, "hacer": lambda k=k: self._set_claudito_modo(k)}
                                       for k, n in {"no": "Oculto", **temas.CLAUDITO}.items()]))
        filas += [("Búsqueda", con_oculto("busqueda", "barra_busqueda", "auto")),
                  ("Icono de búsqueda", eleccion("icono_busqueda", "windows")),
                  ("Vista de tareas", con_oculto("vista", "vista_tareas", "insignia")),
                  ("Icono de vista", eleccion("icono_vista", "windows")),
                  ("Hora y fecha", eleccion("hora", "tema"))]
        medir = [{"texto": n, "marcado": m in a["medidores"], "hacer": lambda m=m: self._set_medidor(m)}
                 for m, n in (("cpu", "CPU"), ("ram", "RAM"), ("gpu", "GPU"))] if a["sistema"] else []
        if medir:
            medir.append({"texto": "Pequeños hasta que pasan del 75 %", "marcado": a["medidores_mini"],
                          "hacer": self._set_medidores_mini})
        return {"titulo": "Widgets", "filas": filas, "interruptores": medir,
                "botones": [{"texto": "Ciudad del tiempo: " + (a["ciudad"].get("nombre") or "elegir…"),
                             "hacer": lambda: QTimer.singleShot(0, self._pedir_ciudad)}]}
    tiempo = Property("QVariantMap", lambda self: {**self._clima, "ciudad": self.ajustes["ciudad"].get("nombre", "")},
                      notify=tiempoCambio)

    def _pedir_tiempo(self):
        c = self.ajustes["ciudad"]
        if self.vista or not c or not self.ajustes["widgets"] or not self._animar or (self._hilo_tiempo and self._hilo_tiempo.is_alive()):
            return

        def pedir():
            try:
                t = tiempo.ahora(c, DATOS)
            except (OSError, ValueError):
                return                  # se queda el último
            if t:
                self._tiempo.emit((c, t))
        self._hilo_tiempo = threading.Thread(target=pedir, daemon=True)
        self._hilo_tiempo.start()

    def _set_tiempo(self, par):
        if par[0] == self.ajustes["ciudad"]:          # no ha cambiado mientras tanto
            self._clima = par[1]
            self.tiempoCambio.emit()

    def _pedir_ciudad(self):
        d = QInputDialog()
        d.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        d.setWindowTitle("Ciudad del tiempo")
        d.setLabelText("Tu ciudad (vacío para no mostrar el tiempo).\nSe consulta en open-meteo.com.")
        d.setTextValue(self.ajustes["ciudad"].get("nombre", ""))
        QTimer.singleShot(0, lambda: win.user32.SetForegroundWindow(int(d.winId())))
        if not d.exec():
            return
        nombre = d.textValue().strip()[:80]
        if not nombre:
            self._set_ciudad({})
            return

        def buscar():
            try:
                self._ciudad.emit(tiempo.buscar_ciudad(nombre, DATOS) or nombre)
            except (OSError, ValueError):
                self._ciudad.emit(nombre)
        threading.Thread(target=buscar, daemon=True).start()

    def _set_ciudad(self, c):
        if isinstance(c, str):
            d = QMessageBox(QMessageBox.Icon.Information, "Ciudad del tiempo", f"No se encontró «{c}», o no hay conexión.")
            d.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
            d.exec()
            return
        self.ajustes["ciudad"] = c
        self._guardar()
        self._clima = dict(tiempo.NADA)
        self.tiempoCambio.emit()
        self._hilo_tiempo = None
        self._pedir_tiempo()

    def _set_widgets(self, si):
        self.ajustes["widgets"] = si
        self._guardar()
        self.temaCambio.emit()
        self._pedir_tiempo()

    def _set_atajos(self, si):
        self.ajustes["atajos"] = si
        self._guardar()
        self.animarCambio.emit()

    # ----- bandeja -----
    def _set_bandeja(self, m):
        if m["op"] == "quitar":
            self._tray.pop(m["key"], None)
        else:
            nombre = "tray-" + m["key"]
            self.almacen.poner_pixeles(nombre, m.pop("pixels"))
            self._tray[m["key"]] = {**m, "icono": self.almacen.url(nombre)}
        self._poner_bandeja()

    @staticmethod
    def _clave_bandeja(v):
        return programas.clave_bandeja(v["exe"], v["guid"], v["tip"])

    def _en_bandeja(self):
        """[(clave del icono, sus datos, si está oculto)], los ocultos primero."""
        out = [(k, v, self._clave_bandeja(v) in self.ajustes["ocultos"])
               for k, v in self._tray.items() if not v["hidden"] and v["icono"]]
        return sorted(out, key=lambda x: not x[2])

    def _poner_bandeja(self):
        todos = self._en_bandeja()
        n = sum(o for _, _, o in todos)
        abierta = self._abierta and n > 0
        self.tray.poner([{"key": k, "icono": v["icono"], "tip": v["tip"] or programas.nombre(v["exe"]), "oculto": o}
                         for k, v, o in todos if abierta or not o])
        if (n, abierta) != (self._ocultos, self._abierta):
            self._ocultos, self._abierta = n, abierta
        self.bandejaCambio.emit()

    ocultos = Property(int, lambda self: self._ocultos, notify=bandejaCambio)
    bandejaAbierta = Property(bool, lambda self: self._abierta, notify=bandejaCambio)

    @Slot(bool)
    def abrir_bandeja(self, si):
        self._abierta = si
        self._poner_bandeja()

    @Slot(str)
    def ocultar_icono(self, clave):
        """Clic central en un icono de la bandeja: lo guarda tras la flecha o lo saca."""
        if clave in self._tray:
            c = self._clave_bandeja(self._tray[clave])
            # Después del clic: el botón pulsado puede desaparecer de la lista.
            QTimer.singleShot(0, lambda: self._ocultar([c], c not in self.ajustes["ocultos"]))

    def _ocultar(self, claves, si):
        resto = [c for c in self.ajustes["ocultos"] if c not in claves]
        self.ajustes["ocultos"] = resto + list(dict.fromkeys(claves)) if si else resto
        self._guardar()
        self._poner_bandeja()

    def _fila_bandeja(self):
        """Los iconos de la bandeja para el menú: los marcados se ven."""
        vistos, out = [], []
        for _, v, oculto in self._en_bandeja():
            c = self._clave_bandeja(v)
            if c in vistos:
                continue
            vistos.append(c)
            n = v["tip"].split("\n")[0] if c.split(":")[0] in programas.GENERICOS and v["tip"] else programas.nombre(v["exe"])
            out.append({"texto": n if len(n) <= 24 else n[:23] + "…", "elegido": not oculto,
                        "hacer": lambda c=c, o=oculto: self._ocultar([c], not o)})
        out.sort(key=lambda x: x["texto"].lower())          # que no salten al pulsarlos
        if out:
            todos = all(not x["elegido"] for x in out)
            out.append({"texto": "Mostrar todos" if todos else "Ocultar todos",
                        "hacer": lambda: self._ocultar(vistos, not todos)})
        return out

    @Slot(str, bool)
    def pulsar_bandeja(self, clave, derecho):
        if clave in self._tray:
            win.tray_click(self._tray[clave], derecho)

    # ----- botones -----
    @Slot(str)
    def accion(self, que):
        if que == "buscador":
            self.abrir_buscador()
            return
        if que == "microfono":
            os.startfile("ms-settings:privacy-microphone")
            return
        teclas = {"inicio": (0x5B,), "buscar": (0x5B, 0x53), "rapidos": (0x5B, 0x41), "avisos": (0x5B, 0x4E), "widgets": (0x5B, 0x57),
                  "menu_inicio": (0x5B, 0x58), "vista": (0x5B, 0x09),
                  "escritorio_nuevo": (0x5B, 0x11, 0x44), "escritorio_sig": (0x5B, 0x11, 0x27), "escritorio_ant": (0x5B, 0x11, 0x25), "silencio": (0xAD,), "menos": (0xAE,), "mas": (0xAF,)}
        if que in teclas:
            win.press(*teclas[que])
            if que in ("silencio", "menos", "mas"):
                QTimer.singleShot(120, self._sistema)
        elif self.musica:
            self.musica.orden(que)

    @Slot(float, float)
    def calendario(self, x, y):
        self._quitar_previa()
        if self._calendario is None:
            self._calendario = calendario.Calendario(lambda: self.accion("avisos"))
        elif self._calendario.isVisible() or time.monotonic() - self._calendario.cerrado < 0.3:
            self._calendario.hide()          # el clic que lo cerró era sobre el reloj
            return
        self._calendario.mostrar(self.sitio(x, y), self._get_tema())

    @Slot()
    def menu(self):
        self._quitar_previa()
        self.claude_salir()
        if self.selector and time.monotonic() - self.selector.cerrado < 0.3:
            return                  # el mismo clic que lo cerró
        QTimer.singleShot(0, self._abrir_selector)

    def _abrir_selector(self):
        if not self.selector:
            self.selector = selector.Selector(self._datos_selector)
        pos = QCursor.pos()
        self.selector.abrir(self.sitio(pos.x(), pos.y()))
        win.user32.SetForegroundWindow(int(self.selector.winId()))

    def _datos_selector(self):
        a, t = self.ajustes, self._get_tema()

        def fila(opciones, actual, poner):
            return [{"texto": n, "elegido": k == actual, "hacer": lambda k=k: poner(k)} for k, n in opciones.items()]

        formato = a["formatos"].get(self._elegido, "tema")

        def formatos(*claves):
            return fila({k: temas.FORMATOS[k] for k in claves}, formato, self._set_formato)

        def marca(texto, valor, poner):
            return {"texto": texto, "marcado": valor, "hacer": lambda: poner(not valor)}

        con_windows = arranque.activo()
        forma = [("Posición", fila(sitio.LADOS, a["posicion"], self._set_posicion)),
                 *([("Opacidad", fila(temas.OPACIDADES, a["opacidad"], self._set_opacidad))] if t["translucida"] else []),
                 *([("Vidrio", fila(vidrio.NOMBRES, a["vidrio"], self._set_vidrio))] if t["vidrio"] else []),
                 ("Animaciones", fila(temas.ANIMACIONES, a["animaciones"], self._set_animaciones)),
                 ("Menús", fila(temas.MENUS, a["menus"], self._set_menus)),
                 ("Esconderse", [{"texto": "Siempre a la vista", "elegido": not a["esconder"], "hacer": lambda: self._set_esconder(False)},
                                 {"texto": "Se esconde sola", "elegido": a["esconder"], "hacer": lambda: self._set_esconder(True)}]),
                 ("# Formato de " + t["nombre"], []),
                 ("Barra", formatos("tema", "completa", "flotante", "compacta")),
                 ("Islas", formatos("islas", "islas_compactas", "esquinas", "burbujas")),
                 ("Una pieza", formatos("isla", "isla_compacta", "pestana")),
                 ("Dock", formatos("dock", "dock_pegado", "dock_mini")),
                 ("# Colores de " + t["nombre"], []),
                 ("Gama", fila(temas.VARIANTES, a["variantes"].get(self._elegido, "tema"), self._set_variante))]
        iconos_ = [("Estilo", fila(iconos.ESTILOS, a["iconos"], self._set_iconos)),
                   ("Alinear", fila(temas.ALINEACIONES, a["alineacion"], self._set_alineacion)),
                   *([("Con varias pantallas", fila(temas.PANTALLAS, a["pantallas"], self._set_pantallas))] if len(self.paneles) > 1 else []),
                   ("Botón de inicio", fila(temas.ICONO, a["icono"], self._set_icono)),
                   *([("Bandeja (visibles)", self._fila_bandeja())] if self._tray else [])]
        return {
            "colores": t["colores"], "fuente": t["fuente"],
            "pestanas": [
                {"titulo": "Temas",
                 "temas": [{"texto": x["nombre"], "marcado": k == self._elegido, "hacer": lambda k=k: self.elegir(k),
                            "mini": os.path.join(x["carpeta"], "miniatura.png")} for k, x in self.temas.items()],
                 "interruptores": [marca("Cambiar de tema según la hora", a["auto"], self._set_auto)]},
                {"titulo": "Forma", "filas": forma,
                 "interruptores": [marca("Como Windows (los temas, solo en el color y un paisaje suave)", a["integrado"], self._set_integrado)],
                 "botones": [{"texto": "Usar este formato en todos los temas", "cierra": False, "hacer": self._formato_para_todos},
                             {"texto": "Usar estos colores en todos los temas", "cierra": False, "hacer": self._variante_para_todos}]},
                {"titulo": "Iconos", "filas": iconos_,
                 "interruptores": [marca("Agrupar ventanas del mismo programa", a["agrupar"], self._set_agrupar)],
                 "botones": [{"texto": "Restablecer el orden de los botones", "cierra": False, "hacer": self._olvidar_orden}] if a["orden"] else []},
                self._pestana_widgets(),
                {"titulo": "Funciones",
                 "interruptores": [marca("Atajos (Win+1…, Win+T, Win+B)", a["atajos"], self._set_atajos),
                                   marca("Modo juego", a["modo_juego"], self._set_juego),
                                   marca("Pincel en la barra", a["pincel"], self._set_pincel),
                                   marca("Isla dinámica (avisos junto a la barra)", a["isla"], self._set_isla),
                                   marca("Buscador (Alt+Espacio o clic central en Inicio)", a["buscador"], self._set_buscador),
                                   marca("Concentrarse durante el pomodoro", a["concentrar_pomodoro"], self._set_concentrar_pomodoro)],
                 "botones": [{"texto": "Dejar de concentrarse" if self._concentrado else "Concentrarse ahora (esconde lo que distrae)",
                              "hacer": lambda: self.concentrarse(not self._concentrado)},
                             {"texto": "Pomodoro: {} min + {} de descanso (cambiar…)".format(*a["pomodoro"]),
                              "hacer": lambda: QTimer.singleShot(0, lambda: self.abrir_buscador("pomodoro "))}] + self._boton_conectar()},
                {"titulo": "General",
                 "interruptores": [{"texto": "Arrancar con Windows", "marcado": con_windows, "hacer": lambda: self._set_arranque(not con_windows)},
                                   *(self.novedades.interruptor() if self.novedades else [])],
                 "botones": (self.novedades.boton() if self.novedades else []) + [
                     {"texto": "Administrador de tareas", "hacer": lambda: win.press(0x11, 0x10, 0x1B)},
                     {"texto": "Configuración de Windows", "hacer": lambda: win.press(0x5B, 0x49)},
                     {"texto": "Salir y volver a la barra de Windows", "hacer": self.app.quit}]}]}

    def _set_agrupar(self, si):
        self.ajustes["agrupar"] = si
        self._guardar()
        self._quitar_previa()
        self.actualizar_ventanas()

    def _set_icono(self, i):
        self.ajustes["icono"] = i
        self._guardar()
        self._actualizar_camaleon(avisar=False)
        self.temaCambio.emit()

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

    def _abrir_menu(self, m, donde=None):
        QTimer.singleShot(0, lambda: win.user32.SetForegroundWindow(int(m.winId())))
        pos, t = QPoint(*map(round, donde)) if donde else QCursor.pos(), m.sizeHint()
        pos = QPoint(*self.sitio(pos.x(), pos.y())(t.width(), t.height()))
        m.exec(pos)

    def _set_auto(self, si):
        self.ajustes["auto"] = si
        self._guardar()
        self._aplicar_tema(self._tema_que_toca())

    # ----- esconderse sola -----
    def _set_esconder(self, si):
        self.ajustes["esconder"] = si
        self._guardar()
        for p in self.paneles:
            p.esconder(si)
            p.fuera_desde = time.monotonic()
        if si and not self.vista:
            self._t_raton.start()
        else:
            self._t_raton.stop()
        self.temaCambio.emit()            # el área de trabajo cambia: la ajusta el reemplazo

    def _algo_abierto(self):
        """Mientras haya algo de la barra abierto, no se esconde."""
        return bool(QApplication.activePopupWidget() or self._arrastre
                    or any(x is not None and x.isVisible() for x in (self.previa, self.selector, self._calendario, self.panel_claude)))

    def _vigilar_raton(self):
        pos = QCursor.pos()
        punto, lado, ahora = (pos.x(), pos.y()), self.ajustes["posicion"], time.monotonic()
        for p in self.paneles:
            zona = p.zona_real()
            if p.escondida:
                if sitio.en_borde(lado, zona, punto):
                    p.esconder(False)
                    p.fuera_desde = ahora
            elif sitio.dentro(zona, punto, 10) or self._algo_abierto():
                p.fuera_desde = ahora
            elif ahora - p.fuera_desde > 0.7:
                p.esconder(True)

    def _set_arranque(self, si):
        arranque.poner(si)
        self.ajustes["arranque"] = "si" if si else "no"
        self._guardar()

    def _vigilar_arranque(self):
        """Si se quería arrancar con Windows y algo quitó la entrada, se vuelve a poner."""
        try:
            querido, puesta = arranque.revisar(self.ajustes["arranque"])
        except OSError:
            registrar("arranque")
            return
        if querido != self.ajustes["arranque"]:
            self.ajustes["arranque"] = querido
            self._guardar()
        if puesta:
            registrar("arranque: la entrada de Run había desaparecido; puesta otra vez")
            self._avisar({"icono": "", "tipo": "info", "titulo": "Arranque con Windows",
                          "detalle": "Algo lo había quitado; ya está otra vez"})

    def _set_juego(self, si):
        self.ajustes["modo_juego"] = si
        self._guardar()
        if not si:
            self._plena.clear()
            for p in self.paneles:
                p.mostrar(True)
            self._animar = True
            self.animarCambio.emit()


class Novedades(QObject):
    """Busca una versión nueva de vez en cuando y la instala en un momento
    tranquilo. Solo en la copia instalada."""
    PRIMERA, CADA = 60_000, 6 * 3600 * 1000
    MIRAR, QUIETO = 15_000, 120         # con una lista: cada cuánto mirar, y segundos sin tocar el equipo
    _lista = Signal(object)

    def __init__(self, barra, version):
        super().__init__(barra)
        self.barra, self.version = barra, version
        self.carpeta = os.path.join(DATOS, "actualizacion")
        self.lista, self._hilo = None, None        # (versión, archivo, SHA-256)
        self._lista.connect(self._poner)
        self._t_buscar = QTimer(self, interval=self.CADA, timeout=self.buscar)
        self._t_mirar = QTimer(self, interval=self.MIRAR, timeout=self._mirar)
        self._t_buscar.start()
        QTimer.singleShot(self.PRIMERA, self.buscar)

    def interruptor(self):
        si = self.barra.ajustes["actualizar"]
        return [{"texto": f"Actualizar sola ({self.version})", "marcado": si, "hacer": lambda: self._activar(not si)}]

    def boton(self):
        return [{"texto": "Actualizar a la " + self.lista[0], "hacer": self.instalar}] if self.lista else []

    def _activar(self, si):
        self.barra.ajustes["actualizar"] = si
        self.barra._guardar()
        if si:
            self.buscar()
        else:
            self.lista = None
            self._t_mirar.stop()

    def buscar(self):
        a = self.barra.ajustes
        if not a["actualizar"] or self.lista or (self._hilo and self._hilo.is_alive()):
            return
        self._hilo = threading.Thread(target=self._descargar, args=(a["intentos"],), daemon=True)
        self._hilo.start()

    def _descargar(self, hechos):
        try:
            hay = actualizar.descargar(self.version, self.carpeta,
                                       saltar=lambda v: actualizar.intentos(hechos, v) >= actualizar.MAX_INTENTOS)
        except actualizar.SinRed:
            return
        except Exception:
            registrar("actualización")
            return
        if hay:
            self._lista.emit(hay)

    def _poner(self, hay):
        if self.barra.ajustes["actualizar"]:
            self.lista = hay
            self._t_mirar.start()

    def _mirar(self):
        b = self.barra
        ocupada = not b._animar or b.arrastrando() or (b.selector and b.selector.isVisible())
        if self.lista and not ocupada and win.segundos_inactivo() >= self.QUIETO:
            self.instalar()

    def instalar(self):
        if not self.lista:
            return
        (version, ruta, suma), self.lista = self.lista, None
        self._t_mirar.stop()
        # Se apunta antes: lo que sigue cierra la barra.
        self.barra.ajustes["intentos"] = actualizar.contar(self.barra.ajustes["intentos"], version)
        self.barra._guardar()
        try:
            actualizar.ejecutar(ruta, suma)
        except Exception:
            registrar("actualización")


class Panel:
    """La barra de una pantalla."""

    def __init__(self, barra, pantalla, primaria):
        self.barra, self.pantalla, self.primaria = barra, pantalla, primaria
        self.tareas = Lista(["key", "titulo", "icono", "activa", "minimizada", "abierta", "hwnd", "exe", "ruta", "cuenta", "atencion"])
        if barra.motor is None:              # uno para todas las pantallas: ahorra unos 15 MB
            barra.motor = QQmlEngine(barra)
            barra.motor.addImageProvider("iconos", Iconos(barra.almacen))
        v = self.view = QQuickView(barra.motor, None)
        v.setFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
                   | Qt.WindowType.WindowDoesNotAcceptFocus | Qt.WindowType.NoDropShadowWindowHint)
        v.setColor(QColor(Qt.GlobalColor.transparent))
        v.setTitle("Barra de temas")
        ctx = self._ctx = QQmlContext(barra.motor.rootContext())
        for nombre, valor in (("barra", barra), ("tareas", self.tareas), ("bandeja", barra.tray)):
            ctx.setContextProperty(nombre, valor)
        ctx.setContextProperty("esPrimaria", primaria)
        self.escondida, self.fuera_desde = bool(barra.ajustes["esconder"]) and not barra.vista, 0.0
        ctx.setContextProperty("oculta", self.escondida)
        v.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        if pantalla:
            v.setScreen(pantalla)
            self.colocar()
            pantalla.geometryChanged.connect(lambda *_: self.colocar())
            barra.temaCambio.connect(self.colocar)
        url = QUrl.fromLocalFile(os.path.join(AQUI, "qml", "Barra.qml"))
        comp = self._comp = QQmlComponent(barra.motor, url)
        raiz = self._raiz = comp.create(ctx)
        self.errores = [e.toString() for e in comp.errors()]
        if raiz is not None:
            v.setContent(url, comp, raiz)

    def colocar(self):
        self.view.setGeometry(QRect(*self.zona_real()))

    def esconder(self, si):
        if si != self.escondida:
            self.escondida = si
            self._ctx.setContextProperty("oculta", si)
            if not self.barra.vista:
                self.barra._ver_inactividad()
            if si:
                self.barra._quitar_previa()

    def pantalla_real(self):
        return win.monitor_of(int(self.view.winId()))

    def zona_real(self):
        """(x, y, ancho, alto) en píxeles, como los da Qt."""
        return sitio.franja(self.barra.ajustes["posicion"], self.pantalla.geometry().getRect(), self.barra.alto())

    def mostrar(self, si, encima=True):
        if self.view.isVisible() != si:
            self.view.setVisible(si)
        elif si and encima:          # otra ventana "siempre encima" pudo taparla
            win.user32.SetWindowPos(win.w.HWND(int(self.view.winId())), win.w.HWND(-1), 0, 0, 0, 0, 0x13)

    def poner_ventanas(self, info, fijos):
        if self.barra.arrastrando():          # no tocar la lista que se está moviendo
            return
        if self.pantalla and len(self.barra.paneles) > 1:
            info = temas.ventanas_de_pantalla(info, self.barra.ajustes["pantallas"], self.primaria, self.pantalla_real())
            if not self.primaria:          # los anclados, solo en la principal
                fijos = []
        fijos = [{**x, "icono": self.barra.almacen.url(self.barra.almacen.de_fijo(x))} for x in fijos]
        self.tareas.poner(programas.agrupar(info, fijos, self.barra.ajustes["agrupar"], self.barra._orden,
                                            self.barra.ajustes["orden"]))


# ---------------------------------------------------------------------------

class Esquinas(QObject):
    """Cada ventanita de la barra (menú, calendario, vistas, buscador, menús de clic derecho) se
    redondea al abrirse como pide «Menús»: con la forma de la barra o como las de Windows."""

    def __init__(self, barra):
        super().__init__(barra)
        self.barra = barra

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow() and not obj.property("sinMarco"):
            try:
                win.esquinas(int(obj.winId()), self.barra.esquinas_menus())
            except Exception:
                registrar("esquinas")
        return False


def lanzar(*args):
    # -I -S: sin paquetes externos, arrancan antes y ocupan menos.
    return subprocess.Popen([sys.executable.replace("pythonw.exe", "python.exe"), "-I", "-S", *args], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                            creationflags=SIN_CONSOLA)


class Reemplazo(QObject):
    """Oculta la barra de Windows mientras el vigilante esté vivo."""

    def __init__(self, barra):
        super().__init__(barra)
        self.barra = barra
        self.activo = True
        self.vigilante = self.tray = self.teclas = self.cava = None
        self._fps = self._fallos_cava = 0
        self._fallos = self._fallos_teclas = 0
        self._timer = QTimer(self, interval=1000, timeout=self.latido)

    def empezar(self):
        self._vigilar()
        self._bandeja()
        self._atajos()
        self.barra.animarCambio.connect(self._atajos)
        for s in (self.barra.musicaCambio, self.barra.animarCambio, self.barra.ritmoCambio):
            s.connect(self._ver_cava)
        self._ver_cava()
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

        threading.Thread(target=self._leer, args=(self.tray, self.barra._bandeja), daemon=True).start()

    def _atajos(self):
        """El proceso de los atajos: en marcha si se quieren, y quieto en modo juego."""
        if not self.activo:
            return
        quiere, vivo = self.barra.ajustes["atajos"], self.teclas is not None and self.teclas.poll() is None
        try:
            if vivo and not quiere:
                self.teclas.stdin.close()
            elif vivo:
                self.teclas.stdin.write("si\n" if self.barra._animar else "no\n")
                self.teclas.stdin.flush()
            elif quiere and self._fallos_teclas <= 2:
                if self.teclas is not None and self.teclas.returncode:
                    self._fallos_teclas += 1
                self.teclas = lanzar(os.path.join(AQUI, "barra", "atajos.py"))
                threading.Thread(target=self._leer, args=(self.teclas, self.barra._atajo), daemon=True).start()
        except (OSError, ValueError):
            pass

    def _ver_cava(self):
        """El proceso del visualizador solo existe mientras hay algo que enseñar."""
        fps = self.barra.fps_cava() if self.activo else 0
        vivo = self.cava is not None and self.cava.poll() is None
        if vivo and fps == self._fps:
            return
        if vivo:
            try:
                self.cava.stdin.close()
            except (OSError, ValueError):
                pass
        self._fps, self.cava = fps, None
        if fps and self._fallos_cava < 4:
            self._fallos_cava += 1               # se perdona si aguanta
            self.cava = proc = lanzar(os.path.join(AQUI, "barra", "cava.py"), str(fps))
            QTimer.singleShot(10_000, lambda: self._perdonar_cava(proc))

            def leer():
                for linea in proc.stdout:
                    if proc is self.cava:
                        try:
                            self.barra._cava.emit(json.loads(linea))
                        except (ValueError, RuntimeError):
                            pass
            threading.Thread(target=leer, daemon=True).start()
        elif not fps:
            self.barra._set_cava([0] * 16)

    def _perdonar_cava(self, proc):
        if proc.poll() is None or proc is not self.cava:
            self._fallos_cava = 0

    @staticmethod
    def _leer(proc, aviso):
        for linea in proc.stdout:
            try:
                aviso.emit(json.loads(linea))
            except (ValueError, RuntimeError):
                pass

    def latido(self):
        if not self.activo:
            return
        if self.cava is not None and self.cava.poll() is not None:
            self._ver_cava()
        if self.barra.ajustes["atajos"] and self.teclas is not None and self.teclas.poll() is not None:
            self._atajos()
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
        """El sitio libre para las ventanas, según dónde esté la barra."""
        if self.activo:
            lado, grosor = self.barra.ajustes["posicion"], 0 if self.barra.ajustes["esconder"] else self.barra.alto()
            # Abajo y en tamaño normal, justo el hueco que ya reserva Windows.
            win.ajustar_area(None if (lado, grosor) == ("abajo", ALTO) else sitio.margenes(lado, grosor))
            win.recolocar_encajadas()

    def parar(self):
        if not self.activo:
            return                  # ya se paró
        self.activo = False
        self._timer.stop()
        for p in (self.cava, self.teclas, self.tray, self.vigilante):
            try:
                if p is self.vigilante:
                    p.stdin.write("adios\n")      # cierre a propósito: que no la reabra
                    p.stdin.flush()
                p.stdin.close()
                p.wait(3)
            except (OSError, ValueError, subprocess.TimeoutExpired, AttributeError):
                pass
        win.show_taskbars()


def preparar_vista(app, todo=False):
    """Una barra con datos de ejemplo, fuera de la pantalla."""
    barra = Barra(app, vista=True)
    barra._datos = {"cpu": 23, "ram": 58, "gpu": 41, "volumen": 64, "silencio": False,
                    "historia": {"cpu": [12, 18, 35, 22, 60, 41, 30, 23], "ram": [55, 56, 58, 57, 58],
                                 "gpu": [10, 80, 72, 35, 41]},
                    "red": red.glifo_red({"tipo": "wifi", "internet": True, "senal": 80}), "redTexto": "Wi-Fi (80 %)",
                    "bateria": red.glifo_bateria(70, False), "bateriaPct": 70, "cargando": False}
    barra._cancion = {"titulo": "Canción de ejemplo", "artista": "Artista", "sonando": True}
    barra._titulo = "Documento sin título - Bloc de notas"
    barra._clima = {"hay": True, "icono": "🌤️", "grados": "22°", "texto": "Poco nuboso", "tipo": "parcial", "noche": False}
    barra.ajustes["widgets"] = barra.ajustes["cava"] = True
    barra._apariencia = (False, "", "")          # igual en todos los equipos
    barra._barras = [35, 62, 88, 100, 81, 66, 74, 52, 60, 43, 38, 49, 30, 24, 17, 10]
    barra._leer_ropa()
    barra._claude = {"modo": "idle", "texto": "Construyendo…"}
    exes = [os.path.join(os.environ["WINDIR"], n) for n in ("explorer.exe", "notepad.exe", "regedit.exe")]
    g = app.primaryScreen().geometry()
    barra.fondo.zonas = [(g.x(), g.y() + g.height() - ALTO, g.width(), ALTO)]
    barra.fondo.leer()
    panel = Panel(barra, None, True)
    panel.tareas.poner([{"key": str(i), "titulo": os.path.basename(e), "activa": i == 1, "minimizada": False,
                         "icono": barra.almacen.url(barra.almacen.de_archivo(e)), "abierta": i != 2, "cuenta": (3, 1, 0)[i], "clave": e, "hwnd": "",
                         "exe": e, "ruta": ""} for i, e in enumerate(exes)])
    barra.tray.poner([{"key": e, "icono": barra.almacen.url(barra.almacen.de_archivo(e)), "tip": e} for e in exes])
    panel.view.setGeometry(-6000, -6000, 1920, ALTO)
    panel.view.show()
    for e in panel.errores:
        print("QML:", e)
    casos = [(t, f, a, "dia", p) for p in ("arriba", "izquierda", "derecha") for t in barra.temas
             for f in ("tema", "islas_compactas", "completa", "isla") for a in ("centro", "izquierda")] if todo else []
    casos += [(t, f, a, m, "abajo") for t in barra.temas for f in ("tema", "islas_compactas", "isla", "isla_compacta", "flotante", "pestana", "dock", "dock_pegado", "dock_mini", "esquinas", "burbujas")
              for a in ("izquierda", "centro")
             for m in (cielo.MOMENTOS if barra.temas[t]["momentos"] and (f, a) == ("tema", "centro") else ("dia",))]
    return barra, panel, casos


def hacer_vista(app, carpeta):
    """Una imagen por tema, formato, posición y momento."""
    os.makedirs(carpeta, exist_ok=True)
    barra, panel, casos = preparar_vista(app, todo=True)
    g = app.primaryScreen().geometry()

    def siguiente(i):
        if i:
            img = panel.view.grabWindow()
            vertical = casos[i - 1][4] in sitio.VERTICALES
            fondo = QImage(img.width(), img.height() + (0 if vertical else 72 - img.height()), QImage.Format.Format_RGB32)
            fondo.fill(QColor("#4A6B8A"))
            p = QPainter(fondo)
            _, f = barra.fondo.franja(g.x() + 1, g.y() + g.height() - 2)
            if f and not vertical:
                p.drawImage(QPoint(0, fondo.height() - f["nitida"].height()), f["nitida"])
            p.drawImage(QPoint(0, fondo.height() - img.height()), img)
            p.end()
            fondo.save(os.path.join(carpeta, "-".join(casos[i - 1]) + ".png"))
        if i == len(casos):
            app.quit()
            return
        barra.ajustes["formatos"] = {casos[i][0]: casos[i][1]}
        barra.ajustes["alineacion"] = casos[i][2]
        barra._poner_momento(casos[i][3])
        barra.ajustes["posicion"] = casos[i][4]
        n = barra.alto()
        panel.view.setGeometry(-6000, -6000, *((n, 1080) if casos[i][4] in sitio.VERTICALES else (1920, n)))
        barra._aplicar_tema(casos[i][0])
        QTimer.singleShot(900, lambda: siguiente(i + 1))

    siguiente(0)
    app.exec()


def hacer_miniaturas(app):
    """Guarda temas/<tema>/miniatura.png, con fondo transparente."""
    barra, panel, casos = preparar_vista(app)
    barra.tray.poner([])
    ids = list(barra.temas)

    def siguiente(i):
        if i:
            img = panel.view.grabWindow().convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
            trozos = ((0, 88), (850, 220), (1690, 230))
            mini = QImage(sum(an for _, an in trozos), ALTO, QImage.Format.Format_ARGB32_Premultiplied)
            mini.fill(Qt.GlobalColor.transparent)
            p, x = QPainter(mini), 0
            for x0, an in trozos:
                p.drawImage(QPoint(x, 0), img, QRect(x0, 0, an, ALTO))
                x += an
            p.end()
            mini.save(os.path.join(barra.temas[ids[i - 1]]["carpeta"], "miniatura.png"))
        if i == len(ids):
            app.quit()
            return
        barra._elegido = ids[i]
        barra.ajustes.update(formatos={}, alineacion="centro", icono="tema", posicion="abajo")
        barra._momento = "dia"
        barra._aplicar_tema(ids[i])
        QTimer.singleShot(1200, lambda: siguiente(i + 1))

    siguiente(0)
    app.exec()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vista")
    ap.add_argument("--segundos", type=int)
    ap.add_argument("--miniaturas", action="store_true")
    args = ap.parse_args()
    os.makedirs(DATOS, exist_ok=True)
    # Dibuja con el procesador: son 48 px de alto y así no le quita nada a los juegos.
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)
    QQuickStyle.setStyle("Basic")
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    vidrio.registrar_tipo()
    if args.miniaturas:
        hacer_miniaturas(app)
        return 0
    if args.vista:
        hacer_vista(app, args.vista)
        return 0
    candado = QLockFile(os.path.join(DATOS, "barra.lock"))
    if not candado.tryLock(100):
        return 1
    anotar_errores()
    with open(os.path.join(DATOS, "pid.json"), "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid()}, f)
    for aviso in ("parar", "recargar"):       # eran para la anterior: si esta se cae, que se reabra
        try:
            os.remove(os.path.join(DATOS, aviso))
        except OSError:
            pass
    limite = time.monotonic() + 60
    while not win.taskbars() and time.monotonic() < limite:      # recién iniciada la sesión
        time.sleep(0.5)
    barra = Barra(app)
    esquinas = Esquinas(barra)
    app.installEventFilter(esquinas)
    for s in app.screens():
        barra.paneles.append(Panel(barra, s, s == app.primaryScreen()))
    errores = [e for p in barra.paneles for e in p.errores]
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
    version = actualizar.version_instalada()
    if version:
        barra.novedades = Novedades(barra, version)
    if args.segundos:
        QTimer.singleShot(args.segundos * 1000, app.quit)
    try:
        return app.exec()
    finally:
        reemplazo.parar()
        try:
            os.remove(os.path.join(DATOS, "pid.json"))      # ese número puede acabar siendo de otro
        except OSError:
            pass


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        registrar("la barra se cerró")
        raise
