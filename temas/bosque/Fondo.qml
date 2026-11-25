import QtQuick

// Vetas de madera y musgo. Hojas según la estación (nieve en invierno),
// luciérnagas de noche y niebla al amanecer.
Item {
  id: f
  readonly property string momento: barra.momento
  readonly property bool invierno: barra.mes === 12 || barra.mes <= 2
  readonly property var hojas: {
    var m = barra.mes
    return f.invierno ? ["#E8F0F2", "#CFDDE2", "#FFFFFF"]
         : m <= 5 ? ["#F4B6C8", "#F9D5E0", "#B7D78A"]
         : m <= 8 ? ["#7CB342", "#9CCC65", "#558B2F"]
         : ["#D9772B", "#E0A458", "#B5482A"]
  }
  Canvas {
    anchors.fill: parent
    renderStrategy: Canvas.Cooperative
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
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
      for (var k = 0; k < width; k += 7) {
        var h = 1 + azar() * 4
        x.fillStyle = "rgba(110,150,60,0.55)"; x.fillRect(k, 0, 7, h)                        // musgo
        if (f.invierno) { x.fillStyle = "rgba(235,243,246,0.8)"; x.fillRect(k, 0, 7, h * 0.6) }   // nieve
      }
    }
  }
  // Niebla
  Repeater {
    id: niebla
    model: f.momento === "amanecer" ? 5 : 0
    Rectangle {
      width: f.width * 0.35; height: f.height
      Component.onCompleted: x = index * f.width * 0.26 - 200
      gradient: Gradient {
        orientation: Gradient.Horizontal
        GradientStop { position: 0; color: "#00E9EFE4" }
        GradientStop { position: 0.5; color: "#12E9EFE4" }
        GradientStop { position: 1; color: "#00E9EFE4" }
      }
    }
  }
  // Hojas: menos de noche
  Repeater {
    id: rep
    model: Math.max(5, Math.round(f.width / (f.momento === "noche" ? 320 : 130)))
    Rectangle {
      property real vx: 0.3 + Math.random() * 0.6
      property real vy: 0.35 + Math.random() * 0.5
      width: f.invierno ? 4 : 7; height: 4; radius: 2
      opacity: f.momento === "noche" ? 0.4 : 0.75
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
  // Luciérnagas: aparecen y se apagan mientras derivan
  Repeater {
    id: luces
    model: f.momento === "noche" && !f.invierno ? Math.max(6, Math.round(f.width / 150)) : 0
    Item {
      property real fase: Math.random() * 6.28
      property real vx: Math.random() * 0.8 - 0.4
      Component.onCompleted: { x = Math.random() * f.width; y = 8 + Math.random() * (f.height - 16) }
      opacity: Math.max(0, Math.sin(fase))
      Rectangle { anchors.centerIn: parent; width: 10; height: 10; radius: 5; color: "#2EF4E285" }
      Rectangle { anchors.centerIn: parent; width: 3; height: 3; radius: 1.5; color: "#F9F1A5" }
      function volar() {
        fase += 0.09
        x = (x + vx + f.width) % f.width
        y = Math.max(5, Math.min(f.height - 5, y + Math.sin(fase * 1.7) * 0.4))
      }
    }
  }
  Timer {
    interval: barra.ritmo; repeat: true
    running: f.visible && barra.mover
    onTriggered: {
      for (var i = 0; i < rep.count; i++) rep.itemAt(i).caer()
      for (var j = 0; j < luces.count; j++) luces.itemAt(j).volar()
      for (var k = 0; k < niebla.count; k++) { var o = niebla.itemAt(k); o.x = o.x > f.width ? -o.width : o.x + 0.5 }
    }
  }
}
