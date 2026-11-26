import QtQuick

// Atardecer sintético: sol a rayas, estrellas y una rejilla de neón que avanza.
Item {
  id: f
  property real radio: 0
  property real desde: 0
  property real total: 0
  readonly property real largo: total > 0 ? total : width
  readonly property bool deNoche: barra.momento === "noche"
  readonly property real horizonte: Math.round(height * 0.52)
  readonly property real solX: largo * (barra.tema.unica ? 0.82 : 0.62) - desde
  function recortar(x, w, h) {
    if (radio <= 0) return
    var r = Math.min(radio, h / 2, w / 2)
    x.beginPath()
    x.moveTo(r, 0); x.arcTo(w, 0, w, h, r); x.arcTo(w, h, 0, h, r); x.arcTo(0, h, 0, 0, r); x.arcTo(0, 0, w, 0, r)
    x.closePath(); x.clip()
  }
  // Lo que no se mueve: estrellas, sol y las líneas que van hacia el horizonte.
  Canvas {
    id: quieto
    anchors.fill: parent
    renderStrategy: Canvas.Cooperative
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    readonly property real clave: f.solX + (f.deNoche ? 1 : 0)
    onClaveChanged: requestPaint()
    onPaint: {
      var x = getContext("2d"), s = 7, w = width, h = height, hz = f.horizonte
      function azar() { s = (s * 16807) % 2147483647; return s / 2147483647 }
      x.reset()
      f.recortar(x, w, h)
      for (var i = 0; i < w / 18; i++) {
        x.fillStyle = "rgba(255,240,255," + (0.25 + azar() * 0.55) + ")"
        x.fillRect(azar() * w, azar() * (hz - 4), 1, 1)
      }
      // El sol: medio disco con franjas que se abren hacia abajo.
      var r = h * 0.62, cx = f.solX, cy = hz + 1
      var g = x.createLinearGradient(0, cy - r, 0, cy)
      g.addColorStop(0, f.deNoche ? "#FF9DE2" : "#FFFB96")
      g.addColorStop(1, "#FF4FA3")
      x.save()
      x.beginPath(); x.arc(cx, cy, r, Math.PI, 2 * Math.PI); x.closePath(); x.clip()
      x.fillStyle = g
      x.fillRect(cx - r, cy - r, 2 * r, r)
      x.globalCompositeOperation = "destination-out"
      for (var k = 0; k < 5; k++) {
        var yy = cy - r * 0.45 + k * r * 0.11
        x.fillRect(cx - r, yy, 2 * r, 1 + k * 0.6)
      }
      x.restore()
      // halo
      var halo = x.createRadialGradient(cx, cy, r * 0.6, cx, cy, r * 1.9)
      halo.addColorStop(0, "rgba(255,113,206,0.28)")
      halo.addColorStop(1, "rgba(255,113,206,0)")
      x.fillStyle = halo
      x.fillRect(cx - r * 2, 0, r * 4, hz)
      // el suelo y sus líneas de fuga
      x.fillStyle = "rgba(20,4,40,0.55)"
      x.fillRect(0, hz, w, h - hz)
      x.strokeStyle = "rgba(1,205,254,0.45)"
      x.lineWidth = 1
      for (var j = -40; j <= 40; j++) {
        var arriba = cx + j * 14, abajo = cx + j * 70
        x.beginPath(); x.moveTo(arriba, hz); x.lineTo(abajo, h); x.stroke()
      }
      x.strokeStyle = "rgba(255,113,206,0.9)"
      x.beginPath(); x.moveTo(0, hz + 0.5); x.lineTo(w, hz + 0.5); x.stroke()
    }
  }
  // Las líneas horizontales del suelo: bajan y se separan, como si avanzáramos.
  Item {
    id: suelo
    anchors.fill: parent
    clip: true
    property real fase: 0
    Repeater {
      model: 5
      Rectangle {
        readonly property real t: ((index + suelo.fase) % 5) / 5          // 0 horizonte, 1 borde
        width: f.width
        height: 1
        y: f.horizonte + (f.height - f.horizonte) * t * t
        color: "#01CDFE"
        opacity: 0.25 + 0.5 * t
      }
    }
    Timer {
      interval: barra.ritmo; repeat: true
      running: f.visible && barra.mover
      onTriggered: suelo.fase = (suelo.fase + 0.06) % 5
    }
  }
}
