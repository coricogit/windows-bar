import QtQuick

// Ciudad de noche tras las islas: silueta, ventanas que se encienden, luna y lluvia fina.
Item {
 id: todo
 Item {
  id: f
  // Las islas dejan un margen; la ciudad llega hasta los bordes.
  readonly property real m: barra.tema.forma === "islas" ? barra.tema.margen : 0
  x: -m
  width: todo.width + 2 * m
  height: todo.height
  readonly property real suelo: height + (barra.tema.forma === "islas" ? barra.tema.margen : 0)
  readonly property var tonos: ["#E0AF68", "#7AA2F7", "#BB9AF7", "#F7768E", "#7DCFFF"]

  Rectangle {
    width: f.width; y: -4; height: f.suelo + 4
    visible: barra.tema.forma === "islas"
    gradient: Gradient {
      GradientStop { position: 0; color: "#001A1B26" }
      GradientStop { position: 0.5; color: "#8C1A1B26" }
      GradientStop { position: 1; color: "#E616161E" }
    }
  }
  // Luna con halo
  Repeater {
    model: [[30, "#0FC0CAF5"], [22, "#1CC0CAF5"], [14, "#E6E0E6FF"]]
    Rectangle {
      width: modelData[0]; height: width; radius: width / 2
      color: modelData[1]
      x: f.width * 0.71 - width / 2; y: 9 - height / 2
    }
  }

  property var ventanas: []
  Canvas {
    id: ciudad
    width: f.width; height: f.suelo
    renderStrategy: Canvas.Cooperative
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
      var x = getContext("2d"), s = 41, luces = []
      function azar() { s = (s * 16807) % 2147483647; return s / 2147483647 }
      x.reset()
      for (var capa = 0; capa < 2; capa++) {
        var px = -5
        while (px < width) {
          var an = 12 + Math.floor(azar() * 26), al = (capa ? 5 : 10) + azar() * (capa ? 15 : 24) * Math.min(1, height / 44)
          x.fillStyle = capa ? "#F216161E" : "#A6292E42"
          x.fillRect(px, height - al, an, al)
          if (azar() > 0.82) x.fillRect(px + an / 2, height - al - 5, 1, 5)      // antena
          if (capa) for (var vy = height - al + 3; vy < height - 3; vy += 5)
            for (var vx = px + 3; vx < px + an - 3; vx += 5)
              if (azar() > 0.55) luces.push([vx, vy])
          px += an + (azar() > 0.7 ? 3 : 0)
        }
      }
      f.ventanas = luces
    }
  }
  Repeater {
    id: luz
    model: Math.min(70, f.ventanas.length)
    Rectangle {
      readonly property var sitio: f.ventanas[(index * 37) % f.ventanas.length] || [0, 0]
      x: sitio[0]; y: sitio[1]
      width: 2; height: 2
      color: f.tonos[index % 5]
      property bool encendida: Math.random() > 0.4
      opacity: encendida ? 0.85 : 0.08
    }
  }
  Timer {
    interval: 600; repeat: true; running: f.visible && barra.animar
    onTriggered: { var o = luz.itemAt(Math.floor(Math.random() * luz.count)); if (o) o.encendida = !o.encendida }
  }
  Repeater {
    id: gotas
    model: Math.round(f.width / 95)
    Rectangle {
      property real v: 4.5 + Math.random() * 3.5
      width: 1; height: 5 + v
      color: "#3D7DCFFF"
      Component.onCompleted: { x = Math.random() * f.width; y = Math.random() * 48 - 8 }
      function caer() { y += v; x -= 0.6; if (y > f.suelo) { y = -12; x = Math.random() * (f.width + 20) } }
    }
  }
  Timer {
    interval: 125; repeat: true; running: f.visible && barra.animar
    onTriggered: { for (var i = 0; i < gotas.count; i++) gotas.itemAt(i).caer() }
  }
}
}
