"""py -m unittest discover -s tests   (no toca la barra de Windows)"""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from barra import ajustes, bandeja, claudito, temas, vista, win  # noqa: E402


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
        self.assertEqual(list(temas.cargar()), ["tokyo", "catppuccin", "sakura", "liquid", "capsula", "terminal", "pixel", "bosque",
                                                "minimal", "camaleon"])

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

    def test_estructura_de_dwm(self):
        self.assertEqual(vista.ctypes.sizeof(vista.PROPS), 45)


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
