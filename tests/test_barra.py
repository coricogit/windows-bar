"""py -m unittest discover -s tests   (no toca la barra de Windows)"""
import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from barra import actualizar, ajustes, arranque, atajos, cava, iconos, tiempo, bandeja, cielo, claudito, instalado, panel_claude, programas, selector, sesiones, sistema, sitio, temas, vidrio, vigilante, vista, win  # noqa: E402


def aviso(msg, hwnd=0x1234, uid=7, flags=7, tip="Hola", version=0, estado=0, mascara=0):
    d = bytearray(964)
    struct.pack_into("<8I", d, 0, bandeja.SIGNATURE, msg, 956, hwnd, uid, flags, 0x401, 0x99)
    d[32:32 + len(tip) * 2] = tip.encode("utf-16-le")
    struct.pack_into("<II", d, 288, estado, mascara)
    struct.pack_into("<I", d, 808, version)
    return bytes(d)


class Bandeja(unittest.TestCase):
    def test_lee_el_mensaje(self):
        n = bandeja.parse(aviso(0, tip="Ñandú"))
        self.assertEqual((n["hwnd"], n["uid"], n["callback"], n["tip"]), (0x1234, 7, 0x401, "Ñandú"))

    def test_ignora_lo_que_no_es(self):
        self.assertIsNone(bandeja.parse(b""))
        self.assertIsNone(bandeja.parse(b"\0" * 964))

    def test_ciclo(self):
        ic = bandeja.Icons()
        k = ic.apply(bandeja.parse(aviso(0)))
        ic.apply(bandeja.parse(aviso(4, version=4)))
        self.assertEqual(ic.items[k]["version"], 4)
        ic.apply(bandeja.parse(aviso(1, flags=4, tip="Nuevo")))
        self.assertEqual((ic.items[k]["tip"], ic.items[k]["callback"]), ("Nuevo", 0x401))
        ic.apply(bandeja.parse(aviso(1, flags=8, estado=1, mascara=1)))
        self.assertTrue(ic.items[k]["hidden"])
        self.assertEqual(ic.apply(bandeja.parse(aviso(2))), k)
        self.assertEqual(ic.items, {})

    def test_mensajes_de_clic(self):
        self.assertEqual(win.tray_messages(True, 4), [0x204, 0x205, 0x7B])
        self.assertEqual(win.tray_messages(False, 0), [0x201, 0x202])


class Temas(unittest.TestCase):
    def test_los_que_hay(self):
        self.assertEqual(list(temas.cargar((temas.RAIZ,))), ["tokyo", "original", "sakura", "pixel", "bosque"])

    def test_caben_y_tienen_colores(self):
        for ident, t in temas.cargar().items():
            self.assertLessEqual(t["alto"] + t["margen"], 48, ident)
            for c in temas.BASE["colores"]:
                self.assertIn(c, t["colores"], ident)
            self.assertTrue(not t["fondo"] or t["fondoUrl"], ident)

    def test_formatos(self):
        for ident, t in temas.cargar().items():
            for f in temas.FORMATOS:
                n = temas.con_formato(t, f)
                self.assertLessEqual(n["alto"] + n["margen"], temas.alto_total(n), (ident, f))
                self.assertIs(temas.con_formato(t, "tema"), t)
                if f != "tema":
                    self.assertEqual(n["compacto"], "compacta" in f)
                    self.assertEqual(n["forma"] == "islas", f.startswith("isla"))
                    self.assertEqual(n["unica"], f in ("isla", "isla_compacta"))
        self.assertEqual(temas.alto_total(temas.con_formato(temas.cargar()["pixel"], "compacta")), 30)

    def test_paleta(self):
        p = temas.paleta([(200, 30, 30)] * 50 + [(20, 20, 20)] * 50)
        r, g, b = (int(p["acento"][i:i + 2], 16) for i in (3, 5, 7))
        self.assertTrue(r > g and r > b)
        self.assertEqual(temas.paleta([]), {})
        self.assertIn("acento", temas.paleta([(90, 90, 90)] * 10))


def _rgb(c):
    c = c.lstrip("#")
    return [int(c[-6:][i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _alfa(c):
    return int(c[1:3], 16) / 255 if len(c) == 9 else 1


def _lum(rgb):
    v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def contraste(a, b):
    x, y = sorted((_lum(a) + 0.05, _lum(b) + 0.05))
    return y / x


class Contraste(unittest.TestCase):
    def revisar(self, col, fondos, nombre, con_tenue=True):
        for f in fondos:
            for detras in (0, 1):          # escritorio negro o blanco
                base = [x * _alfa(f) + detras * (1 - _alfa(f)) for x in _rgb(f)]
                self.assertGreaterEqual(contraste(_rgb(col["texto"]), base), 4.5, (nombre, f, detras))
                if con_tenue:
                    self.assertGreaterEqual(contraste(_rgb(col["tenue"]), base), 4.2, (nombre, "tenue", f, detras))

    def test_temas_y_momentos(self):
        for ident, t in temas.cargar().items():
            if t["vidrio"] or t["adapta"] or t["dinamico"]:
                continue
            for m in cielo.MOMENTOS:
                c = temas.con_momento(t, m)["colores"]
                self.revisar(c, [c["isla"]] if t["forma"] == "islas" else [c["fondo"], c["fondo2"]], (ident, m))

    def test_camaleon(self):
        import random
        azar = random.Random(3)
        casos = [[tuple(azar.randrange(256) for _ in range(3)) for _ in range(60)] for _ in range(40)]
        casos += [[(255, 255, 255)] * 9, [(0, 0, 0)] * 9, [(250, 240, 20)] * 9, [(20, 20, 250)] * 9]
        for pix in casos:
            c = temas.paleta(pix)
            self.revisar(c, [c["isla"], c["fondo"]], "camaleon")
            self.assertGreater(contraste(_rgb(c["acento"]), _rgb(c["isla"])), 4)

    def test_minimalista(self):
        for i in range(101):
            clara = vidrio.es_clara([i / 100], False)
            v = vidrio.velo_justo([i / 100], clara)
            fondo = i / 100 * (1 - v) + 0.07 * v
            self.assertGreater(contraste([0.08] * 3 if clara else [0.96] * 3, [fondo] * 3), 4.1, i)
        self.assertEqual(vidrio.velo_justo([0.2, 0.4], False), 0)


class Opacidad(unittest.TestCase):
    def test_solo_los_translucidos(self):
        t = temas.cargar()["tokyo"]
        self.assertIs(temas.con_opacidad(t, 30, 0.5), t)
        t = temas.cargar()["original"]
        self.assertIs(temas.con_opacidad(t, 100, 0.5), t)

    def test_baja_sin_llegar_a_cero(self):
        for f in temas.FORMATOS:
            t = temas.con_formato(temas.cargar()["original"], f)
            for k in ("fondo", "isla"):
                v = [temas.rgb(temas.con_opacidad(t, n, 0.3)["colores"][k])[3] for n in sorted(temas.OPACIDADES)]
                if v[-1]:
                    self.assertEqual(v, sorted(v))
                    self.assertGreater(v[0], 0)          # con 0, Windows dejaría pasar los clics

    def test_se_lee_sobre_cualquier_fondo(self):
        for f in ("tema", "isla"):
            t = temas.con_formato(temas.cargar()["original"], f)
            for n in temas.OPACIDADES:
                for i in range(101):
                    d = temas.con_opacidad(t, n, i / 100)
                    c = {**d["colores"], **(d["coloresClaros"] if d["clara"] else {})}
                    a = n / 100
                    gris = [0x1C / 255 * a + i / 100 * (1 - a)] * 3
                    self.assertGreater(contraste(_rgb(c["texto"]), gris), 3.8, (f, n, i))
                    self.assertGreater(contraste(_rgb(c["tenue"]), gris), 3, (f, n, i))

    def test_brillo_de_lado(self):
        pix = [(255, 255, 255) if y >= 36 else (0, 0, 0) for x in range(40) for y in range(40)]
        b = temas.brillo_de_lado
        self.assertAlmostEqual(b(pix, "abajo"), 1)
        self.assertAlmostEqual(b(pix, "arriba"), 0)
        self.assertAlmostEqual(b(pix, "izquierda"), 0.1)
        self.assertEqual(b([], "abajo"), 0.3)

    def test_ajuste(self):
        for v, sale in ((50, 50), (-3, 0), (900, 100), ("x", 85), (None, 85)):
            self.assertEqual(ajustes.normalizar({"opacidad": v}, {"tokyo": 1}, temas.FORMATOS)["opacidad"], sale)


class Icono(unittest.TestCase):
    def test_destaca_en_todos(self):
        for ident, t in temas.cargar().items():
            for m in cielo.MOMENTOS:
                for f in temas.FORMATOS:
                    n = temas.con_icono(temas.con_formato(temas.con_momento(t, m), f), None)
                    if not (n["vidrio"] or n["adapta"] or n["dinamico"]):
                        for c in n["logo"]["colores"]:
                            self.assertGreaterEqual(temas.contraste(temas.rgb(c), temas.base_de(n)), 3, (ident, m, f))

    def test_cualquier_color(self):
        for i in range(24):
            for base in ((0.02, 0.02, 0.03), (0.95, 0.95, 0.9), (0.45, 0.7, 0.9), (0.4, 0.2, 0.4)):
                for tono in ((i / 24, 1), None):
                    c = temas.tonos_icono(tono, base)
                    self.assertEqual(len(c), 4)
                    self.assertGreaterEqual(min(temas.contraste(temas.rgb(x), base) for x in c), 3, (i, base))

    def test_predominante(self):
        h, _ = temas.predominante(temas.cargar()["sakura"])
        self.assertTrue(h > 0.85 or h < 0.05)           # rosa
        h, _ = temas.predominante(temas.cargar()["tokyo"])
        self.assertTrue(0.55 < h < 0.75)                # azul


class Menu(unittest.TestCase):
    def test_nada_se_sale_ni_se_pisa(self):
        o = [{"texto": "x" * n} for n in (4, 20, 12, 30, 9)]
        zonas, alto = selector.colocar([{"texto": str(i)} for i in range(7)], [("A", o), ("B", o + o)],
                                       [{**x, "marcado": True} for x in o], o, lambda t: len(t) * 7)
        for i, (r, _, _) in enumerate(zonas):
            self.assertLessEqual(r.right(), selector.ANCHO - selector.MARGEN + 1)
            self.assertLess(r.bottom(), alto)
            for r2, _, _ in zonas[:i]:
                self.assertFalse(r.intersects(r2))


class Arranque(unittest.TestCase):
    def test_orden(self):
        self.assertIn("barra.pyw", arranque.orden())
        self.assertTrue(os.path.exists(arranque.BARRA))
        self.assertIn(arranque.activo(), (True, False))

    def test_desactivada(self):
        self.assertTrue(arranque.desactivada(bytes([3] + [0] * 11)))
        self.assertFalse(arranque.desactivada(bytes([2] + [0] * 11)))
        self.assertFalse(arranque.desactivada(None))


class Programas(unittest.TestCase):
    def test_elegir(self):
        e = programas.elegir
        self.assertEqual(e("Windows Terminal Host", "Windows Terminal", "WindowsTerminal.exe"), "Windows Terminal")
        self.assertEqual(e("Bloc de notas", "Sistema operativo Microsoft® Windows®", "notepad.exe"), "Bloc de notas")
        self.assertEqual(e("Microsoft PowerPoint", "Microsoft Office", "POWERPNT.EXE"), "Microsoft PowerPoint")
        self.assertEqual(e("", "", "juego.exe"), "Juego")
        self.assertEqual(e("x" * 80, "", "raro.exe"), "Raro")

    def test_nombre_real(self):
        self.assertNotIn(programas.nombre(os.path.join(os.environ["WINDIR"], "explorer.exe")).lower(), ("", "explorer"))
        self.assertEqual(programas.nombre("C:\\no\\existe.exe"), "Existe")
        self.assertEqual(programas.principal("C:\\a\\b.exe"), "C:\\a\\b.exe")

    @staticmethod
    def v(h, clave, z=0, **k):
        return {"hwnd": h, "clave": clave, "nombre": clave.title(), "titulo": f"t{h}", "icono": "", "activa": False,
                "minimizada": False, "exe": clave, "z": z, **k}

    def test_agrupar(self):
        v, orden = self.v, {}
        info = [v(30, "zen", 0, activa=True), v(10, "disc", 1), v(20, "zen", 2, minimizada=True)]
        f = programas.agrupar(info, [], True, orden)
        self.assertEqual([(x["key"], x["cuenta"], x["titulo"]) for x in f], [("g:disc", 1, "t10"), ("g:zen", 2, "Zen")])
        self.assertEqual((f[1]["ventanas"], f[1]["hwnd"], f[1]["activa"], f[1]["minimizada"]), ([20, 30], "30", True, False))
        # no se mueven al cambiar de ventana activa ni al cerrarse una
        info = [v(10, "disc", 0), v(20, "zen", 1), v(5, "nota", 2)]
        self.assertEqual([x["key"] for x in programas.agrupar(info, [], True, orden)], ["g:disc", "g:zen", "g:nota"])
        # sin agrupar, una por ventana
        info = [v(30, "zen"), v(20, "zen")]
        self.assertEqual([x["key"] for x in programas.agrupar(info, [], False, {})], ["20", "30"])

    def test_anclados(self):
        fijo = {"clave": "zen", "exe": "zen.exe", "nombre": "Zen", "ruta": "r", "icono": ""}
        f = programas.agrupar([self.v(1, "disc")], [fijo], True, {})
        self.assertEqual([(x["key"], x["abierta"], x["cuenta"]) for x in f], [("g:zen", False, 0), ("g:disc", True, 1)])
        f = programas.agrupar([self.v(1, "disc"), self.v(2, "zen")], [fijo], True, {})
        self.assertEqual([x["key"] for x in f], ["g:zen", "g:disc"])       # misma clave: el botón no salta


class IconosOcultos(unittest.TestCase):
    def test_clave(self):
        c = programas.clave_bandeja
        self.assertEqual(c("C:\\x\\app-1.0\\SignalRgb.exe", "", "a"), c("C:\\x\\app-2.0\\SignalRgb.exe", "g", "b"))
        self.assertEqual(c("C:\\p\\pythonw.exe", "", "Claudito: 3 sesiones"), c("C:\\p\\pythonw.exe", "", "Claudito - 5"))
        self.assertNotEqual(c("C:\\p\\pythonw.exe", "", "Claudito"), c("C:\\p\\pythonw.exe", "", "Minipantalla"))
        self.assertNotEqual(c("C:\\w\\explorer.exe", "g1", "x"), c("C:\\w\\explorer.exe", "g2", "x"))
        self.assertEqual(c("", "", "Antivirus"), ":antivirus")

    def test_ajuste(self):
        n = ajustes.normalizar({"ocultos": ["a", 3, "a", "b"]}, {"tokyo": 1}, temas.FORMATOS)
        self.assertEqual(n["ocultos"], ["a", "b"])


class Actualizar(unittest.TestCase):
    @staticmethod
    def release(version="1.2.0", **k):
        n = actualizar.archivo(version)
        return {"tag_name": "v" + version, "draft": False, "prerelease": False, "assets": [
            {"name": n, "digest": "sha256:" + "a" * 64,
             "browser_download_url": actualizar.DESCARGAS + f"v{version}/{n}"}], **k}

    def test_versiones(self):
        self.assertLess(actualizar.numeros("1.9.0"), actualizar.numeros("1.10"))
        for malo in ("", "1.x", "1..2", None, "1.2.3.4.5", "-1"):
            self.assertIsNone(actualizar.numeros(malo))
        self.assertEqual(actualizar.version_instalada(), "")          # esta es la copia del código

    def test_mas_nueva(self):
        def m(r, actual="1.1.0"):
            return actualizar.mas_nueva(json.dumps(r), actual)
        self.assertEqual(m(self.release())[0], "1.2.0")
        self.assertIsNone(m(self.release(), "1.2.0"))
        self.assertIsNone(m(self.release(), "2.0"))
        for k in ({"draft": True}, {"prerelease": True}, {"assets": []}, {"assets": None}, {"tag_name": "1.2.0"}, {"tag_name": 3}):
            self.assertIsNone(m(self.release(**k)), k)
        for campo, valor in (("name", "otro.exe"), ("digest", None), ("digest", "sha256:x"),
                             ("browser_download_url", "https://malo.example/Windows-Bar-Setup-1.2.0.exe")):
            r = self.release()
            r["assets"][0][campo] = valor
            self.assertIsNone(m(r), (campo, valor))
        for texto in ("", "[]", "no json", "null"):
            self.assertIsNone(actualizar.mas_nueva(texto, "1.0"))

    def test_descarga_comprobada(self):
        import hashlib
        with tempfile.TemporaryDirectory() as d:
            r = self.release()
            bueno = b"instalador"

            def traer(que):
                def f(url, ruta):
                    with open(ruta, "wb") as s:
                        s.write(json.dumps(r).encode() if url == actualizar.ULTIMO else que)
                return f
            r["assets"][0]["digest"] = "sha256:" + hashlib.sha256(bueno).hexdigest()
            c = os.path.join(d, "a")
            with self.assertRaises(ValueError):
                actualizar.descargar("1.0", c, traer=traer(b"otra cosa"))
            self.assertFalse([n for n in os.listdir(c) if "Setup" in n])
            v, ruta, suma = actualizar.descargar("1.0", c, traer=traer(bueno))
            self.assertEqual((v, actualizar.sha256(ruta)), ("1.2.0", suma))
            with open(ruta, "ab") as f:
                f.write(b"x")
            with self.assertRaises(ValueError):          # cambiado después
                actualizar.ejecutar(ruta, suma, os.path.join(d, "log"))
            self.assertIsNone(actualizar.descargar("1.0", c, saltar=lambda v: True, traer=traer(bueno)))
            self.assertFalse(os.path.exists(c))

    def test_intentos(self):
        t = actualizar.contar("", "1.2")
        self.assertEqual(actualizar.intentos(actualizar.contar(t, "1.2"), "1.2"), 2)
        self.assertEqual(actualizar.intentos(t, "1.3"), 0)
        self.assertEqual(actualizar.intentos("1.2:5:2000-01-01", "1.2"), 0)
        for basura in (None, "x", "a:b:c", 3):
            self.assertEqual(actualizar.intentos(basura, "1.2"), 0)

    def test_es_de(self):
        self.assertTrue(instalado.es_de("C:\\P\\Bar\\python\\pythonw.exe", "c:\\p\\bar"))
        self.assertFalse(instalado.es_de("C:\\P\\Barra2\\x.exe", "C:\\P\\Bar"))
        self.assertFalse(instalado.es_de("", "C:\\P"))

    def test_temas_propios(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "mio"))
            with open(os.path.join(d, "mio", "tema.json"), "w", encoding="utf-8") as f:
                f.write('{"nombre": "Mío"}')
            t = temas.cargar((temas.RAIZ, d, os.path.join(d, "no-existe")))
            self.assertEqual((t["mio"]["carpeta"], "tokyo" in t), (os.path.join(d, "mio"), True))

    def test_encuentra_a_claudito(self):
        self.assertEqual(claudito.encontrar(["C:\\no1", "C:\\no2"]), "C:\\no1")


class Atajos(unittest.TestCase):
    def setUp(self):
        self.l, self.t = atajos.Logica(), 0

    def pulsa(self, vk, win=False, mayus=False, ctrl=False, alt=False, suelta=True):
        vk = ord(vk) if isinstance(vk, str) else vk
        self.t += 0.1
        r = self.l.tecla(vk, True, win, mayus, ctrl, alt, self.t)
        if suelta:
            self.assertEqual(self.l.tecla(vk, False, win, mayus, ctrl, alt, self.t)[0], r[0])
        return r

    def test_numeros(self):
        self.assertEqual([self.pulsa(str(n), True)[1]["i"] for n in (1, 2, 9, 0)], [0, 1, 8, 9])
        self.assertEqual(self.pulsa("1"), (False, None))                 # sin Windows, se escribe
        a = self.pulsa("3", True, mayus=True, ctrl=True)[1]
        self.assertEqual((a["i"], a["mayus"], a["ctrl"], a["alt"]), (2, True, True, False))

    def test_mantenida_cuenta_una_vez(self):
        self.assertIsNotNone(self.pulsa("1", True, suelta=False)[1])
        self.assertEqual(self.pulsa("1", True, suelta=False), (True, None))
        self.assertEqual(self.pulsa("1", False, suelta=False)[0], True)      # soltó Windows antes que el número

    def test_lo_demas_sigue_siendo_de_windows(self):
        for k in "ADELRSVXNWI":
            self.assertEqual(self.pulsa(k, True), (False, None), k)
        for k in ({"ctrl": True}, {"alt": True}, {"mayus": True}):           # PowerToys, HDR...
            self.assertEqual(self.pulsa("T", True, **k), (False, None))
            self.assertEqual(self.pulsa("B", True, **k), (False, None))

    def test_elegir_con_flechas(self):
        self.assertEqual(self.pulsa("T", True), (True, {"op": "mover", "lista": "tareas", "paso": 1}))
        self.assertEqual(self.pulsa("T", True, mayus=True)[1]["paso"], -1)
        self.assertEqual(self.pulsa(0x27)[1]["paso"], 1)
        self.assertEqual(self.pulsa(0x25)[1]["paso"], -1)
        self.assertEqual(self.pulsa(0x10), (False, None))                    # Mayús sola no corta
        self.assertEqual(self.pulsa(0x0D), (True, {"op": "pulsar", "lista": "tareas"}))
        self.assertEqual(self.pulsa(0x0D), (False, None))                    # ya terminó
        self.pulsa("B", True)
        self.assertEqual(self.pulsa(0x5D)[1], {"op": "menu", "lista": "bandeja"})
        self.pulsa("B", True)
        self.assertEqual(self.pulsa(0x1B), (True, {"op": "cancelar"}))

    def test_escribir_cancela_sin_perder_la_tecla(self):
        self.pulsa("T", True)
        self.assertEqual(self.pulsa("H"), (False, {"op": "cancelar"}))
        self.assertEqual(self.pulsa("O"), (False, None))
        self.pulsa("T", True)
        self.t += atajos.ESPERA + 1
        self.assertEqual(self.pulsa(0x27), (False, {"op": "cancelar"}))      # caducó: la flecha no se pierde


class Cava(unittest.TestCase):
    @staticmethod
    def tono(hz, volumen, fs=24000):
        import math
        return [volumen * math.sin(2 * math.pi * hz * i / fs) for i in range(cava.MAX_MUESTRAS)]

    def mas_alta(self, hz, volumen=0.3):
        e = cava.Espectro(24000)
        e.anadir(self.tono(hz, volumen))
        for _ in range(20):
            b = e.fotograma(1 / 30)
        return b.index(max(b)), b

    def test_cada_tono_en_su_barra(self):
        sitios = [self.mas_alta(hz)[0] for hz in (70, 150, 400, 1000, 2500, 6000)]
        self.assertEqual(sitios, sorted(set(sitios)))
        self.assertTrue(sitios[0] <= 2 and sitios[-1] >= 13, sitios)

    def test_el_volumen_no_importa(self):
        self.assertGreater(max(self.mas_alta(440, 0.9)[1]), 95)
        self.assertGreater(max(self.mas_alta(440, 0.02)[1]), 95)

    def test_silencio_y_caida(self):
        e = cava.Espectro(24000)
        self.assertEqual(e.fotograma(0.03), [0] * cava.BARRAS)
        e.anadir(self.tono(440, 0.3))
        for _ in range(20):
            e.fotograma(0.03)
        e.anadir([0.0] * cava.MAX_MUESTRAS)
        maximos = [max(e.fotograma(0.03)) for _ in range(60)]
        self.assertEqual(maximos, sorted(maximos, reverse=True))
        self.assertEqual(maximos[-1], 0)

    def test_mono(self):
        datos = struct.pack("<8f", .5, .3, 9, 9, .1, .1, 9, 9)
        self.assertEqual([round(x, 3) for x in cava.a_mono(datos, 2, 2, True)], [0.4, 0.1])
        self.assertEqual(cava.a_mono(struct.pack("<2h", 16384, -16384), 1, 1, False), [0.5, -0.5])


class IconosDelTema(unittest.TestCase):
    @staticmethod
    def icono(colores):
        from PySide6.QtGui import QColor, QImage
        img = QImage(32, 32, QImage.Format.Format_ARGB32)
        img.fill(0)
        for i, c in enumerate(colores):
            for y in range(4, 28):
                for x in range(4 + i * 24 // len(colores), 4 + (i + 1) * 24 // len(colores)):
                    img.setPixelColor(x, y, QColor(c))
        return img

    def test_originales(self):
        for t in temas.cargar((temas.RAIZ,)).values():
            self.assertEqual(iconos.con_iconos(t, "originales")["estiloIconos"], "")
            self.assertEqual(iconos.con_iconos(t, "raro")["icono"], t["icono"])

    def test_se_ven_en_todos_los_temas(self):
        for ident, t in temas.cargar((temas.RAIZ,)).items():
            if t["pixelado"]:
                continue
            for m in cielo.MOMENTOS:
                for f in temas.FORMATOS:
                    for n in (100, 30, 0):
                        for detras in (0.05, 0.95):
                            x = temas.con_opacidad(temas.con_formato(temas.con_momento(t, m), f), n, detras)
                            base = temas.base_de(x)
                            if x["opacidad"] < 100:
                                base = tuple(b * n / 100 + detras * (1 - n / 100) for b in base[:3])
                            tonos = iconos.tonos(x)
                            self.assertGreater(max(temas.contraste(c, base) for c in tonos), 3, (ident, m, f, n, detras))
                            self.assertEqual(sorted(tonos, key=temas.luz), list(tonos), (ident, m))

    def test_bandeja_con_fondo(self):
        t = temas.cargar((temas.RAIZ,))["sakura"]
        fondo = temas.rgb(t["colores"]["fondoBandeja"])
        tonos = iconos.tonos_bandeja(t)
        self.assertGreater(temas.contraste(tonos[0], fondo), 1.8)
        self.assertGreater(temas.contraste(tonos[2], fondo), 7)
        self.assertEqual(iconos.tonos_bandeja(temas.cargar((temas.RAIZ,))["tokyo"]), iconos.tonos(temas.cargar((temas.RAIZ,))["tokyo"]))

    def test_dos_tonos(self):
        e = iconos.adaptar(self.icono(["#000000", "#808080", "#FFFFFF"]), "d-102030-405060-A0B0C0")
        self.assertEqual([e.pixelColor(x, 16).name() for x in (5, 27)], ["#102030", "#a0b0c0"])
        self.assertEqual(e.pixelColor(0, 0).alpha(), 0)
        plano = iconos.adaptar(self.icono(["#5865F2"]), "d-102030-405060-A0B0C0")
        self.assertEqual(plano.pixelColor(16, 16).name(), "#405060")          # de un color: el del medio

    def test_pixel(self):
        e = iconos.adaptar(self.icono(["#FF0000", "#00FF00"]), "p-17122E")
        self.assertEqual((e.width(), e.height()), (16, 16))
        usados = {e.pixelColor(x, y).getRgb()[:3] for x in range(16) for y in range(16) if e.pixelColor(x, y).alpha()}
        self.assertLessEqual(usados, set(iconos.PALETA))
        self.assertIn((0x17, 0x12, 0x2E), usados)

    def test_texto_raro(self):
        i = self.icono(["#123456"])
        for malo in ("", "x", "d-12", "p-zzzzzz"):
            self.assertEqual(iconos.adaptar(i, malo), i)
        for t in temas.cargar((temas.RAIZ,)).values():
            e = iconos.estilo(t, "tema")
            self.assertTrue(e.startswith("~"))
            self.assertNotEqual(iconos.adaptar(i, e[1:]), i)


class Tiempo(unittest.TestCase):
    def test_leer(self):
        def r(codigo, grados=21.6, dia=1):
            return tiempo.leer_tiempo(json.dumps({"current": {"weather_code": codigo, "temperature_2m": grados, "is_day": dia}}))
        self.assertEqual(r(0), {"hay": True, "icono": "☀️", "grados": "22°", "texto": "Despejado"})
        self.assertEqual(r(0, -0.4, 0)["grados"], "0°")
        self.assertEqual([r(c)["texto"] for c in (3, 45, 61, 75, 95, 500)], ["Nublado", "Niebla", "Lluvia", "Nieve", "Tormenta", "Tormenta"])
        for malo in ("", "{}", "[]", "null", '{"current": {"weather_code": "x"}}'):
            self.assertIsNone(tiempo.leer_tiempo(malo))
            self.assertIsNone(tiempo.leer_ciudad(malo))
        c = tiempo.leer_ciudad('{"results": [{"name": "X", "latitude": 1.5, "longitude": -3}]}')
        self.assertEqual(c, {"nombre": "X", "lat": 1.5, "lon": -3.0})
        self.assertTrue(tiempo.ciudad_valida(c))

    def test_ajuste(self):
        for malo in ({"nombre": "x"}, {"nombre": "x", "lat": "1", "lon": 2}, "Lima", {"nombre": "x", "lat": 1, "lon": 999}):
            self.assertEqual(ajustes.normalizar({"ciudad": malo}, {"tokyo": 1}, temas.FORMATOS)["ciudad"], {})


class Sitio(unittest.TestCase):
    P = (1920, -468, 1200, 1920)

    def test_franja_y_margenes(self):
        self.assertEqual(sitio.franja("abajo", (0, 0, 1920, 1080), 48), (0, 1032, 1920, 48))
        self.assertEqual(sitio.franja("derecha", self.P, 60), (3060, -468, 60, 1920))
        self.assertEqual(sitio.margenes("arriba", 48), (0, 48, 0, 0))
        self.assertEqual(sitio.margenes("derecha", 60), (0, 0, 60, 0))

    def test_ventanitas_dentro_y_sin_tapar_la_barra(self):
        for lado in sitio.LADOS:
            bx, by, ban, bal = sitio.franja(lado, self.P, 60)
            for ancla in ((1920, -468), (3119, 1451), (2500, 500)):
                for an, al in ((200, 100), (730, 640)):
                    x, y = sitio.colocar(lado, ancla, an, al, self.P, 60)
                    self.assertTrue(1920 <= x and x + an <= 3120 and -468 <= y and y + al <= 1452, (lado, ancla))
                    self.assertFalse(x < bx + ban and bx < x + an and y < by + bal and by < y + al, (lado, ancla))

    def test_mas_cerca(self):
        p = (0, 0, 1920, 1080)
        self.assertEqual([sitio.mas_cerca(q, p) for q in ((960, 1070), (960, 5), (4, 500), (1915, 500))],
                         ["abajo", "arriba", "izquierda", "derecha"])

    def test_temas_en_cada_lado(self):
        for t in temas.cargar().values():
            for f in temas.FORMATOS:
                for lado in sitio.LADOS:
                    n = temas.con_posicion(temas.con_formato(t, f), lado)
                    self.assertEqual(n["vertical"], lado in ("izquierda", "derecha"))
                    self.assertLessEqual(n["alto"] + n["margen"], temas.alto_total(n))
                    if n["vertical"]:
                        self.assertEqual((temas.alto_total(n), n["fondoUrl"]), (46 if n["compacto"] else 60, ""))
        self.assertEqual(temas.con_posicion(t, "raro")["lado"], "abajo")


class Orden(unittest.TestCase):
    def test_fusionar(self):
        f = ajustes.fusionar_orden
        self.assertEqual(f([], ["a", "b"]), ["a", "b"])
        self.assertEqual(f(["a", "b", "c"], ["c", "a", "b"]), ["c", "a", "b"])
        # x no se ve: sigue detrás de su vecino b
        self.assertEqual(f(["a", "b", "x", "c"], ["c", "b", "a"]), ["c", "b", "x", "a"])
        self.assertEqual(f(["x", "a"], ["b", "a"]), ["x", "b", "a"])
        self.assertEqual(f(["a"], ["a", "nuevo"]), ["a", "nuevo"])
        for n in (ajustes.MAX_ORDEN, ajustes.MAX_ORDEN + 50):
            r = f([f"v{i}" for i in range(n)], ["a", "b"])
            self.assertLessEqual(len(r), ajustes.MAX_ORDEN)
            self.assertTrue({"a", "b"} <= set(r))

    def test_manda_el_elegido(self):
        v = Programas.v
        fijo = {"clave": "zen", "exe": "zen.exe", "nombre": "Zen", "ruta": "r", "icono": ""}
        info = [v(1, "disc"), v(2, "steam"), v(3, "nota")]

        def orden(*e):
            return [x["clave"] for x in programas.agrupar(info, [fijo], True, {}, e)]
        self.assertEqual(orden(), ["zen", "disc", "steam", "nota"])
        self.assertEqual(orden("steam", "zen"), ["steam", "zen", "disc", "nota"])
        self.assertEqual(orden("cerrado", "nota"), ["nota", "zen", "disc", "steam"])
        # sin agrupar, las ventanas de un programa siguen juntas
        info.append(v(9, "disc"))
        f = programas.agrupar(info, [], False, {}, ["nota", "disc"])
        self.assertEqual([x["key"] for x in f], ["3", "1", "9", "2"])


class Reinicio(unittest.TestCase):
    def test_tope(self):
        self.assertTrue(vigilante.puede_reiniciar([], 1000))
        self.assertTrue(vigilante.puede_reiniciar([990, 995], 1000))
        self.assertFalse(vigilante.puede_reiniciar([990, 995, 999], 1000))
        self.assertTrue(vigilante.puede_reiniciar([10, 20, 30], 1000))          # ya pasó un rato
        self.assertTrue(vigilante.puede_reiniciar(["x", None, 5000], 1000))     # basura o futuro


class Recursos(unittest.TestCase):
    def test_gpu(self):
        g = sistema.Gpu()
        v = g.percent()
        self.assertTrue(v is None or 0 <= v <= 100)

    def test_inactividad(self):
        self.assertGreaterEqual(win.segundos_inactivo(), 0)


class Cielo(unittest.TestCase):
    def test_momentos(self):
        for mes in range(1, 13):
            self.assertEqual([cielo.momento(h, mes) for h in (0, 3, 12, 15, 23)],
                             ["noche", "noche", "dia", "dia", "noche"])
            visto = []
            for h in range(0, 24 * 60):
                m = cielo.momento(h / 60, mes)
                if not visto or visto[-1] != m:
                    visto.append(m)
            self.assertEqual(visto, ["noche", "amanecer", "dia", "atardecer", "noche"])


class Alineacion(unittest.TestCase):
    def test_centro_e_izquierda(self):
        for ident, t in temas.cargar().items():
            todos = sorted(m for z in t["modulos"].values() for g in z for m in g)
            for centro in (True, False):
                n = temas.con_alineacion(t, centro)
                self.assertEqual(sorted(m for z in n["modulos"].values() for g in z for m in g), todos, ident)
                zona = [m for g in n["modulos"]["centro" if centro else "izquierda"] for m in g]
                self.assertEqual(zona[:2], ["inicio", "tareas"], ident)
                izq = [m for g in n["modulos"]["izquierda"] for m in g]
                for m in ("widgets", "claudito", "sistema"):
                    self.assertEqual(m in izq, centro and m in todos, (ident, m))

    def test_una_isla(self):
        for ident, t in temas.cargar().items():
            for f in ("isla", "isla_compacta"):
                for centro in (True, False):
                    n = temas.con_alineacion(temas.con_formato(t, f), centro)
                    zona = [m for g in n["modulos"]["centro" if centro else "izquierda"] for m in g]
                    self.assertEqual((zona[:2], n["centrado"], n["unica"]), (["inicio", "tareas"], centro, True), ident)
                    self.assertGreater(temas.rgb(n["colores"]["isla"])[3], 0.5)

    def test_lee_windows(self):
        self.assertIn(temas.windows_centrado(), (True, False))


class Vidrio(unittest.TestCase):
    def test_velo(self):
        v = [vidrio.velo(n, [0.2], False) for n in vidrio.NIVELES]
        self.assertEqual(v, sorted(v))
        self.assertEqual(set(vidrio.NIVELES), set(vidrio.NOMBRES))
        self.assertEqual(vidrio.velo("raro", [0.2], False), vidrio.velo("normal", [0.2], False))

    @staticmethod
    def _contraste(fondo, texto):
        def lin(x):
            return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
        a, b = sorted((lin(fondo) + 0.05, lin(texto) + 0.05))
        return b / a

    def test_el_texto_se_lee(self):
        for nivel in vidrio.NIVELES:
            for i in range(101):
                luz = i / 100
                clara = vidrio.es_clara([luz], False)
                v = vidrio.velo(nivel, [luz], clara)
                fondo = luz * (1 - v) + (1 if clara else 0.07) * v
                self.assertGreater(self._contraste(fondo, 0.085 if clara else 1), 4.5, (nivel, luz))

    def test_clara(self):
        self.assertTrue(vidrio.es_clara([0.9, 0.7], False))
        self.assertFalse(vidrio.es_clara([0.9, 0.2], False))      # mitad oscura: texto blanco
        self.assertNotEqual(vidrio.es_clara([0.58], True), vidrio.es_clara([0.58], False))
        self.assertFalse(vidrio.es_clara([], True))


class Claude(unittest.TestCase):
    def test_lista(self):
        def v(s, m, ts):
            return {"session": s, "mode": m, "ts": ts, "project": "p" + s}
        vistas = {x["session"]: x for x in (v("a", "idle", 9), v("b", "waiting", 1), v("c", "sleep", 5))}
        self.assertEqual([x["id"] for x in claudito.lista_sesiones(vistas, {"a": 1, "b": 1})], ["b", "a"])
        self.assertEqual([x["id"] for x in claudito.lista_sesiones(vistas, None)], ["b", "a"])

    def test_cadena(self):
        t = {5: (4, "claude.exe"), 4: (3, "pwsh.exe"), 3: (2, "windowsterminal.exe"), 2: (1, "explorer.exe")}
        self.assertEqual(sesiones.cadena(5, t), [5, 4, 3])
        self.assertEqual(sesiones.cadena(1, {1: (2, "a"), 2: (1, "b")}), [1, 2])

    def test_textos(self):
        self.assertEqual([panel_claude.miles(n) for n in (5, 1500, 2_400_000)], ["5", "1.5 k", "2.4 M"])
        self.assertEqual(panel_claude.falta(1000 + 7800, 1000), "2 h 10 min")
        self.assertEqual(panel_claude.falta(1000 + 90000, 1000), "1 d 1 h")
        self.assertEqual(panel_claude.falta(None, 0), "")


class Ajustes(unittest.TestCase):
    T = {"tokyo": 1, "bosque": 1, "liquid": 1}
    F = temas.FORMATOS

    def test_pasa_el_formato_antiguo(self):
        a = ajustes.normalizar({"tema": "liquid", "formato": "compacta"}, self.T, self.F)
        self.assertEqual(a["formatos"], {"liquid": "compacta"})
        self.assertNotIn("formato", a)
        a = ajustes.normalizar({"tema": "liquid", "formato": "tema"}, self.T, self.F)
        self.assertEqual(a["formatos"], {})

    def test_aguanta_basura(self):
        for d in (None, [], "x", {"tema": 3, "formatos": [], "fijados": ["x", {}], "quitados": [1]},
                  {"tema": "neon", "formatos": {"neon": "islas", "tokyo": "raro"}}):
            a = ajustes.normalizar(d, self.T, self.F)
            self.assertEqual((a["tema"], a["formatos"], a["fijados"], a["quitados"]), ("tokyo", {}, [], []))

    def test_no_comparte_los_valores_por_defecto(self):
        ajustes.normalizar(None, self.T, self.F)["formatos"]["x"] = 1
        self.assertEqual(ajustes.DEFECTO["formatos"], {})

    def test_anclar_y_desanclar(self):
        a = ajustes.normalizar(None, self.T, self.F)
        w = [{"clave": "zen"}]
        ajustes.fijar(a, {"clave": "steam", "exe": "s"}, ["zen"])
        ajustes.fijar(a, {"clave": "steam", "exe": "s"}, ["zen"])
        self.assertEqual([f["clave"] for f in ajustes.lista_fijos(a, w)], ["zen", "steam"])
        ajustes.soltar(a, "zen", ["zen"])
        ajustes.soltar(a, "steam", ["zen"])
        self.assertEqual(ajustes.lista_fijos(a, w), [])
        ajustes.fijar(a, {"clave": "zen", "exe": "z"}, ["zen"])
        self.assertEqual([f["clave"] for f in ajustes.lista_fijos(a, w)], ["zen"])

    def test_clave_de_la_tienda(self):
        v = "C:\\Program Files\\WindowsApps\\Spotify_1.%d_x64\\Spotify.exe"
        self.assertEqual(win.clave_exe(v % 1), win.clave_exe(v % 2))
        self.assertEqual(win.clave_exe("C:\\A.EXE"), "c:\\a.exe")


class Previa(unittest.TestCase):
    def test_encajar(self):
        self.assertEqual(vista.encajar(1920, 1080), (240, 135))
        self.assertEqual(vista.encajar(600, 1200), (75, 150))
        self.assertEqual(vista.encajar(100, 80), (100, 80))
        self.assertEqual(vista.encajar(0, 0), (0, 0))

    def test_disponer(self):
        for n in (1, 2, 3, 5, 8, 20):
            for ancho in (1896, 1176):
                for tam in ((1920, 1080), (600, 1200), (0, 0)):
                    t, r, an, al = vista.disponer([tam] * n, ancho)
                    self.assertEqual((len(t), len(r)), (n, n))
                    self.assertLessEqual(an, ancho)
                    for i, x in enumerate(t):
                        self.assertTrue(x.right() < an and x.bottom() < al, (n, ancho, tam))
                        self.assertTrue(r[i].isEmpty() or x.contains(r[i]))
                        self.assertFalse(any(x.intersects(y) for y in t[:i]))

    def test_estructura_de_dwm(self):
        self.assertEqual(vista.ctypes.sizeof(vista.PROPS), 45)


class Dibujo(unittest.TestCase):
    def test_adaptar(self):
        with open(claudito.PERSONAJE, encoding="utf-8") as f:
            n = claudito.adaptar(f.read())
        self.assertIn("Math.max(minimo", n)
        self.assertIsNone(claudito.adaptar("otra cosa"))


class Ropa(unittest.TestCase):
    def test_elegir(self):
        r = claudito.elegir_ropa
        self.assertEqual(r("auto", "true", "true", "autumn"), {"gorro": "autumn", "traje": "autumn"})
        self.assertEqual(r("winter", "false", "true", "autumn"), {"gorro": "", "traje": "winter"})
        self.assertEqual(r("none", "true", "true", "autumn"), {"gorro": "", "traje": ""})


class Pantalla(unittest.TestCase):
    def test_cubre(self):
        self.assertTrue(win.covers((0, 0, 1920, 1080), (0, 0, 1920, 1080)))
        self.assertFalse(win.covers((0, 0, 1920, 1032), (0, 0, 1920, 1080)))

    def test_alto_reservado(self):
        self.assertEqual(win.alto_reservado((0, 1032, 1920, 1080), (0, 0, 1920, 1080)), 48)
        self.assertIsNone(win.alto_reservado((0, 1078, 1920, 1126), (0, 0, 1920, 1080)))   # ocultación automática
        self.assertIsNone(win.alto_reservado((0, 0, 1920, 48), (0, 0, 1920, 1080)))        # arriba

    def test_sitio_maximizada(self):
        p = (0, 0, 1920, 1080)
        areas = {"abajo": (0, 0, 1920, 1032), "arriba": (0, 48, 1920, 1080), "izquierda": (60, 0, 1920, 1080),
                 "derecha": (0, 0, 1860, 1080), "compacta": (0, 0, 1920, 1050)}
        for sobra in (0, 7, 8):
            for a in areas.values():
                antes = (a[0] - sobra, a[1] - sobra, a[2] + sobra, a[3] + sobra)
                for b in areas.values():
                    n = (b[0] - sobra, b[1] - sobra, b[2] + sobra, b[3] + sobra)
                    self.assertEqual(win.sitio_maximizada(antes, b, p), n if n != antes else None)
        self.assertIsNone(win.sitio_maximizada((100, 100, 900, 700), areas["abajo"], p))
        # segunda pantalla, con coordenadas negativas
        self.assertEqual(win.sitio_maximizada((1912, -476, 3128, 1412), (1980, -468, 3120, 1452), (1920, -468, 3120, 1452)),
                         (1972, -476, 3128, 1460))

    def test_encuentra_la_barra_de_explorer(self):
        self.assertTrue(win.taskbars())


if __name__ == "__main__":
    unittest.main()
