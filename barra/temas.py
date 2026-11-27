"""Carga de temas (una carpeta por tema) y colores del fondo para Camaleón."""
import colorsys
import json
import os
import winreg

from . import sitio

RAIZ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temas")
# Los tuyos: ahí las actualizaciones no los tocan.
PROPIOS = os.path.join(os.environ["LOCALAPPDATA"], "barra-temas", "temas")

BASE = {
    "nombre": "", "orden": 99, "forma": "completa", "alto": 48, "margen": 0, "radio": 0, "relleno": 6,
    "separacion": 8, "fuente": "Segoe UI", "tamano": 13, "negrita": False, "borde": 0, "indicador": "linea",
    "reloj": "HH:mm", "fecha": "ddd d MMM", "fondo": "", "pixelado": False, "paseo": False,
    "corchetes": False, "dinamico": False, "icono": 24, "estiloIconos": "", "estiloBandeja": "", "vidrio": False,
    "compacto": False, "dock": False, "lupa": 0.38, "pegada": False, "esquinas": False, "burbujas": False, "centrado": False, "vertical": False, "lado": "abajo", "coloresClaros": {}, "adapta": False,
    "medidor": "texto", "momentos": {}, "logoClaros": [], "unica": False, "radioBoton": 0, "relojDoble": True, "sombraReloj": False, "variante": "tema", "dentro": False,
    "glifos": False, "acentoWindows": True, "fondoActiva": True, "pastillaSoloOriginales": False, "translucida": False, "opacidad": 100, "aire": 0, "cava": "barras", "clima": "emoji", "windows": False, "claro": {}, "clara": False, "contorno": False, "adorno": 1,
    "busqueda": "auto", "icono_busqueda": "lupa", "vista": "insignia", "icono_vista": "ventanas", "glifoBusqueda": "\uE721", "glifoVista": "\uE7C4",
    "logo": {"colores": ["acento"], "fuera": 0, "dentro": 0, "lados": 0, "hueco": 2, "opacidad": 1, "contorno": False,
             "filo": "", "bisel": False},
    "colores": {"fondo": "#E6202020", "fondo2": "#E6202020", "isla": "transparent", "borde": "#40FFFFFF",
                "texto": "#FFFFFF", "tenue": "#A0A0A0", "acento": "#4CC2FF", "acento2": "#4CC2FF",
                "alerta": "#FF6B6B", "encima": "#22FFFFFF", "fondoBandeja": "transparent",
                "medidor1": "", "medidor2": "", "medidor3": "", "cava1": "", "cava2": ""},
    "modulos": {"izquierda": [["inicio", "tareas"]], "centro": [["musica"]],
                "derecha": [["widgets"], ["claudito"], ["sistema"], ["bandeja", "volumen"], ["reloj"], ["temas"]]},
}


def cargar(raices=(RAIZ, PROPIOS)):
    """{id: tema}, en el orden en que se muestran. Un tema roto se salta."""
    out = {}
    for raiz, nombre in [(r, n) for r in raices if os.path.isdir(r) for n in sorted(os.listdir(r))]:
        ruta = os.path.join(raiz, nombre, "tema.json")
        if not os.path.exists(ruta):
            continue
        try:
            with open(ruta, encoding="utf-8") as f:
                d = json.load(f)
            t = {**BASE, **d, "id": nombre, "carpeta": os.path.join(raiz, nombre)}
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


FORMATOS = {"tema": "El del tema", "completa": "Completa", "flotante": "Flotante", "islas": "Islas", "compacta": "Compacta",
            "islas_compactas": "Islas compactas", "isla": "Una isla", "isla_compacta": "Una isla compacta",
            "pestana": "Pestaña", "dock": "Dock", "dock_pegado": "Dock pegado", "dock_mini": "Dock pequeño",
            "esquinas": "Esquinas", "burbujas": "Burbujas"}
UNA_ISLA = ("isla", "isla_compacta", "pestana", "dock", "dock_pegado", "dock_mini")
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
    if formato in UNA_ISLA:       # todo junto, en el centro
        if t["forma"] != "islas" or rgb(col["isla"])[3] < 0.5:
            col["isla"] = col["fondo"]
        t.update(forma="islas", unica=True, dentro=True, paseo=False, vidrio=False, adapta=False,
                 separacion=10 if t["compacto"] else 16, aire=4 if t["compacto"] else 6, relleno=8,
                 borde=2 if t["pixelado"] else 1, alto=42, margen=3)
        t["radio"] = 0 if t["pixelado"] or t["corchetes"] else max(t["radio"], 14)
        if formato == "pestana":          # pegada al borde, redondeada solo por dentro
            t.update(pegada=True, alto=46, margen=0)
        if formato.startswith("dock"):     # iconos grandes que crecen bajo el ratón; algo más alta
            t.update(dock=True, alto=54, margen=3, icono=34, relleno=10, lupa=0.38)
            if formato == "dock_pegado":
                t.update(alto=56, margen=0, pegada=True)
            elif formato == "dock_mini":      # cabe en lo que reserva Windows
                t.update(alto=44, margen=2, icono=28, relleno=8, lupa=0.25)
            if t["indicador"] in ("linea", "relleno"):
                t["indicador"] = "punto"
            t["radio"] = 0 if t["pixelado"] or t["corchetes"] else max(t["radio"], 18)
    elif formato in ("esquinas", "burbujas"):
        if t["forma"] != "islas" or rgb(col["isla"])[3] < 0.5:
            col["isla"] = col["fondo"]
        t.update(forma="islas", dentro=True, borde=2 if t["pixelado"] else 1)
        if formato == "esquinas":       # tres piezas: los lados encajados en las esquinas
            t.update(esquinas=True, alto=44, margen=0, relleno=12, separacion=10)
            t["radio"] = 0 if t["pixelado"] or t["corchetes"] else max(t["radio"], 14)
        else:                           # cada botón en su círculo; el resto, en píldoras
            t.update(burbujas=True, alto=40, margen=4, relleno=8, separacion=10, aire=4, indicador="burbuja")
            t["radio"] = 0 if t["pixelado"] or t["corchetes"] else 20
    elif formato.startswith("islas"):
        if t["forma"] != "islas":
            t.update(forma="islas", dentro=True, separacion=8, relleno=8, borde=2 if t["pixelado"] else 1)
            t["radio"] = 0 if t["pixelado"] or t["corchetes"] else max(t["radio"], 12)
            col["isla"] = col["fondo"]
        t.update(alto=42, margen=3)
    else:
        if t["forma"] == "islas":
            t.update(forma="completa", radio=0, vidrio=False, adapta=False)
            col["isla"] = "transparent"
        t.update(alto=46, margen=0)
        if formato == "flotante":          # separada del borde, como una píldora
            t.update(alto=38, margen=5, borde=2 if t["pixelado"] else 1)
            t["radio"] = 0 if t["pixelado"] or t["corchetes"] else 19
    if t["compacto"]:
        t.update(alto=30, margen=3 if t["forma"] == "islas" else 0, tamano=min(t["tamano"], 12), icono=18)
    t["colores"] = col
    return t


OPACIDADES = {100: "Opaca", 85: "85 %", 70: "70 %", 50: "50 %", 30: "30 %", 15: "15 %", 0: "Transparente"}


def _con_alfa(c, alfa):
    """El color con su alfa multiplicado. Nunca 0: Windows dejaría pasar los clics."""
    r, g, b, a = rgb(c)
    if a == 0:
        return c
    return "#%02X%02X%02X%02X" % tuple(round(x * 255) for x in (max(a * alfa, 1 / 255), r, g, b))


def brillo(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def brillo_de_lado(pixeles, lado, n=40):
    """Lo clara que es, de 0 a 1, la parte del fondo que queda tras la barra.
    `pixeles`: [(r, g, b)] de una imagen de n x n, por columnas."""
    if len(pixeles) != n * n:
        return 0.3
    b = max(1, n // 10)
    toca = {"abajo": lambda x, y: y >= n - b, "arriba": lambda x, y: y < b,
            "izquierda": lambda x, y: x < b, "derecha": lambda x, y: x >= n - b}[lado]
    v = [brillo([k / 255 for k in p]) for i, p in enumerate(pixeles) if toca(i // n, i % n)]
    return sum(v) / len(v)


def con_opacidad(t, nivel, detras):
    """El tema con su fondo más o menos transparente. `detras`: lo claro que es
    el fondo de escritorio ahí. El texto pasa a oscuro si hace falta."""
    if not t["translucida"] or nivel >= 100:
        return t
    a = max(0, nivel) / 100
    col = dict(t["colores"])
    base = brillo(rgb(col["isla"] if t["forma"] == "islas" else col["fondo"]))
    for k in ("fondo", "fondo2", "isla", "borde"):
        col[k] = _con_alfa(col[k], a)
    if nivel < 80:                  # el gris se perdería sobre una imagen
        x, y = rgb(col["texto"]), rgb(col["tenue"])
        col["tenue"] = "#%02X%02X%02X" % tuple(round((0.75 * i + 0.25 * j) * 255) for i, j in zip(x[:3], y[:3]))
    return {**t, "colores": col, "opacidad": nivel, "contorno": nivel < 60,
            "clara": base * a + detras * (1 - a) > 0.5}


def apariencia_windows():
    """(¿modo claro?, acento para fondo oscuro, acento para fondo claro), como los
    usa la barra de Windows. Los acentos, o "" si no se pueden leer."""
    claro = _valor(r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "SystemUsesLightTheme") == 1
    p = _valor(r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent", "AccentPalette")
    if not isinstance(p, bytes) or len(p) < 32:
        return claro, "", ""
    return claro, "#%02X%02X%02X" % tuple(p[4:7]), "#%02X%02X%02X" % tuple(p[16:19])


def _legible(c, fondo, minimo=3.2):
    """El color, aclarado u oscurecido lo justo para destacar sobre `fondo`."""
    v, hacia = rgb(c)[:3], (0, 0, 0) if luz(fondo) > 0.3 else (1, 1, 1)
    for i in range(21):
        x = tuple(a + (b - a) * i / 20 for a, b in zip(v, hacia))
        if contraste(x, fondo) >= minimo:
            break
    return "#%02X%02X%02X" % tuple(round(a * 255) for a in x)


def con_windows(t, apariencia):
    """El tema con el modo y el acento elegidos en Windows."""
    if not t["windows"]:
        return t
    claro, en_oscuro, en_claro = apariencia
    col = {**t["colores"], **(t["claro"] if claro else {})}
    acento = (en_claro if claro else en_oscuro) if t["acentoWindows"] else None
    if acento:
        col["acento"] = col["acento2"] = _legible(acento, rgb(col["fondo"]))
    otros = dict(t["coloresClaros"])
    if en_claro and otros and t["acentoWindows"]:
        otros["acento"] = otros["acento2"] = en_claro
    return {**t, "colores": col, "coloresClaros": otros}


def con_windows_y_opacidad(t, apariencia, formato, nivel, detras):
    """Modo de Windows, formato y opacidad. En modo claro y casi transparente
    sobre un fondo oscuro, el texto negro no se leería: ahí va el modo oscuro."""
    x = con_opacidad(con_formato(con_windows(t, apariencia), formato), nivel, detras)
    if t["windows"] and apariencia[0] and x["opacidad"] < 100 and not x["clara"]:
        x = con_opacidad(con_formato(con_windows(t, (False, *apariencia[1:])), formato), nivel, detras)
    return x


def con_posicion(t, lado):
    """El tema en ese lado de la pantalla. En vertical `alto` es el grosor, y no
    lleva paisaje: están dibujados a lo ancho."""
    lado = lado if lado in sitio.LADOS else "abajo"
    if lado not in sitio.VERTICALES:
        return {**t, "lado": lado, "vertical": False}
    islas = t["forma"] == "islas"
    margen = (3 if t["compacto"] else 4) if islas else 0
    total = 46 if t["compacto"] else 60
    return {**t, "lado": lado, "vertical": True, "fondoUrl": "", "alto": total - 2 * margen, "margen": margen,
            "relleno": 4 if islas else 8, "separacion": min(t["separacion"], 14 if t["unica"] else 8)}


ALINEACIONES = {"windows": "Como en Windows", "izquierda": "Al principio", "centro": "En el centro"}


def windows_centrado():
    """Lo elegido en Configuración > Personalización > Barra de tareas."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced") as k:
            return winreg.QueryValueEx(k, "TaskbarAl")[0] != 0
    except OSError:
        return True          # el valor de fábrica de Windows 11


def con_alineacion(t, centro):
    """Inicio y ventanas en el centro o a la izquierda. En el centro, los
    widgets, Claudito, el uso del sistema y lo que había allí pasan a la izquierda."""
    m = t["modulos"]
    grupos = m["izquierda"] + m["centro"]
    apps = [g for g in grupos if "inicio" in g or "tareas" in g]
    resto = [g for g in grupos if g not in apps]
    if centro:
        lado = [g for g in m["derecha"] if {"widgets", "claudito", "sistema"} & set(g)]
        nuevo = {"izquierda": lado + resto, "centro": apps,
                 "derecha": [g for g in m["derecha"] if g not in lado]}
        if t["unica"]:             # repartido, para que la isla sea más corta
            nuevo.update(izquierda=lado, derecha=resto + nuevo["derecha"])
    else:
        nuevo = {"izquierda": apps, "centro": resto}
    return {**t, "modulos": {**m, **nuevo}, "centrado": centro}


def con_busqueda(t, si):
    """El campo «Buscar» justo después de Inicio, en su mismo grupo."""
    if not si:
        return t
    m = {lado: [list(g) for g in grupos] for lado, grupos in t["modulos"].items()}
    for grupos in m.values():
        for g in grupos:
            if "inicio" in g and "buscar" not in g:
                g.insert(g.index("inicio") + 1, "buscar")
                return {**t, "modulos": m}
    return t


def con_vista_tareas(t, si):
    """El botón de Vista de tareas tras Inicio (y tras «Buscar», si está)."""
    if not si:
        return t
    m = {lado: [list(g) for g in grupos] for lado, grupos in t["modulos"].items()}
    for grupos in m.values():
        for g in grupos:
            if "inicio" in g and "vista" not in g:
                g.insert(g.index("buscar" if "buscar" in g else "inicio") + 1, "vista")
                return {**t, "modulos": m}
    return t


# Qué ventanas enseña cada barra cuando hay varias pantallas.
PANTALLAS = {"suya": "Las de su pantalla", "principal": "Todas en la principal", "todas": "Todas en todas"}


def ventanas_de_pantalla(info, modo, primaria, mia):
    """Las ventanas que van en la barra de la pantalla `mia`."""
    if modo == "todas" or (modo == "principal" and primaria):
        return info
    return [i for i in info if i["pantalla"] == mia]


ICONO = {"tema": "Color del tema", "fondo": "Color del fondo"}
VARIANTES = {"tema": "Original", "pastel": "Pastel", "vivos": "Vivos", "suaves": "Suaves", "oscuro": "Oscuro"}
_FONDOS = ("fondo", "fondo2", "isla", "fondoBandeja")
_TONOS = ("acento", "acento2", "alerta", "medidor1", "medidor2", "medidor3", "cava1", "cava2")


def _hsl(c):
    """(tono, saturación, luz, alfa) de un color del tema, o None si no es un color."""
    import colorsys
    if not isinstance(c, str) or not c.startswith("#") or len(c) not in (7, 9):
        return None
    r, g, b, a = rgb(c)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h, s, l, a


def _de_hsl(h, s, l, a=1.0):
    import colorsys
    r, g, b = colorsys.hls_to_rgb(h % 1, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    if a >= 0.999:
        return "#%02X%02X%02X" % tuple(round(x * 255) for x in (r, g, b))
    return "#%02X%02X%02X%02X" % tuple(round(x * 255) for x in (a, r, g, b))


_VIVOS = ("acento", "acento2", "medidor1", "medidor2", "medidor3", "cava1", "cava2")


def _claro(c, luz=0.6):
    """El color con al menos esa luz, para que se vea sobre el gris de Windows."""
    x = _hsl(c)
    if x is None or x[2] >= luz:
        return c
    return _de_hsl(x[0], x[1], luz, x[3])


def con_integrado(t, si):
    """«Como Windows»: la forma, la letra y el gris de la barra de Windows. Del tema quedan
    sus colores de acento (logo, indicador, medidores, visualizador) y su paisaje, muy suave."""
    if not si:
        return t
    col = dict(t["colores"])
    r, g, b, _ = rgb(col["fondo"]) if col["fondo"].startswith("#") else (0.125, 0.125, 0.125, 1)
    k = 0.18 if brillo((r, g, b)) < 0.5 else 0.1          # los temas de fondo claro, menos tinte
    # Casi opaca, como la de Windows; en los temas con opacidad ajustable manda ese ajuste.
    fondo = ("#FF" if t["translucida"] else "#EB") + "%02X%02X%02X" % tuple(round((k * x + (1 - k) * 0.125) * 255) for x in (r, g, b))
    col.update(fondo=fondo, fondo2=fondo, isla=fondo, borde="#FF3A3A3A", texto="#FFFFFF", tenue="#A6A6A6",
               encima="#1FFFFFFF", fondoBandeja="transparent")
    for k in _VIVOS:
        if col.get(k):
            col[k] = _claro(col[k])
    logo = {**t["logo"], "colores": [c if c in col else _claro(c, 0.5) for c in t["logo"]["colores"]]}
    return {**t, "colores": col, "logo": logo, "coloresClaros": {}, "logoClaros": [], "claro": {},
            "forma": "completa", "alto": 48, "margen": 0, "radio": 0, "borde": 0, "relleno": 6, "separacion": 4,
            "radioBoton": 5, "fuente": "Segoe UI Variable Text", "tamano": 12, "negrita": False, "glifos": True,
            "medidor": "linea", "indicador": "linea", "clima": "emoji", "cava": "barras", "relojDoble": True,
            "fecha": "dd/MM/yyyy", "reloj": "HH:mm", "pixelado": False, "paseo": False, "sombraReloj": False,
            "corchetes": False, "fondoActiva": True, "estiloIconos": "", "estiloBandeja": "",
            "adorno": 0.3, "integrado": True}


# Los diseños de cada widget: los que ya traen los temas, para cualquiera de ellos.
DISENOS = {
    "clima": {"tema": "Del tema", "emoji": "Emoji", "neon": "Neón", "flor": "Flor", "hoja": "Hoja", "pixel": "Píxel"},
    "medidor": {"tema": "Del tema", "texto": "Texto", "linea": "Línea", "pildora": "Píldora", "onda": "Onda",
                "anillo": "Anillo", "flor": "Flor", "corazones": "Corazones", "rama": "Rama"},
    "cava": {"tema": "Del tema", "barras": "Barras", "neon": "Neón", "petalos": "Pétalos", "hojas": "Hojas",
             "bloques": "Bloques"},
    "busqueda": {"auto": "Automática", "campo": "Campo", "pastilla": "Pastilla", "subrayado": "Subrayado", "lupa": "Solo el icono"},
    "icono_busqueda": {"lupa": "Lupa", "caja": "Lupa en caja", "bombilla": "Bombilla", "chispa": "Chispa",
                       "globo": "Globo", "robot": "Robot"},
    "vista": {"insignia": "Número en insignia", "texto": "Número al lado", "puntos": "Puntos", "nada": "Sin número"},
    "icono_vista": {"ventanas": "Ventanas", "cuadricula": "Cuadrícula", "mosaico": "Mosaico", "copias": "Capas",
                    "pantalla": "Pantalla", "paneles": "Paneles"},
}
# Los de Segoe Fluent Icons (comprobados a ojo: se ven en Windows 11).
GLIFOS = {"lupa": "\uE721", "caja": "\uE773", "bombilla": "\uEA80", "chispa": "\uEA38", "globo": "\uE774",
          "robot": "\uE99A", "ventanas": "\uE7C4", "cuadricula": "\uE8A9", "mosaico": "\uECA5", "copias": "\uE8C8",
          "pantalla": "\uE7F4", "paneles": "\uF246"}
CLAUDITO = {"tema": "Del tema", "quieto": "Quieto", "paseo": "Paseando"}
MENUS = {"barra": "Con la forma de la barra", "windows": "Como los de Windows"}


def forma_menus(t, modo):
    """(esquinas de DWM, separación de la barra) para las ventanitas de la barra.
    DWM: 1 sin redondear, 2 redondeadas (8 px, las de Windows 11), 3 un poco (4 px)."""
    if modo == "windows":
        return 2, 12
    if t["pixelado"] or t["radio"] <= 1:
        pref = 1
    else:
        pref = 3 if t["radio"] <= 6 else 2
    return pref, max(4, t["margen"])


def con_widgets(t, disenos, sistema=True, claudito=True):
    """El diseño elegido para cada widget (si no, el del tema), y fuera los que se apagaron."""
    t = {**t, **{k: v for k, v in disenos.items() if k in DISENOS and v in DISENOS[k] and v != "tema"}}
    t["glifoBusqueda"], t["glifoVista"] = GLIFOS[t["icono_busqueda"]], GLIFOS[t["icono_vista"]]
    modo = disenos.get("claudito", "tema")
    if modo in ("quieto", "paseo"):
        t["paseo"] = modo == "paseo" and not t["vertical"]
    quitar = {m for m, si in (("sistema", sistema), ("claudito", claudito)) if not si}
    if quitar:
        t["modulos"] = {lado: [[m for m in g if m not in quitar] for g in grupos] for lado, grupos in t["modulos"].items()}
        t["modulos"] = {lado: [g for g in grupos if g] for lado, grupos in t["modulos"].items()}
        if "claudito" in quitar:
            t["paseo"] = False
    return t


def con_variante(t, variante):
    """El tema con otra gama de colores: pastel, vivos, suaves u oscuro. Sale de sus
    propios colores (cada tema conserva sus tonos) y deja el texto legible."""
    if variante not in VARIANTES or variante == "tema":
        return t
    col = dict(t["colores"])
    acento = _hsl(col.get("acento")) or (0.58, 0.6, 0.6, 1)
    h = acento[0]

    def cambiar(clave, f):
        x = _hsl(col.get(clave))
        if x is not None and x[3] > 0:
            col[clave] = _de_hsl(*f(*x))

    if variante == "pastel":                 # fondo claro y suave, texto oscuro
        for k in _FONDOS:
            luz = {"fondo": 0.87, "fondo2": 0.83, "isla": 0.9, "fondoBandeja": 0.8}[k]
            cambiar(k, lambda _h, s, l, a, luz=luz: (h, 0.5, luz, a))
        cambiar("borde", lambda _h, s, l, a: (h, 0.35, 0.7, a))
        col["texto"], col["tenue"] = _de_hsl(h, 0.3, 0.2), _de_hsl(h, 0.18, 0.4)
        for k in _TONOS:
            cambiar(k, lambda th, s, l, a: (th, 0.55, 0.6, a))
        cambiar("encima", lambda _h, s, l, a: (h, 0.45, 0.5, 0.18))
    elif variante == "vivos":                # más color en todo: el fondo, de su tono pero intenso
        for k in _TONOS:
            cambiar(k, lambda th, s, l, a: (th, min(1.0, s * 1.3 + 0.15), max(0.5, min(0.62, l)), a))
        for k in _FONDOS:
            cambiar(k, lambda th, s, l, a: (th if s > 0.08 else h, min(1.0, max(s * 1.6, 0.45)), l, a))
    elif variante == "suaves":               # apagado, casi gris, sin perder el tono
        for k in _TONOS:
            cambiar(k, lambda th, s, l, a: (th, s * 0.45, 0.5 * l + 0.33, a))
        for k in _FONDOS + ("borde",):
            cambiar(k, lambda th, s, l, a: (th, s * 0.3, l, a))
    elif variante == "oscuro":               # fondo muy oscuro de su mismo tono, texto claro
        for k in _FONDOS:
            cambiar(k, lambda th, s, l, a: (th, min(s, 0.35), min(l * 0.45, 0.1), a))
        texto = _hsl(col.get("texto"))
        if texto and texto[2] < 0.6:
            col["texto"], col["tenue"] = _de_hsl(texto[0], 0.15, 0.92), _de_hsl(texto[0], 0.12, 0.7)
    logo = dict(t.get("logo") or {})
    if variante != "oscuro" and isinstance(logo.get("colores"), list):
        tonos = []
        for c in logo["colores"]:
            x = _hsl(c)
            if x is None:
                tonos.append(c)
            elif variante == "pastel":
                tonos.append(_de_hsl(x[0], 0.55, 0.62, x[3]))
            elif variante == "vivos":
                tonos.append(_de_hsl(x[0], min(1.0, x[1] * 1.3 + 0.15), max(0.5, min(0.62, x[2])), x[3]))
            else:
                tonos.append(_de_hsl(x[0], x[1] * 0.45, 0.5 * x[2] + 0.33, x[3]))
        logo["colores"] = tonos
    out = {**t, "colores": col, "logo": logo, "variante": variante}
    if variante == "pastel":
        out["clara"] = True
    elif variante == "oscuro":
        out["clara"] = False
    return out


ANIMACIONES = {"completas": "Completas", "suaves": "Suaves", "ninguna": "Ninguna"}
RITMO = {"completas": 100, "suaves": 200, "ninguna": 1000}       # ms entre fotogramas de los fondos


def rgb(c):
    """(r, g, b, alfa) de 0 a 1 de "#RRGGBB" o "#AARRGGBB"."""
    if not c.startswith("#"):
        return 0, 0, 0, 0
    n = [int(c[i:i + 2], 16) / 255 for i in range(1, len(c), 2)]
    return (*n, 1) if len(n) == 3 else (*n[1:], n[0])


def luz(c):
    v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c[:3]]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def contraste(a, b):
    x, y = sorted((luz(a) + 0.05, luz(b) + 0.05))
    return y / x


def base_de(t):
    """El color que se ve detrás del icono."""
    c = t["colores"]
    isla = rgb(c["isla"])
    if t["forma"] == "islas":
        return isla
    a, b = rgb(c["fondo"]), rgb(c["fondo2"])
    return tuple((x + y) / 2 for x, y in zip(a, b))


def predominante(t):
    """(tono, saturación) del color que manda en el tema, o None si no tiene."""
    for c in (base_de(t), rgb(t["colores"]["acento"])):
        h, s, v = colorsys.rgb_to_hsv(*c[:3])
        if c[3] > 0.5 and s >= 0.25 and v > 0.08:
            return h, s
    return None


def tonos_icono(tono, base):
    """Cuatro tonos del mismo color que destacan sobre `base`. `tono` es
    (matiz, saturación) o None para un gris."""
    h, s = tono or (0, 0)
    color = s > 0
    if luz(base) > 0.35:
        intentos = [(0.85, v) for v in (0.72, 0.64, 0.56, 0.48, 0.40, 0.32, 0.24, 0.16, 0.08)]
        grados = (1, 0.88, 0.88, 0.76)
    else:
        tope = min(0.60, max(0.30, s + 0.12))        # tan vivo como el tema
        intentos = [(tope, 1)] + [(x, 1) for x in (0.50, 0.40, 0.30, 0.20, 0.10, 0) if x < tope]
        grados = (1, 0.92, 0.92, 0.84)
    for sat, v in intentos:
        out = [colorsys.hsv_to_rgb(h, sat if color else 0, v * g) for g in grados]
        if min(contraste(x, base) for x in out) >= 3.1:      # 3, con margen para el redondeo
            break
    return ["#%02X%02X%02X" % tuple(round(x * 255) for x in c) for c in out]


def con_icono(t, tono):
    """El tema con su icono de Windows teñido. `tono` manda si no es None."""
    if t["vidrio"] or t["adapta"] or t["opacidad"] < 100:         # cambia según lo claro que sea el fondo
        oscura, clara = (0.12, 0.14, 0.18), (0.93, 0.93, 0.93)
        if t["opacidad"] < 100:
            tono = tono or predominante({**t, "colores": {**t["colores"], "fondo": "#FF000000", "fondo2": "#FF000000",
                                                          "isla": "#FF000000"}})
    else:
        oscura = clara = base_de(t)
        tono = tono or predominante(t)
    logo = t["logo"]
    return {**t, "logo": {**logo, "colores": tonos_icono(tono, oscura)},
            "logoClaros": tonos_icono(tono, clara)}


def alto_total(t):
    """Alto de la ventana. Los normales usan todo el hueco de la barra de Windows."""
    return t["alto"] + 2 * t["margen"] if t["compacto"] or t["vertical"] or t["dock"] else NORMAL


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
            "medidor3": color((uno + dos) / 2, 0.45, 1.0), "tono": (uno, 1) if tonos else None}
