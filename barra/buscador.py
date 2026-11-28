"""El buscador: Alt+Espacio (o clic central en Inicio) y escribir.

Busca en las aplicaciones del menú Inicio (barra/apps.py), en páginas de
Configuración y hace cuentas. Lo que no encuentra se puede buscar en los
archivos con el Explorador. Todo es local: no se conecta a nada.
"""
import ast
import ctypes
import math
import operator
import os
import re
import time
import unicodedata
from ctypes import wintypes as w

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QImage, QPainter, QPen
from PySide6.QtWidgets import QLineEdit, QWidget

from . import atencion, win

ANCHO, CABEZA, FILA, MAX, MARGEN = 560, 56, 44, 8, 10
# Una sola rejilla para la cabecera y las filas: la lupa y los iconos en la misma
# columna, lo que se escribe y los nombres empezando en la misma x.
COL_ICONO, LADO, COL_TEXTO = 22, 24, 60

# Páginas de Configuración: (nombre, dirección, otras palabras con las que buscarla).
AJUSTES = [
    ("Pantalla", "ms-settings:display", "resolución brillo escala monitor hdr"),
    ("Sonido", "ms-settings:sound", "volumen altavoces micrófono audio"),
    ("Bluetooth y dispositivos", "ms-settings:bluetooth", "auriculares mando emparejar"),
    ("Wi-Fi", "ms-settings:network-wifi", "red inalámbrica internet"),
    ("Red e Internet", "ms-settings:network", "ethernet conexión vpn proxy"),
    ("Fondo de escritorio", "ms-settings:personalization-background", "fondo pantalla wallpaper imagen"),
    ("Colores", "ms-settings:colors", "modo oscuro claro acento tema"),
    ("Barra de tareas", "ms-settings:taskbar", "ocultar automáticamente"),
    ("Aplicaciones instaladas", "ms-settings:appsfeatures", "desinstalar programas"),
    ("Aplicaciones de inicio", "ms-settings:startupapps", "arranque arrancar con windows"),
    ("Aplicaciones predeterminadas", "ms-settings:defaultapps", "navegador abrir con"),
    ("Windows Update", "ms-settings:windowsupdate", "actualizaciones actualizar"),
    ("Energía y batería", "ms-settings:powersleep", "suspender apagar pantalla batería"),
    ("Almacenamiento", "ms-settings:storagesense", "disco espacio liberar"),
    ("Notificaciones", "ms-settings:notifications", "avisos no molestar"),
    ("Ratón", "ms-settings:mousetouchpad", "mouse puntero velocidad"),
    ("Teclado", "ms-settings:typing", "escritura idioma distribución"),
    ("Hora e idioma", "ms-settings:dateandtime", "fecha reloj zona horaria"),
    ("Privacidad y seguridad", "ms-settings:privacy", "permisos cámara ubicación"),
    ("Seguridad de Windows", "windowsdefender:", "antivirus defender firewall"),
    ("Juegos", "ms-settings:gaming-gamebar", "game bar grabación"),
    ("Gráficos", "ms-settings:display-advancedgraphics", "gpu preferencia rendimiento"),
    ("Cuentas", "ms-settings:yourinfo", "usuario inicio de sesión contraseña"),
    ("Accesibilidad", "ms-settings:easeofaccess", "lupa contraste narrador"),
    ("Configuración", "ms-settings:", "ajustes opciones"),
]


def normalizar(texto):
    """Minúsculas y sin tildes: "Música" y "musica" son lo mismo."""
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(ch for ch in t if unicodedata.category(ch) != "Mn")


def puntuar(consulta, nombre, extra=""):
    """De 0 (nada) a 100 (igual). `consulta` ya normalizada."""
    if not consulta:
        return 0
    n = normalizar(nombre)
    if n == consulta:
        return 100
    if n.startswith(consulta):
        return 90
    palabras = n.replace("-", " ").replace(".", " ").split()
    if any(p.startswith(consulta) for p in palabras):
        return 80
    if len(consulta) >= 2 and "".join(p[0] for p in palabras if p).startswith(consulta):
        return 72                    # iniciales: "vsc" -> Visual Studio Code
    if consulta in n:
        return 60
    if extra and any(p.startswith(consulta) for p in normalizar(extra).split()):
        return 55
    i = 0
    for ch in n:                     # las letras en orden, con huecos
        if i < len(consulta) and ch == consulta[i]:
            i += 1
    return 30 if i == len(consulta) and len(consulta) >= 3 else 0


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
        ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCIONES = {"sqrt": math.sqrt, "raiz": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
              "log": math.log10, "ln": math.log, "abs": abs, "round": round}
_CONSTANTES = {"pi": math.pi, "e": math.e}


_UNIDADES = {"h": 3600, "hora": 3600, "horas": 3600, "m": 60, "min": 60, "mins": 60, "minuto": 60,
             "minutos": 60, "s": 1, "seg": 1, "segs": 1, "segundo": 1, "segundos": 1}
# El menú de ajustes también con teclado (WCAG 2.1.1): Alt+Espacio y «ajustes».
_PALABRAS_AJUSTES = ("ajustes", "ajustes de la barra", "configurar la barra", "menu de la barra", "temas de la barra")
_PALABRAS_CONCENTRAR = ("concentracion", "concentrarse", "concentrar", "foco", "focus", "no molestar")
_PALABRAS_TEMPORIZADOR = ("temporizador", "timer", "alarma", "cuenta atras", "avisame en", "avisar en")


def duracion(segundos):
    """90 → "1 min 30 s"; 5400 → "1 h 30 min"."""
    h, resto = divmod(int(segundos), 3600)
    m, s = divmod(resto, 60)
    return " ".join(f"{n} {u}" for n, u in ((h, "h"), (m, "min"), (s, "s")) if n) or "0 s"


def temporizador(texto, pomodoro=(25, 5)):
    """{"segundos", "pomodoro"} (y "descanso" en un pomodoro) si `texto` pide un temporizador, o None.
    «temporizador 10» (minutos), «5 min», «1h 30m», «90 s», «alarma 2 horas»; «pomodoro» con los minutos
    de `pomodoro` (trabajo, descanso), o con otros: «pomodoro 50», «pomodoro 50/10», «pomodoro 50 10»."""
    t = normalizar(texto.strip())
    p = re.fullmatch(r"pomodoro(?:\s+(\d{1,3})\s*(?:m|min|minutos)?(?:\s*[/+y,]?\s*(\d{1,2})\s*(?:m|min|minutos)?)?)?", t)
    if p:
        trabajo = int(p.group(1)) if p.group(1) else pomodoro[0]
        descanso = int(p.group(2)) if p.group(2) else pomodoro[1]
        if not (1 <= trabajo <= 180 and 0 <= descanso <= 60):
            return None
        return {"segundos": trabajo * 60, "pomodoro": True, "descanso": descanso * 60}
    palabra = next((p for p in _PALABRAS_TEMPORIZADOR if t.startswith(p)), "")
    resto = t[len(palabra):].strip()
    if palabra and re.fullmatch(r"\d+(?:[.,]\d+)?", resto):
        resto += " min"                          # «temporizador 10»: minutos
    partes = re.findall(r"(\d+(?:[.,]\d+)?)\s*([a-z]+)", resto)
    if not partes or re.sub(r"[\d.,\sa-z]", "", resto) or "".join(n + u for n, u in partes) != resto.replace(" ", ""):
        return None
    total = 0
    for n, u in partes:
        if u not in _UNIDADES:
            return None
        total += float(n.replace(",", ".")) * _UNIDADES[u]
    total = round(total)
    return {"segundos": total, "pomodoro": False} if 0 < total <= 24 * 3600 else None


def calcular(texto):
    """El resultado de una cuenta como "2*(3+4)" o "15% de 80", o None si no lo es."""
    t = texto.strip().lower().replace(",", ".").replace("x", "*").replace("×", "*").replace("÷", "/").replace("^", "**")
    if " de " in t and t.split(" de ")[0].strip().endswith("%"):
        a, b = t.split(" de ", 1)
        t = f"({a.strip()[:-1]})/100*({b})"
    if not any(ch.isdigit() for ch in t) or not any(ch in t for ch in "+-*/%()") and not any(f in t for f in _FUNCIONES):
        return None
    try:
        arbol = ast.parse(t, mode="eval")
    except SyntaxError:
        return None

    def valor(n):
        if isinstance(n, ast.Expression):
            return valor(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.Name) and n.id in _CONSTANTES:
            return _CONSTANTES[n.id]
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            a, b = valor(n.left), valor(n.right)
            if isinstance(n.op, ast.Pow) and abs(b) > 100:
                raise ValueError("demasiado grande")
            return _OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](valor(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCIONES and len(n.args) == 1:
            return _FUNCIONES[n.func.id](valor(n.args[0]))
        raise ValueError("no es una cuenta")

    try:
        r = valor(arbol)
    except (ValueError, ZeroDivisionError, OverflowError, TypeError):
        return None
    if isinstance(r, float):
        if math.isnan(r) or math.isinf(r):
            return None
        r = round(r, 10)
        if r.is_integer() and abs(r) < 1e15:
            r = int(r)
    return f"{r:,}".replace(",", " ") if isinstance(r, int) else f"{r:.10g}"


def resultados(texto, apps, usos=None, ventanas=(), pomodoro=(25, 5)):
    """Lo que se enseña para `texto`: [{"tipo", "nombre", "detalle", ...}], lo mejor primero.
    `ventanas`: las abiertas, [{"id" (hwnd), "nombre" (el programa), "titulo", "icono"}]."""
    usos = usos or {}
    consulta = normalizar(texto.strip())
    out = []
    tiempo = temporizador(texto, pomodoro)
    if tiempo:
        if tiempo["pomodoro"]:
            d = tiempo["descanso"] // 60
            nombre = f"Pomodoro: {tiempo['segundos'] // 60} min" + (f" y {d} de descanso" if d else ", sin descanso")
        else:
            nombre = "Temporizador de " + duracion(tiempo["segundos"])
        out.append({"tipo": "temporizador", **tiempo, "detalle": "Intro: empezar", "nombre": nombre})
    if len(consulta) >= 3 and any(p.startswith(consulta) or consulta.startswith(p) for p in _PALABRAS_AJUSTES):
        out.append({"tipo": "ajustes_barra", "nombre": "Ajustes de la barra", "detalle": "Intro: abrir"})
    if consulta and any(p.startswith(consulta) or consulta.startswith(p) for p in _PALABRAS_CONCENTRAR) and len(consulta) >= 3:
        out.append({"tipo": "concentracion", "nombre": "Modo concentración", "detalle": "Intro: activar o quitar"})
    cuenta = calcular(texto)
    if cuenta is not None:
        out.append({"tipo": "cuenta", "nombre": "= " + cuenta, "detalle": "Intro: copiar", "valor": cuenta.replace(" ", "")})
    if not consulta:
        recientes = sorted((a for a in apps if usos.get(a["id"])), key=lambda a: -usos[a["id"]])[:MAX]
        return [{"tipo": "app", **a, "detalle": "Usada a menudo"} for a in recientes]
    puestos = []
    for a in apps:
        p = puntuar(consulta, a["nombre"])
        if p:
            puestos.append((p + min(15, 3 * usos.get(a["id"], 0)), {"tipo": "app", **a, "detalle": "Aplicación"}))
    for v in ventanas:                        # ir a una abierta va antes que abrir otra
        p = max(puntuar(consulta, v["nombre"]), puntuar(consulta, v["titulo"]) - 5)
        if p:
            puestos.append((p + 8, {"tipo": "ventana", "id": v["id"], "icono": v.get("icono", ""),
                                    "nombre": v["titulo"] or v["nombre"], "detalle": "Ventana abierta"}))
    for nombre, uri, extra in AJUSTES:
        p = puntuar(consulta, nombre, extra)
        if p:
            puestos.append((p - 5, {"tipo": "ajuste", "nombre": nombre, "id": uri, "detalle": "Configuración"}))
    if sum(1 for p, _ in puestos if p >= 50) >= 3:          # con bastantes de verdad, sin las de letras sueltas
        puestos = [x for x in puestos if x[0] >= 50]
    puestos.sort(key=lambda x: (-x[0], len(x[1]["nombre"]), x[1]["nombre"]))
    out = (out + [r for _, r in puestos])[:MAX - 1]
    out.append({"tipo": "archivos", "nombre": f"Buscar «{texto.strip()}» en los archivos", "detalle": "Explorador",
                "id": texto.strip()})
    return out


def abrir(r):
    """Hace lo que toca con un resultado. Devuelve True si hay que cerrar el buscador."""
    if r["tipo"] == "cuenta":
        QGuiApplication.clipboard().setText(r["valor"])
    elif r["tipo"] == "ventana":
        win.activate(int(r["id"]))
    elif r["tipo"] == "app":
        os.startfile("shell:AppsFolder\\" + r["id"])
    elif r["tipo"] == "ajuste":
        os.startfile(r["id"])
    elif r["tipo"] == "archivos":
        carpeta = os.path.expanduser("~")
        consulta = r["id"].replace("&", " ").replace("%", " ")
        os.startfile(f"search-ms:query={consulta}&crumb=location:{carpeta}")
    return True


class Atajo:
    """Alt+Espacio con RegisterHotKey en una ventana invisible propia: sin ganchos de teclado."""

    def __init__(self, al_pulsar, mods=0x1 | 0x4000, tecla=0x20):        # MOD_ALT | MOD_NOREPEAT, VK_SPACE
        self._al_pulsar, self._mods, self._tecla = al_pulsar, mods, tecla
        self._proc = atencion.WNDPROC(self._wndproc)
        inst = atencion.kernel32.GetModuleHandleW(None)
        wc = atencion.WNDCLASSW(lpfnWndProc=self._proc, hInstance=inst, lpszClassName="BarraTemasBuscador")
        atencion.user32.RegisterClassW(ctypes.byref(wc))
        self.hwnd = atencion.user32.CreateWindowExW(0x80, "BarraTemasBuscador", "", 0x80000000, 0, 0, 0, 0,
                                                    None, None, inst, None)
        self.activo = False

    def poner(self, si):
        """Registra o suelta el atajo (se suelta en modo juego). Devuelve si está puesto."""
        u = atencion.user32
        if si and not self.activo and self.hwnd:
            self.activo = bool(u.RegisterHotKey(w.HWND(self.hwnd), 1, self._mods, self._tecla))
        elif not si and self.activo:
            u.UnregisterHotKey(w.HWND(self.hwnd), 1)
            self.activo = False
        return self.activo

    def _wndproc(self, hwnd, msg, wp, lp):
        if msg == 0x312:             # WM_HOTKEY
            try:
                self._al_pulsar()
            except Exception:
                pass
            return 0
        return atencion.user32.DefWindowProcW(hwnd, msg, wp, lp)

    def cerrar(self):
        self.poner(False)
        if self.hwnd:
            atencion.user32.DestroyWindow(self.hwnd)
            self.hwnd = None


def encajar(img, lado):
    """Quita el borde transparente de `img` y la escala (sin deformar) para que quepa en lado×lado.

    Cada programa trae su icono con un margen distinto; sin esto unos se ven
    grandes, otros pequeños y otros desplazados dentro de su hueco.
    """
    img = img.convertToFormat(QImage.Format.Format_ARGB32)
    an, al, paso = img.width(), img.height(), img.bytesPerLine()
    alfa = bytes(img.constBits())[3::4] if paso == an * 4 else bytes(an * al)
    filas = [y for y in range(al) if max(alfa[y * an:(y + 1) * an]) > 24]
    if filas:
        cols = [x for x in range(an) if max(alfa[x::an]) > 24]
        img = img.copy(cols[0], filas[0], cols[-1] - cols[0] + 1, filas[-1] - filas[0] + 1)
    return img.scaled(lado, lado, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


class Buscador(QWidget):
    def __init__(self, icono, al_usar):
        """`icono(r)` da la QImage de un resultado (o None); `al_usar(r)` apunta lo que se abre."""
        super().__init__(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self._icono, self._al_usar = icono, al_usar
        self.apps, self.usos, self.ventanas, self.pomodoro = [], {}, [], (25, 5)
        self._res, self._sel, self._encima = [], 0, -1
        self._col, self._fuente = {}, "Segoe UI"
        self.cerrado = 0.0
        self._encajados = {}
        self.entrada = QLineEdit(self)
        self.entrada.setFrame(False)
        self.entrada.setPlaceholderText("Buscar aplicaciones, configuración, cuentas…")
        self.entrada.textChanged.connect(self._buscar)
        self.entrada.installEventFilter(self)
        self.setMouseTracking(True)

    # ----- abrir y cerrar -----
    def mostrar(self, poner, tema, apps, usos, ventanas=(), pomodoro=(25, 5), texto="", escala=1.0):
        """`texto`: con qué empieza escrito (el menú abre «pomodoro » para cambiar sus minutos).
        `escala`: el «Tamaño del texto» de Windows; crece todo junto (WCAG 1.4.4)."""
        self.apps, self.usos, self.ventanas, self.pomodoro = apps, usos, list(ventanas), tuple(pomodoro)
        self._col, self._fuente = tema["colores"], tema["fuente"]
        self._esc = max(1.0, min(2.0, escala))
        c = self._col
        f = QFont(self._fuente)
        f.setPixelSize(round(17 * self._esc))
        self.entrada.setFont(f)
        self.entrada.setStyleSheet(f"QLineEdit {{ background: transparent; color: {c['texto']}; "
                                   f"selection-background-color: {c['acento']}; }}")
        self._poner = poner
        self.entrada.setText(texto)              # dispara la búsqueda si cambia
        self._buscar(texto)
        self.show()
        self.raise_()
        atencion.user32.SetForegroundWindow(int(self.winId()))
        self.activateWindow()
        self.entrada.setFocus()

    def poner_apps(self, apps):
        """La lista llegó (o cambió) con el buscador abierto."""
        if apps == self.apps:
            return                               # igual que antes: no mover lo que ya se ha elegido
        self.apps = apps
        if self.isVisible():
            self._buscar(self.entrada.text())

    def hideEvent(self, e):
        self.cerrado = time.monotonic()
        super().hideEvent(e)

    def _alto(self):
        return CABEZA + (len(self._res) * FILA + MARGEN if self._res else 0)

    def _buscar(self, texto):
        self._res = resultados(texto, self.apps, self.usos, self.ventanas, self.pomodoro) if (texto.strip() or self.usos) else []
        if not texto.strip() and not self.apps:
            self._res = [{"tipo": "nada", "nombre": "Leyendo las aplicaciones…", "detalle": ""}]
        self._sel, self._encima = 0, -1
        esc = getattr(self, "_esc", 1.0)
        an, al = round(ANCHO * esc), round(self._alto() * esc)
        x, y = self._poner(an, al)
        self.setGeometry(QRect(x, y, an, al))
        # QLineEdit deja 2 px por dentro antes del texto.
        self.entrada.setGeometry(round((COL_TEXTO - 2) * esc), 0, round((ANCHO - COL_TEXTO - 16) * esc), round(CABEZA * esc))
        self.update()

    def _usar(self, i):
        if not (0 <= i < len(self._res)) or self._res[i]["tipo"] == "nada":
            return
        r = self._res[i]
        self.hide()
        try:
            abrir(r)
            self._al_usar(r)
        except OSError:
            pass

    # ----- teclado y ratón -----
    def eventFilter(self, obj, e):
        if obj is self.entrada and e.type() == e.Type.KeyPress:
            k = e.key()
            if k == Qt.Key.Key_Escape:
                self.hide()
                return True
            if k in (Qt.Key.Key_Down, Qt.Key.Key_Tab):
                self._mover(1)
                return True
            if k in (Qt.Key.Key_Up, Qt.Key.Key_Backtab):
                self._mover(-1)
                return True
            if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._usar(self._sel)
                return True
        return super().eventFilter(obj, e)

    def _mover(self, paso):
        if self._res:
            self._sel = (self._sel + paso) % len(self._res)
            self.update()

    def _fila(self, pos):
        y = pos.y() / getattr(self, "_esc", 1.0) - CABEZA
        i = int(y // FILA) if y >= 0 else -1
        return i if 0 <= i < len(self._res) else -1

    def mouseMoveEvent(self, e):
        i = self._fila(e.position())
        if i != self._encima:
            self._encima = i
            if i >= 0:
                self._sel = i
            self.update()

    def mousePressEvent(self, e):
        if not self.rect().contains(e.position().toPoint()):
            self.hide()
            return
        i = self._fila(e.position())
        if i >= 0 and e.button() == Qt.MouseButton.LeftButton:
            self._usar(i)

    # ----- dibujo -----
    def _encajado(self, r):
        """El icono del resultado sin su margen transparente y escalado a LADO, o None."""
        clave = (r["tipo"], r.get("id") or r["nombre"])
        if clave not in self._encajados:
            img = self._icono(r)
            self._encajados[clave] = encajar(img, LADO) if isinstance(img, QImage) and not img.isNull() else None
        return self._encajados[clave]

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        esc = getattr(self, "_esc", 1.0)
        p.scale(esc, esc)
        todo = QRect(0, 0, ANCHO, self._alto())
        c = {k: QColor(v) for k, v in self._col.items() if v}
        fondo = QColor(c.get("fondo", QColor("#202020")))
        fondo.setAlpha(255)
        p.fillRect(todo, fondo)
        p.setPen(QPen(c["acento"]))
        p.drawRect(todo.adjusted(0, 0, -1, -1))
        # La lupa, a la izquierda de lo que se escribe.
        lupa = QFont("Segoe Fluent Icons")
        lupa.setPixelSize(16)
        p.setFont(lupa)
        p.setPen(c.get("tenue", c["texto"]))
        p.drawText(QRectF(16, 0, 26, CABEZA), Qt.AlignmentFlag.AlignCenter, "")
        if self._res:
            p.setPen(QPen(c.get("borde", c["acento"])))
            p.drawLine(12, CABEZA - 1, ANCHO - 12, CABEZA - 1)
        f, peq = QFont(self._fuente), QFont(self._fuente)
        f.setPixelSize(14)
        peq.setPixelSize(11)
        for i, r in enumerate(self._res):
            y = CABEZA + i * FILA + MARGEN / 2
            caja = QRectF(6, y, ANCHO - 12, FILA - 4)
            if i == self._sel and r["tipo"] != "nada":
                encima = QColor(c.get("encima", c["acento"]))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(encima)
                p.drawRoundedRect(caja, 6, 6)
                p.setBrush(c["acento"])
                p.drawRoundedRect(QRectF(caja.left(), caja.top() + 10, 3, caja.height() - 20), 1.5, 1.5)
            icono = QRectF(COL_ICONO, caja.center().y() - LADO / 2, LADO, LADO)
            img = self._encajado(r)
            if img is not None:
                p.drawImage(QRectF(icono.center().x() - img.width() / 2, icono.center().y() - img.height() / 2,
                                   img.width(), img.height()), img)
            else:
                g = QFont("Segoe Fluent Icons")
                g.setPixelSize(20)
                p.setFont(g)
                p.setPen(c["acento"])
                p.drawText(icono, Qt.AlignmentFlag.AlignCenter,
                           {"temporizador": "", "cuenta": "", "ajuste": "", "archivos": "", "ventana": ""}.get(r["tipo"], {"concentracion": "", "ajustes_barra": ""}.get(r["tipo"], "")))
            texto = QRectF(COL_TEXTO, caja.top(), caja.right() - 140 - COL_TEXTO, caja.height())
            p.setFont(f)
            p.setPen(c["texto"])
            p.drawText(texto, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       QFontMetrics(f).elidedText(r["nombre"], Qt.TextElideMode.ElideRight, int(texto.width())))
            if r.get("detalle"):
                p.setFont(peq)
                p.setPen(c.get("tenue", c["texto"]))
                p.drawText(QRectF(caja.right() - 130, caja.top(), 118, caja.height()),
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, r["detalle"])
        p.end()
