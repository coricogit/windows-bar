import QtQuick

// Una rama en flor a la izquierda y pétalos que caen con el viento.
Item {
  id: f
  // Dentro de una isla: sus esquinas, y qué trozo del paisaje le toca.
  property real radio: 0
  property real desde: 0
  property real total: 0
  readonly property real largo: total > 0 ? total : width
  readonly property bool dentro: barra.tema.dentro
  function recortar(x, w, h) {
    if (radio <= 0) return
    var r = Math.min(radio, h / 2, w / 2)
    x.beginPath()
    x.moveTo(r, 0); x.arcTo(w, 0, w, h, r); x.arcTo(w, h, 0, h, r); x.arcTo(0, h, 0, 0, r); x.arcTo(0, 0, w, 0, r)
    x.closePath(); x.clip()
  }
  Canvas {
    anchors.fill: parent
    renderStrategy: Canvas.Cooperative
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    readonly property real trozo: f.desde + f.largo
    onTrozoChanged: requestPaint()
    onPaint: {
      var x = getContext("2d"), s = 23
      function azar() { s = (s * 16807) % 2147483647; return s / 2147483647 }
      x.reset()
      f.recortar(x, width, height)
      x.translate(-f.desde, 0)
      // Rama: entra por arriba y se afina.
      var fin = f.largo * (barra.tema.unica ? 0.22 : 0.34)
      for (var i = 0; i < 60; i++) {
        var a = i / 60, b = (i + 1) / 60
        x.strokeStyle = "rgba(110,70,75,0.35)"
        x.lineWidth = 3.2 * (1 - a) + 0.6
        x.beginPath()
        x.moveTo(a * fin, 2 + 4 * Math.sin(a * 9)); x.lineTo(b * fin, 2 + 4 * Math.sin(b * 9))
        x.stroke()
      }
      // Flores de cinco pétalos.
      for (var k = 0; k < 26; k++) {
        var t = azar(), cx = t * fin, cy = 3 + 4 * Math.sin(t * 9) + azar() * 6 - 2, r = 2 + azar() * 2
        x.fillStyle = azar() > 0.5 ? "rgba(244,143,177,0.75)" : "rgba(248,187,208,0.9)"
        for (var p = 0; p < 5; p++) {
          x.beginPath()
          x.arc(cx + Math.cos(p * 1.2566) * r, cy + Math.sin(p * 1.2566) * r, r * 0.8, 0, 6.2832)
          x.fill()
        }
        x.fillStyle = "rgba(194,56,95,0.7)"
        x.beginPath(); x.arc(cx, cy, r * 0.45, 0, 6.2832); x.fill()
      }
    }
  }
  Item {               // lo que se mueve, sin asomar por las esquinas
    id: marco
    anchors { fill: parent; leftMargin: f.radio * 0.55; rightMargin: f.radio * 0.55; topMargin: f.radio > 0 ? 1 : 0; bottomMargin: f.radio > 0 ? 1 : 0 }
    clip: f.dentro
    Repeater {
      id: rep
      model: Math.max(f.dentro ? 1 : 6, Math.round(f.width / 120))
      Rectangle {
        property real vx: 0.4 + Math.random() * 0.7
        property real vy: 0.25 + Math.random() * 0.4
        width: 7; height: 5; radius: 2.5
        opacity: 0.65
        color: index % 3 ? "#F48FB1" : "#F8BBD0"
        Component.onCompleted: { x = Math.random() * f.width; y = Math.random() * 40; rotation = Math.random() * 360 }
        function caer() {
          rotation += 3 * vx
          x += vx + Math.sin(y / 6) * 0.8
          y += vy
          if (y > f.height + 6) { y = -8; x = Math.random() * f.width }
        }
      }
    }
    Timer {
      interval: barra.ritmo; repeat: true
      running: f.visible && barra.mover
      onTriggered: { for (var i = 0; i < rep.count; i++) rep.itemAt(i).caer() }
    }
  }
}
