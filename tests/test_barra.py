"""py -m unittest discover -s tests   (no toca la barra de Windows)"""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from barra import ajustes, arranque, bandeja, cielo, claudito, panel_claude, programas, selector, sesiones, sistema, temas, vidrio, vigilante, vista, win  # noqa: E402


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
        self.assertEqual(list(temas.cargar()), ["tokyo", "grafito", "papel", "nordico", "sakura", "pixel",
                                                "bosque"])

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
                    self.assertEqual(n["forma"] == "islas", f.startswith("islas"))
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
                for m in ("claudito", "sistema"):
                    self.assertEqual(m in izq, centro and m in todos, (ident, m))

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

    def test_borde_maximizada(self):
        area = (0, 0, 1920, 1044)
        self.assertEqual(win.borde_maximizada((-8, -8, 1928, 1040), area), 1052)
        self.assertIsNone(win.borde_maximizada((-8, -8, 1928, 1052), area))
        self.assertIsNone(win.borde_maximizada((100, 100, 900, 700), area))

    def test_encuentra_la_barra_de_explorer(self):
        self.assertTrue(win.taskbars())


if __name__ == "__main__":
    unittest.main()
