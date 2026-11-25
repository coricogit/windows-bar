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
    "compacto": False,
    "logo": {"colores": ["acento"], "fuera": 0, "dentro": 0, "lados": 0, "hueco": 2, "opacidad": 1, "contorno": False,
             "filo": "", "bisel": False},
    "colores": {"fondo": "#E6202020", "fondo2": "#E6202020", "isla": "transparent", "borde": "#40FFFFFF",
                "texto": "#FFFFFF", "tenue": "#A0A0A0", "acento": "#4CC2FF", "acento2": "#4CC2FF",
                "alerta": "#FF6B6B", "encima": "#22FFFFFF", "fondoBandeja": "transparent"},
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
            t.update(forma="completa", radio=0, vidrio=False, brillo=False)
            col["isla"] = "transparent"
        t.update(alto=46, margen=0)
    if t["compacto"]:
        t.update(alto=30, margen=3 if t["forma"] == "islas" else 0, tamano=min(t["tamano"], 12), icono=18)
    t["colores"] = col
    return t


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
    """Colores del tema a partir de [(r, g, b)]: fondo oscuro del tono medio y
    acento del tono vivo más presente."""
    if not pixeles:
        return {}
    n = len(pixeles)
    r, g, b = (sum(p[i] for p in pixeles) / n / 255 for i in range(3))
    h, s, _ = colorsys.rgb_to_hsv(r, g, b)
    cubos = {}
    for p in pixeles:
        ph, ps, pv = colorsys.rgb_to_hsv(*(x / 255 for x in p))
        peso = ps * pv
        if peso > 0.12:
            c = cubos.setdefault(int(ph * 24) % 24, [0, 0])
            c[0] += peso
            c[1] += ph * peso
    if cubos:
        mejor = max(cubos.values(), key=lambda c: c[0])
        tono = mejor[1] / mejor[0]
    else:                      # fondo gris
        tono, s = h, 0

    def color(hh, ss, vv, alfa=255):
        return "#%02X%02X%02X%02X" % ((alfa,) + tuple(round(x * 255) for x in colorsys.hsv_to_rgb(hh % 1, ss, vv)))

    viva = 0.55 if cubos else 0.05
    return {"fondo": color(h, min(s, 0.6), 0.13, 235), "fondo2": color(h, min(s, 0.6), 0.2, 235),
            "isla": color(h, min(s, 0.5), 0.24, 160), "borde": color(tono, viva * 0.7, 0.6, 90),
            "texto": color(tono, 0.06, 0.97), "tenue": color(tono, 0.14, 0.72),
            "acento": color(tono, viva, 0.95), "acento2": color(tono + 0.08, viva, 0.85),
            "encima": color(tono, viva, 0.95, 45)}
