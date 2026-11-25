import QtQuick

// Ciudad de noche tras las islas: silueta, ventanas que se encienden, luna y lluvia fina.
Item {
 id: todo
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
 Item {
  id: f
  // Las islas dejan un margen; la ciudad llega hasta los bordes.
  readonly property real m: detras ? barra.tema.margen : 0
  readonly property bool detras: barra.tema.forma === "islas" && !todo.dentro
  x: -m
  width: todo.width + 2 * m
  height: todo.height
  readonly property real suelo: height + m
  readonly property var tonos: ["#E0AF68", "#7AA2F7", "#BB9AF7", "#F7768E", "#7DCFFF"]

  Rectangle {
    width: f.width; y: -4; height: f.suelo + 4
    visible: f.detras
    gradient: Gradient {
      GradientStop { position: 0; color: "#001A1B26" }
      GradientStop { position: 0.5; color: "#8C1A1B26" }
      GradientStop { position: 1; color: "#E616161E" }
    }
  }
  Item {               // lo que se mueve, sin asomar por las esquinas
    anchors { fill: parent; leftMargin: todo.radio * 0.55; rightMargin: todo.radio * 0.55; topMargin: todo.radio > 0 ? 1 : 0; bottomMargin: todo.radio > 0 ? 1 : 0 }
    clip: todo.dentro
    // Luna con halo
    Repeater {
      model: [[30, "#0FC0CAF5"], [22, "#1CC0CAF5"], [14, "#E6E0E6FF"]]
      Rectangle {
        width: modelData[0]; height: width; radius: width / 2
        color: modelData[1]
        x: f.width * 0.71 - width / 2; y: 9 - height / 2
      }
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
      todo.recortar(x, width, height)
      for (var capa = 0; capa < 2; capa++) {
        var px = -5
        while (px < width) {
          var an = 12 + Math.floor(azar() * 26), al = (capa ? 5 : 10) + azar() * (capa ? 15 : 24) * Math.min(1, height / 44) * (todo.dentro ? 0.8 : 1)
          x.fillStyle = todo.dentro ? (capa ? "#FF10111A" : "#FF2A3152") : capa ? "#F216161E" : "#A6292E42"
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
  Item {               // lo que se mueve, sin asomar por las esquinas
    anchors { fill: parent; leftMargin: todo.radio * 0.55; rightMargin: todo.radio * 0.55; topMargin: todo.radio > 0 ? 1 : 0; bottomMargin: todo.radio > 0 ? 1 : 0 }
    clip: todo.dentro
    Repeater {
      id: luz
      model: Math.min(40, f.ventanas.length)
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
      interval: 600; repeat: true; running: f.visible && barra.mover
      onTriggered: { var o = luz.itemAt(Math.floor(Math.random() * luz.count)); if (o) o.encendida = !o.encendida }
    }
    Repeater {
      id: gotas
      model: Math.round(f.width / 160)
      Rectangle {
        property real v: 4.5 + Math.random() * 3.5
        width: 1; height: 5 + v
        color: "#3D7DCFFF"
        Component.onCompleted: { x = Math.random() * f.width; y = Math.random() * 48 - 8 }
        function caer() { y += v; x -= 0.6; if (y > f.suelo) { y = -12; x = Math.random() * (f.width + 20) } }
      }
    }
    Timer {
      interval: barra.ritmo; repeat: true; running: f.visible && barra.mover
      onTriggered: { for (var i = 0; i < gotas.count; i++) gotas.itemAt(i).caer() }
    }
  }
}
}
