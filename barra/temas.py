"""Carga de temas (una carpeta por tema) y colores del fondo para Camaleón."""
import colorsys
import json
import os
import winreg

RAIZ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temas")

BASE = {
    "nombre": "", "orden": 99, "forma": "completa", "alto": 48, "margen": 0, "radio": 0, "relleno": 6,
    "separacion": 8, "fuente": "Segoe UI", "tamano": 13, "negrita": False, "borde": 0, "indicador": "linea",
    "reloj": "HH:mm", "fecha": "ddd d MMM", "fondo": "", "pixelado": False, "paseo": False,
    "corchetes": False, "dinamico": False, "icono": 24, "vidrio": False,
    "compacto": False, "centrado": False, "coloresClaros": {}, "adapta": False,
    "medidor": "texto", "momentos": {},
    "logo": {"colores": ["acento"], "fuera": 0, "dentro": 0, "lados": 0, "hueco": 2, "opacidad": 1, "contorno": False,
             "filo": "", "bisel": False},
    "colores": {"fondo": "#E6202020", "fondo2": "#E6202020", "isla": "transparent", "borde": "#40FFFFFF",
                "texto": "#FFFFFF", "tenue": "#A0A0A0", "acento": "#4CC2FF", "acento2": "#4CC2FF",
                "alerta": "#FF6B6B", "encima": "#22FFFFFF", "fondoBandeja": "transparent",
                "medidor1": "", "medidor2": "", "medidor3": ""},
    "modulos": {"izquierda": [["inicio", "tareas"]], "centro": [["musica"]],
                "derecha": [["claudito"], ["sistema"], ["bandeja", "volumen"], ["reloj"], ["temas"]]},
}


def cargar(raiz=RAIZ):
    """{id: tema}, en el orden en que se muestran. Un tema roto se salta."""
    out = {}
    for nombre in sorted(os.listdir(raiz)):
        ruta = os.path.join(raiz, nombre, "tema.json")
        if not os.path.exists(ruta):
            continue
        try:
            with open(ruta, encoding="utf-8") as f:
                d = json.load(f)
            t = {**BASE, **d, "id": nombre}
            t["colores"] = {**BASE["colores"], **d.get("colores", {})}
            t["modulos"] = {**BASE["modulos"], **d.get("modulos", {})}
            t["logo"] = {**BASE["logo"], **d.get("logo", {})}
        except (OSError, ValueError, TypeError, AttributeError) as e:
            print(f"tema {nombre}: {e}")
            continue
        fondo = os.path.join(raiz, nombre, t["fondo"]) if t["fondo"] else ""
        t["fondoUrl"] = "file:///" + fondo.replace("\\", "/") if fondo and os.path.exists(fondo) else ""
        out[nombre] = t
    return dict(sorted(out.items(), key=lambda kv: (kv[1]["orden"], kv[0])))


FORMATOS = {"tema": "El del tema", "completa": "Completa", "islas": "Islas", "compacta": "Compacta",
            "islas_compactas": "Islas compactas"}
NORMAL = 48        # lo que reserva la barra de Windows


def con_momento(t, momento):
    """El tema con los colores de ese momento del día, si los tiene."""
    extra = t["momentos"].get(momento)
    return {**t, "colores": {**t["colores"], **extra}} if extra else t


def con_formato(t, formato):
    """El tema con otra forma o tamaño."""
    if formato not in FORMATOS or formato == "tema":
        return t
    t = {**t, "compacto": "compacta" in formato}
    col = dict(t["colores"])
    if formato.startswith("islas"):
        if t["forma"] != "islas":
            t.update(forma="islas", fondoUrl="", separacion=8, relleno=8, borde=1)
            t["radio"] = 0 if t["pixelado"] or t["corchetes"] else max(t["radio"], 12)
            col["isla"] = col["fondo"]
        t.update(alto=42, margen=3)
    else:
        if t["forma"] == "islas":
            t.update(forma="completa", radio=0, vidrio=False, adapta=False)
            col["isla"] = "transparent"
        t.update(alto=46, margen=0)
    if t["compacto"]:
        t.update(alto=30, margen=3 if t["forma"] == "islas" else 0, tamano=min(t["tamano"], 12), icono=18)
    t["colores"] = col
    return t


ALINEACIONES = {"windows": "Como en Windows", "izquierda": "A la izquierda", "centro": "En el centro"}


def windows_centrado():
    """Lo elegido en Configuración > Personalización > Barra de tareas."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced") as k:
            return winreg.QueryValueEx(k, "TaskbarAl")[0] != 0
    except OSError:
        return True          # el valor de fábrica de Windows 11


def con_alineacion(t, centro):
    """Inicio y ventanas en el centro o a la izquierda. En el centro, Claudito,
    el uso del sistema y lo que había allí pasan a la izquierda."""
    m = t["modulos"]
    grupos = m["izquierda"] + m["centro"]
    apps = [g for g in grupos if "inicio" in g or "tareas" in g]
    resto = [g for g in grupos if g not in apps]
    if centro:
        lado = [g for g in m["derecha"] if "claudito" in g or "sistema" in g]
        nuevo = {"izquierda": lado + resto, "centro": apps,
                 "derecha": [g for g in m["derecha"] if g not in lado]}
    else:
        nuevo = {"izquierda": apps, "centro": resto}
    return {**t, "modulos": {**m, **nuevo}, "centrado": centro}


def alto_total(t):
    """Alto de la ventana. Los normales usan todo el hueco de la barra de Windows."""
    return t["alto"] + 2 * t["margen"] if t["compacto"] else NORMAL


# ----- Camaleón -------------------------------------------------------------

def _valor(clave, nombre):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, clave) as k:
            return winreg.QueryValueEx(k, nombre)[0]
    except OSError:
        return ""


def _buscar(d, clave):
    if isinstance(d, dict):
        if clave in d:
            return d[clave]
        for v in d.values():
            r = _buscar(v, clave)
            if r is not None:
                return r
    return None


def imagen_wallpaper_engine():
    """La vista previa del fondo elegido en Wallpaper Engine, o ""."""
    exe = _valor(r"Software\WallpaperEngine", "installPath")
    try:
        with open(os.path.join(os.path.dirname(exe), "config.json"), encoding="utf-8") as f:
            elegidos = _buscar(json.load(f), "selectedwallpapers") or {}
        for e in elegidos.values():
            archivo = e.get("file") if isinstance(e, dict) else None
            for p in ("preview.jpg", "preview.png", "preview.gif"):
                ruta = os.path.join(os.path.dirname(archivo or ""), p)
                if archivo and os.path.exists(ruta):
                    return ruta
    except (OSError, ValueError, AttributeError):
        pass
    return ""


def imagen_fondo(wallpaper_engine):
    if wallpaper_engine:
        ruta = imagen_wallpaper_engine()
        if ruta:
            return ruta
    ruta = _valor(r"Control Panel\Desktop", "WallPaper")
    return ruta if ruta and os.path.exists(ruta) else ""


def paleta(pixeles):
    """Colores del tema a partir de [(r, g, b)]: fondo muy oscuro y casi opaco
    del tono vivo más presente, para que se lea sobre cualquier imagen."""
    if not pixeles:
        return {}
    cubos = {}
    for p in pixeles:
        ph, ps, pv = colorsys.rgb_to_hsv(*(x / 255 for x in p))
        peso = ps * pv
        if peso > 0.12:
            c = cubos.setdefault(int(ph * 24) % 24, [0, 0])
            c[0] += peso
            c[1] += ph * peso
    orden = sorted(cubos.values(), key=lambda c: -c[0])
    tonos = [c[1] / c[0] for c in orden]
    uno = tonos[0] if tonos else 0
    # El segundo, el más presente que sea claramente otro color.
    dos = next((t for c, t in zip(orden, tonos) if 0.14 < abs(t - uno) < 0.86 and c[0] > orden[0][0] * 0.08),
               uno + 0.45)
    sat = 1 if tonos else 0.08              # fondo gris: casi sin color

    def color(h, s, v, alfa=255):
        return "#%02X%02X%02X%02X" % ((alfa,) + tuple(round(x * 255) for x in colorsys.hsv_to_rgb(h % 1, s * sat, v)))

    return {"fondo": color(uno, 0.50, 0.11, 242), "fondo2": color(uno, 0.50, 0.15, 242),
            "isla": color(uno, 0.48, 0.14, 236), "borde": color(uno, 0.55, 0.85, 150),
            "texto": color(uno, 0.05, 0.99), "tenue": color(uno, 0.16, 0.84),
            "acento": color(uno, 0.55, 1.0), "acento2": color(dos, 0.55, 1.0), "encima": color(uno, 0.55, 1.0, 50),
            "medidor1": color(uno, 0.55, 1.0), "medidor2": color(dos, 0.55, 1.0),
            "medidor3": color((uno + dos) / 2, 0.45, 1.0)}
