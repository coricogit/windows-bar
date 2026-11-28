"""La isla dinámica: una píldora que sale junto a la barra cuando pasa algo
(canción nueva, Claude esperando, red, batería), crece, se queda un momento
y se recoge. No coge el foco; un clic hace lo que toque.

Cada aviso lleva un tipo (musica, ok, aviso, error, info) que le da el color:
el del icono en su baldosa, el del borde y el de la rayita que marca cuánto le
queda. El icono es un glifo de Segoe Fluent Icons o, si lo hay, la imagen del
programa (`imagen`, una QImage)."""
import math
import time

from PySide6.QtCore import QEasingCurve, QRect, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QAccessible, QAccessibleEvent, QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from . import win

ALTO, MIN, MAX, DURA = 46, 150, 460, 3600
SOMBRA = 8                       # margen alrededor de la píldora para la sombra
COLORES = {"ok": "#3DD68C", "aviso": "#FFB020", "musica": "", "info": "", "error": ""}   # "" = del tema
CHEVRON = ""
# Anterior, pausa o seguir y siguiente (Segoe Fluent Icons), en la música al pasar el ratón.
ANTERIOR, PAUSA, SEGUIR, SIGUIENTE = "", "", "", ""
BOTON = 26                       # ancho de cada uno


def ancho_para(titulo, detalle, medir):
    """Lo que necesita la píldora; `medir(texto, negrita)` da el ancho."""
    texto = max(medir(titulo, True), medir(detalle, False) if detalle else 0)
    return int(max(MIN, min(MAX, texto + 76)))


def color_de(tipo, colores):
    """El color de un tipo de aviso con los colores del tema. Con el tema ya ajustado
    (temas.con_accesible) trae los suyos, con contraste 3:1 sobre el fondo."""
    propio = colores.get({"ok": "isla_ok", "aviso": "isla_aviso", "error": "isla_alerta"}.get(tipo, "isla_acento"))
    if propio:
        return QColor(propio)
    fijo = COLORES.get(tipo, "")
    if fijo:
        return QColor(fijo)
    return QColor(colores.get("alerta" if tipo == "error" else "acento") or "#4CC2FF")


class Isla(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.WindowDoesNotAcceptFocus | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._aviso, self._col, self._fuente, self._ancho = None, {}, "Segoe UI", MIN
        self._abierta = 0.0                    # 0 recogida ... 1 del todo
        self._encima, self._desde, self._dura = False, 0.0, DURA
        self._botones, self._sobre = [], None         # [(QRectF, orden)] de la música; el que tiene el ratón
        self.setMouseTracking(True)
        self.setProperty("sinMarco", True)       # Esquinas (barra.pyw) no la toca: dibuja su propia forma
        self._anim = QVariantAnimation(self, duration=260)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim.valueChanged.connect(self._mover)
        self._anim.finished.connect(self._acabado)
        self._quitar = QTimer(self, singleShot=True, timeout=self.recoger)
        self._latido = QTimer(self, interval=66, timeout=self.update)    # barras de música y la rayita

    def showEvent(self, e):
        try:
            win.sin_marco(int(self.winId()))      # sin el borde gris de Windows 11 alrededor de la ventana
        except Exception:
            pass
        super().showEvent(e)

    def avisar(self, aviso, poner, tema):
        """`aviso`: {"icono", "titulo", "detalle", "tipo", "imagen", "fuente_icono", "hacer", "dura"};
        `poner(an, al)` da la esquina."""
        self._aviso, self._col, self._fuente = aviso, tema["colores"], tema["fuente"]
        self._escala = max(1.0, min(1.6, aviso.get("escala", 1.0)))     # el «Tamaño del texto» de Windows
        f = QFontMetrics(self._f(13, True)), QFontMetrics(self._f(11))
        extra = 3 * BOTON + 6 if aviso.get("controles") else 22 if aviso.get("hacer") or aviso.get("tipo") == "musica" else 0
        self._ancho = min(MAX, ancho_para(aviso["titulo"], aviso.get("detalle", ""),
                                          lambda t, b: (f[0] if b else f[1]).horizontalAdvance(t)) + extra)
        self._alto = round(ALTO * (1 + (self._escala - 1) * 0.6))
        an, al = self._ancho + 2 * SOMBRA, self._alto + 2 * SOMBRA
        self.setGeometry(QRect(*poner(an, al), an, al))
        if not self.isVisible() or self._anim.endValue() == 0.0:
            self._ir(1.0)
        self._dura, self._desde = aviso.get("dura", DURA), time.monotonic()
        self.update()
        self.show()
        if self._dura > 0:                       # 0: se queda hasta que la cierres (WCAG 2.2.1)
            self._quitar.start(self._dura)
        else:
            self._quitar.stop()
        if self._dura > 0 or aviso.get("tipo") == "musica":   # la rayita o las barras de la música
            self._latido.start()
        else:
            self._latido.stop()
        # Para el lector de pantalla, como mensaje de estado (WCAG 4.1.3).
        self.setAccessibleName(aviso["titulo"] + (". " + aviso["detalle"] if aviso.get("detalle") else ""))
        try:
            QAccessible.updateAccessibility(QAccessibleEvent(self, QAccessible.Event.Alert))
        except Exception:
            pass

    def recoger(self):
        if self.isVisible():
            self._ir(0.0)

    def _ir(self, a):
        self._anim.stop()
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack if a else QEasingCurve.Type.InCubic)
        self._anim.setDuration(300 if a else 180)
        self._anim.setStartValue(self._abierta)
        self._anim.setEndValue(a)
        self._anim.start()

    def _mover(self, v):
        self._abierta = float(v)
        self.update()

    def _acabado(self):
        if self._anim.endValue() == 0.0:
            self._latido.stop()
            self.hide()

    def _f(self, px, negrita=False, familia=None):
        f = QFont(familia or self._fuente)
        f.setPixelSize(round(px * getattr(self, "_escala", 1.0)))
        if negrita:
            f.setWeight(QFont.Weight.DemiBold)
        return f

    def enterEvent(self, e):
        self._encima = True
        self._quitar.stop()             # mientras la miras, no se va
        self.update()

    def leaveEvent(self, e):
        self._encima, self._sobre = False, None
        if self._dura > 0:
            self._dura, self._desde = 1500, time.monotonic()
            self._quitar.start(1500)
        self.update()

    def mouseMoveEvent(self, e):
        sobre = next((o for r, o in self._botones if r.contains(e.position())), None)
        if sobre != self._sobre:
            self._sobre = sobre
            self.update()

    def mousePressEvent(self, e):
        orden = next((o for r, o in self._botones if r.contains(e.position())), None)
        if orden and e.button() == Qt.MouseButton.LeftButton:
            # Un botón de la música: la isla se queda, y pausa/seguir cambia al momento.
            self._aviso["controles"](orden)
            if orden == "pausa":
                self._aviso["sonando"] = not self._aviso.get("sonando", True)
            self.update()
            return
        hacer = self._aviso and self._aviso.get("hacer")
        self.recoger()
        if hacer and e.button() == Qt.MouseButton.LeftButton:
            hacer()

    # ----- dibujo -----
    def paintEvent(self, e):
        if not self._aviso:
            return
        a = max(0.0, self._abierta)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = {k: QColor(v) for k, v in self._col.items() if v}
        tipo = self._aviso.get("tipo", "info")
        tono = color_de(tipo, self._col)
        fondo = QColor(c.get("fondo", QColor("#202020")))
        fondo.setAlpha(250)
        # Crece desde una pastilla del centro.
        alto = getattr(self, "_alto", ALTO)
        an = alto + (self._ancho - alto) * min(1.0, a)
        caja = QRectF(SOMBRA + (self._ancho - an) / 2, SOMBRA + 1, an, alto - 2)
        r = caja.height() / 2
        self._sombra(p, caja, r, a)
        # Sin contorno: la separa del fondo la sombra; al pasar el ratón, un filo de su color.
        borde = QColor(tono)
        borde.setAlphaF(0.5)
        p.setPen(QPen(borde, 1) if self._encima else Qt.PenStyle.NoPen)
        p.setBrush(fondo)
        p.drawRoundedRect(caja.adjusted(0.5, 0.5, -0.5, -0.5), r, r)

        # El icono, en una baldosa redondeada del color del aviso.
        lado = caja.height() - 14
        baldosa = QRectF(caja.left() + 7, caja.top() + 7, lado, lado)
        imagen = self._aviso.get("imagen")
        tinte = QColor(tono)
        tinte.setAlphaF(0.10 if imagen is not None else 0.20)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(tinte)
        p.drawRoundedRect(baldosa, lado / 2, lado / 2)
        if imagen is not None and not imagen.isNull() and tipo == "musica":
            p.save()                     # la carátula llena la baldosa, recortada en redondo
            recorte = QPainterPath()
            recorte.addRoundedRect(baldosa, lado * 0.28, lado * 0.28)
            p.setClipPath(recorte)
            p.drawImage(baldosa, imagen)
            p.restore()
        elif imagen is not None and not imagen.isNull():
            m = lado * 0.18
            p.drawImage(baldosa.adjusted(m, m, -m, -m), imagen)
        else:
            p.setFont(self._f(15, False, self._aviso.get("fuente_icono", "Segoe Fluent Icons")))
            p.setPen(tono)
            p.drawText(baldosa, Qt.AlignmentFlag.AlignCenter, self._aviso.get("icono", ""))
        if a < 0.55:                     # el texto aparece cuando ya hay sitio
            p.end()
            return
        p.setOpacity(min(1.0, (a - 0.55) / 0.35))

        # A la derecha: barras si suena música, una flecha si el clic hace algo.
        derecha, self._botones = 0, []
        if self._aviso.get("controles"):
            derecha = 3 * BOTON + 6
            if self._encima:
                self._controles(p, caja, tono, c)
            else:
                self._barras(p, QRectF(caja.right() - 16 - derecha / 2 - 7, caja.top() + 13, 14, caja.height() - 26), tono)
        elif tipo == "musica":
            derecha = 22
            self._barras(p, QRectF(caja.right() - 30, caja.top() + 13, 14, caja.height() - 26), tono)
        elif self._aviso.get("hacer"):
            derecha = 20
            p.setFont(self._f(10, False, "Segoe Fluent Icons"))
            p.setPen(c.get("isla_tenue", c.get("tenue", QColor("#A0A0A0"))))
            p.drawText(QRectF(caja.right() - 30, caja.top(), 16, caja.height()), Qt.AlignmentFlag.AlignCenter, CHEVRON)

        texto = QRectF(baldosa.right() + 10, caja.top(), caja.right() - baldosa.right() - 26 - derecha, caja.height())
        detalle = self._aviso.get("detalle", "")
        medida = QFontMetrics(self._f(13, True))
        p.setFont(self._f(13, True))
        p.setPen(c.get("isla_texto", c.get("texto", QColor("#FFFFFF"))))
        arriba = QRectF(texto.left(), texto.top() + (5 if detalle else 0), texto.width(), texto.height() / 2 if detalle else texto.height())
        p.drawText(arriba, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   medida.elidedText(self._aviso["titulo"], Qt.TextElideMode.ElideRight, int(texto.width())))
        if detalle:
            p.setFont(self._f(11))
            p.setPen(c.get("isla_tenue", c.get("tenue", QColor("#A0A0A0"))))
            abajo = QRectF(texto.left(), texto.center().y() - 1, texto.width(), texto.height() / 2 - 4)
            p.drawText(abajo, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       QFontMetrics(self._f(11)).elidedText(detalle, Qt.TextElideMode.ElideRight, int(texto.width())))

        # Lo que le queda, como una rayita abajo (quieta mientras la miras).
        if not self._encima and self._dura > 0 and self._quitar.isActive():
            queda = max(0.0, 1 - (time.monotonic() - self._desde) * 1000 / self._dura)
            raya = QColor(tono)
            raya.setAlphaF(0.55)
            ancho = (caja.width() - 2 * r) * queda
            pluma = QPen(raya, 2)
            pluma.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pluma)
            y = caja.bottom() - 2.5
            p.drawLine(int(caja.left() + r), int(y), int(caja.left() + r + ancho), int(y))
        p.end()

    def _controles(self, p, caja, tono, c):
        """Anterior, pausa o seguir y siguiente; el del medio, en su círculo de color."""
        sonando = self._aviso.get("sonando", True)
        x = caja.right() - 16 - 3 * BOTON
        p.save()
        for i, (glifo, orden) in enumerate(((ANTERIOR, "anterior"), (PAUSA if sonando else SEGUIR, "pausa"),
                                            (SIGUIENTE, "siguiente"))):
            r = QRectF(x + i * BOTON, caja.top() + (caja.height() - BOTON) / 2, BOTON, BOTON)
            self._botones.append((r, orden))
            p.setPen(Qt.PenStyle.NoPen)
            if orden == "pausa":
                p.setBrush(tono.lighter(115) if self._sobre == orden else tono)
                p.drawEllipse(r.adjusted(1, 1, -1, -1))
            elif self._sobre == orden:
                encima = QColor(c.get("isla_texto", c.get("texto", QColor("#FFFFFF"))))
                encima.setAlphaF(0.12)
                p.setBrush(encima)
                p.drawEllipse(r.adjusted(1, 1, -1, -1))
            fondo = QColor(c.get("fondo", QColor("#202020")))
            fondo.setAlpha(255)
            p.setPen(fondo if orden == "pausa" else c.get("isla_texto", c.get("texto", QColor("#FFFFFF"))))
            p.setFont(self._f(10 if orden == "pausa" else 11, False, "Segoe Fluent Icons"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, glifo)
        p.restore()

    def _sombra(self, p, caja, r, a):
        """Una sombra suave: capas cada vez más anchas y más transparentes."""
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(SOMBRA, 0, -2):
            sombra = QColor(0, 0, 0, int(14 * min(1.0, a) * (1 - i / (SOMBRA + 1))))
            p.setBrush(sombra)
            p.drawRoundedRect(caja.adjusted(-i, -i + 2, i, i + 2), r + i, r + i)
        p.restore()

    def _barras(self, p, zona, tono):
        """Tres barritas que bailan, para las canciones."""
        t = time.monotonic()
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(tono)
        ancho = 3
        for i in range(3):
            alto = zona.height() * (0.35 + 0.65 * abs(math.sin(t * (2.6 + i * 0.9) + i * 1.3)))
            camino = QPainterPath()
            camino.addRoundedRect(QRectF(zona.left() + i * (ancho + 2.5), zona.bottom() - alto, ancho, alto), 1.5, 1.5)
            p.drawPath(camino)
        p.restore()
