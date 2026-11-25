import QtQuick

// Vetas de madera y hojas que caen; el color depende de la estación (hemisferio norte).
Item {
  id: f
  readonly property var hojas: {
    var m = barra.mes
    return m >= 3 && m <= 5 ? ["#F4B6C8", "#F9D5E0", "#B7D78A"]
         : m >= 6 && m <= 8 ? ["#7CB342", "#9CCC65", "#558B2F"]
         : m >= 9 && m <= 11 ? ["#D9772B", "#E0A458", "#B5482A"]
         : ["#E8F0F2", "#CFDDE2", "#FFFFFF"]
  }
  Canvas {
    anchors.fill: parent
    renderStrategy: Canvas.Cooperative
    onWidthChanged: requestPaint()
    onPaint: {
      var x = getContext("2d"), s = 5
      function azar() { s = (s * 16807) % 2147483647; return s / 2147483647 }
      x.reset()
      for (var i = 0; i < 22; i++) {
        var y = azar() * height
        x.strokeStyle = azar() > 0.5 ? "rgba(0,0,0,0.16)" : "rgba(190,160,110,0.07)"
        x.lineWidth = 0.6 + azar() * 1.4
        x.beginPath(); x.moveTo(0, y)
        for (var a = 0; a < width; a += 160)
          x.bezierCurveTo(a + 50, y + azar() * 8 - 4, a + 110, y + azar() * 8 - 4, a + 160, y + azar() * 4 - 2)
        x.stroke()
      }
      x.fillStyle = "rgba(110,150,60,0.55)"
      for (var k = 0; k < width; k += 7) x.fillRect(k, 0, 7, 1 + azar() * 4)   // musgo
    }
  }
  Repeater {
    id: rep
    model: Math.max(6, Math.round(f.width / 130))
    Rectangle {
      id: hoja
      property real vx: 0.3 + Math.random() * 0.6
      property real vy: 0.35 + Math.random() * 0.5
      width: 7; height: 4; radius: 2
      opacity: 0.75
      color: f.hojas[index % f.hojas.length]
      Component.onCompleted: { x = Math.random() * f.width; y = Math.random() * 40; rotation = Math.random() * 360 }
      function caer() {
        rotation += 4 * vx
        x += vx + Math.sin(y / 7) * 0.6
        y += vy
        if (y > f.height + 6) { y = -8; x = Math.random() * f.width }
      }
    }
  }
  Timer {
    interval: 80; repeat: true
    running: f.visible && barra.animar
    onTriggered: { for (var i = 0; i < rep.count; i++) rep.itemAt(i).caer() }
  }
}
