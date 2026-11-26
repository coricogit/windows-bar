"""La isla dinámica: una píldora que sale junto a la barra cuando pasa algo
(canción nueva, Claude esperando, red, batería), crece, se queda un momento
y se recoge. No coge el foco; un clic hace lo que toque."""
from PySide6.QtCore import QEasingCurve, QRect, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QWidget

ALTO, MIN, MAX, DURA = 46, 150, 460, 3600


def ancho_para(titulo, detalle, medir):
    """Lo que necesita la píldora; `medir(texto, negrita)` da el ancho."""
    texto = max(medir(titulo, True), medir(detalle, False) if detalle else 0)
    return int(max(MIN, min(MAX, texto + 76)))


class Isla(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.WindowDoesNotAcceptFocus | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._aviso, self._col, self._fuente, self._ancho = None, {}, "Segoe UI", MIN
        self._abierta = 0.0                    # 0 recogida ... 1 del todo
        self._anim = QVariantAnimation(self, duration=260)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim.valueChanged.connect(self._mover)
        self._anim.finished.connect(self._acabado)
        self._quitar = QTimer(self, singleShot=True, timeout=self.recoger)

    def avisar(self, aviso, poner, tema):
        """`aviso`: {"icono", "fuente_icono", "titulo", "detalle", "hacer"};
        `poner(an, al)` da la esquina."""
        self._aviso, self._col, self._fuente = aviso, tema["colores"], tema["fuente"]
        f = QFontMetrics(self._f(13, True)), QFontMetrics(self._f(11))
        self._ancho = ancho_para(aviso["titulo"], aviso.get("detalle", ""),
                                 lambda t, b: (f[0] if b else f[1]).horizontalAdvance(t))
        self.setGeometry(QRect(*poner(self._ancho, ALTO), self._ancho, ALTO))
        if not self.isVisible() or self._anim.endValue() == 0.0:
            self._ir(1.0)
        self.update()
        self.show()
        self._quitar.start(aviso.get("dura", DURA))

    def recoger(self):
        if self.isVisible():
            self._ir(0.0)

    def _ir(self, a):
        self._anim.stop()
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack if a else QEasingCurve.Type.InCubic)
        self._anim.setDuration(260 if a else 180)
        self._anim.setStartValue(self._abierta)
        self._anim.setEndValue(a)
        self._anim.start()

    def _mover(self, v):
        self._abierta = float(v)
        self.update()

    def _acabado(self):
        if self._anim.endValue() == 0.0:
            self.hide()

    def _f(self, px, negrita=False, familia=None):
        f = QFont(familia or self._fuente)
        f.setPixelSize(px)
        f.setBold(negrita)
        return f

    def enterEvent(self, e):
        self._quitar.stop()             # mientras la miras, no se va

    def leaveEvent(self, e):
        self._quitar.start(1500)

    def mousePressEvent(self, e):
        hacer = self._aviso and self._aviso.get("hacer")
        self.recoger()
        if hacer and e.button() == Qt.MouseButton.LeftButton:
            hacer()

    def paintEvent(self, e):
        if not self._aviso:
            return
        a = max(0.0, self._abierta)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = {k: QColor(v) for k, v in self._col.items() if v}
        fondo = QColor(c["fondo"])
        fondo.setAlpha(250)
        # Crece desde una pastilla del centro.
        an = ALTO + (self._ancho - ALTO) * min(1.0, a)
        caja = QRectF((self._ancho - an) / 2, 1, an, ALTO - 2)
        p.setPen(QPen(c["acento"], 1.2))
        p.setBrush(fondo)
        p.drawRoundedRect(caja.adjusted(0.5, 0.5, -0.5, -0.5), caja.height() / 2, caja.height() / 2)
        # El icono, en su círculo.
        circulo = QRectF(caja.left() + 6, caja.top() + 5, caja.height() - 10, caja.height() - 10)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c["acento"])
        p.drawEllipse(circulo)
        p.setFont(self._f(16, False, self._aviso.get("fuente_icono", "Segoe UI Emoji")))
        sobre = QColor(fondo)
        sobre.setAlpha(255)
        p.setPen(sobre)
        p.drawText(circulo, Qt.AlignmentFlag.AlignCenter, self._aviso["icono"])
        if a < 0.55:                     # el texto aparece cuando ya hay sitio
            p.end()
            return
        p.setOpacity(min(1.0, (a - 0.55) / 0.35))
        texto = QRectF(circulo.right() + 10, caja.top(), caja.right() - circulo.right() - 24, caja.height())
        detalle = self._aviso.get("detalle", "")
        medida = QFontMetrics(self._f(13, True))
        p.setFont(self._f(13, True))
        p.setPen(c["texto"])
        arriba = QRectF(texto.left(), texto.top() + (5 if detalle else 0), texto.width(), texto.height() / 2 if detalle else texto.height())
        p.drawText(arriba, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   medida.elidedText(self._aviso["titulo"], Qt.TextElideMode.ElideRight, int(texto.width())))
        if detalle:
            p.setFont(self._f(11))
            p.setPen(c["tenue"])
            abajo = QRectF(texto.left(), texto.center().y() - 1, texto.width(), texto.height() / 2 - 4)
            p.drawText(abajo, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       QFontMetrics(self._f(11)).elidedText(detalle, Qt.TextElideMode.ElideRight, int(texto.width())))
        p.end()
