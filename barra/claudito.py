"""Claudito en la barra. Solo lee: usa su lógica de estados y su dibujo desde
~/src/claudito, sin cambiar nada allí. Si no está, la barra va sin él."""
import importlib.util
import json
import os
import shutil
import sys
import time
import winreg

RAIZ = os.path.join(os.path.expanduser("~"), "src", "claudito")
PERSONAJE = os.path.join(RAIZ, "plasma", "org.corico.claudito", "contents", "ui", "Character.qml")

NOMBRES = {"idle": "Descansando", "wake": "¡Hola!", "thinking": "Pensando…", "build": "Construyendo…",
           "terminal": "En la terminal…", "search": "Buscando…", "explore": "Explorando…",
           "lead": "Coordinando…", "plan": "Planeando…", "create": "Creando…", "work": "Trabajando…",
           "waiting": "¡Te necesito!", "oops": "¡Ups!", "done": "¡Listo!", "sleep": "Durmiendo"}


def _cargar(nombre):
    ruta = os.path.join(RAIZ, "windows", nombre + ".py")
    if not os.path.exists(ruta) or not os.path.exists(PERSONAJE):
        return None
    antes, sys.dont_write_bytecode = sys.dont_write_bytecode, True    # no escribir en su carpeta
    try:
        spec = importlib.util.spec_from_file_location("claudito_" + nombre, ruta)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None
    finally:
        sys.dont_write_bytecode = antes


def _ajuste(nombre, defecto):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\corico\Claudito") as k:
            return str(winreg.QueryValueEx(k, nombre)[0])
    except OSError:
        return defecto


def elegir_ropa(estacion, gorro, traje, auto):
    if estacion == "none":
        estacion = ""
    elif estacion not in ("spring", "summer", "autumn", "winter"):
        estacion = auto
    si = ("true", "1")
    return {"gorro": estacion if gorro.lower() in si else "", "traje": estacion if traje.lower() in si else ""}


# Su dibujo va a 10 cuadros por segundo. Se usa una copia en la que la barra
# puede bajar el ritmo; si el original cambia y esto no encaja, se usa tal cual.
CAMBIOS = (("  readonly property int frameStep: ", "  property int minimo: 1\n  readonly property int frameStep: Math.max(minimo, "),
           ('mode === "idle" ? 2 : 1\n', 'mode === "idle" ? 2 : 1)\n'),
           ("renderStrategy: Canvas.Cooperative", "renderStrategy: Canvas.Immediate"))


def adaptar(texto):
    """El dibujo con ritmo ajustable, o None si ya no es como se esperaba."""
    for antes, despues in CAMBIOS:
        if texto.count(antes) != 1:
            return None
        texto = texto.replace(antes, despues)
    return texto


def copia_personaje(carpeta):
    """Deja la copia en `carpeta` y devuelve qué archivo cargar."""
    try:
        with open(PERSONAJE, encoding="utf-8") as f:
            nuevo = adaptar(f.read())
        if nuevo is None:
            return PERSONAJE
        codigo = os.path.join(os.path.dirname(os.path.dirname(PERSONAJE)), "code")
        for sub in ("ui", "code"):
            os.makedirs(os.path.join(carpeta, sub), exist_ok=True)
        for n in os.listdir(codigo):
            if n.endswith(".js"):
                shutil.copyfile(os.path.join(codigo, n), os.path.join(carpeta, "code", n))
        ruta = os.path.join(carpeta, "ui", "Character.qml")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(nuevo)
        return ruta
    except OSError:
        return PERSONAJE


def lista_sesiones(vistas, vivas):
    """Las sesiones abiertas: primero las que te necesitan, luego las recientes."""
    abiertas = [v for v in vistas.values() if (v["session"] in vivas if vivas is not None else v["mode"] != "sleep")]
    abiertas.sort(key=lambda v: (v["mode"] != "waiting", -v["ts"]))
    return [{"id": v["session"], "proyecto": v["project"], "modo": v["mode"],
             "texto": NOMBRES.get(v["mode"], v["mode"])} for v in abiertas]


class Claudito:
    def __init__(self):
        self._mod = _cargar("activity")
        self._estaciones = _cargar("seasons")
        self._tracker = self._mod.Tracker() if self._mod else None
        self.sesiones, self.actual = [], ""
        self._estado = os.path.join(os.environ["LOCALAPPDATA"], "claudito", "state.json")

    @property
    def disponible(self):
        return self._tracker is not None

    def ropa(self):
        """{"gorro", "traje"}: estaciones o "", según lo elegido en el menú de Claudito."""
        try:
            auto = self._estaciones.current()
            return elegir_ropa(_ajuste("season", "auto"), _ajuste("wearHat", "true"),
                               _ajuste("wearOutfit", "true"), auto)
        except Exception:
            return {"gorro": "", "traje": ""}

    def leer(self):
        """{"modo", "texto"}, o None si esta vez no se pudo."""
        try:
            with open(self._estado, encoding="utf-8") as f:
                texto = f.read()
        except FileNotFoundError:
            texto = ""
        except OSError:
            return None
        try:
            vivas = self._mod.read_registry()
            vista, vistas = self._tracker.update(texto, vivas, time.time())
            if vistas is not None:
                self.sesiones = lista_sesiones(vistas, vivas)
            self.actual = vista.get("session", "")
        except Exception:
            return None
        modo = vista.get("mode", "sleep")
        nombre = NOMBRES.get(modo, modo)
        return {"modo": modo, "texto": nombre + (f' · {vista["project"]}' if vista.get("project") else "")}


if __name__ == "__main__":
    print(json.dumps(Claudito().leer(), ensure_ascii=False))
