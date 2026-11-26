import QtQuick

// Mar abierto: dos capas de olas que avanzan, burbujas que suben y, de noche,
// lucecitas de plancton. Cada ola se dibuja una vez y solo se desplaza.
Item {
  id: f
  property real radio: 0
  property real desde: 0
  property real total: 0
  readonly property bool deNoche: barra.momento === "noche"
  readonly property bool dentro: barra.tema.dentro
  // Dentro de una isla redondeada: lo que se mueve no asoma por las esquinas.
  Item {
  id: m
  anchors { fill: parent; leftMargin: f.radio * 0.55; rightMargin: f.radio * 0.55; topMargin: f.radio > 0 ? 1 : 0; bottomMargin: f.radio > 0 ? 1 : 0 }
  clip: true

  component Ola: Canvas {
    id: ola
    property real periodo: 160
    property real alto: 5
    property real nivel: 10
    property color color: "#40FFFFFF"
    property real velocidad: 1
    property real fase: 0
    width: m.width + periodo
    height: m.height
    renderStrategy: Canvas.Cooperative
    x: -fase
    onWidthChanged: requestPaint()
    onColorChanged: requestPaint()
    onPaint: {
      var c = getContext("2d")
      c.reset()
      c.fillStyle = color
      c.beginPath()
      c.moveTo(0, height)
      for (var i = 0; i <= width; i += 4)
        c.lineTo(i, nivel + alto * Math.sin(i / periodo * 2 * Math.PI))
      c.lineTo(width, height)
      c.closePath()
      c.fill()
    }
    function avanzar() { fase = (fase + velocidad) % periodo }
  }

  Ola { id: lejos; periodo: 210; alto: 3; nivel: 12; velocidad: 1.2; color: f.deNoche ? "#1A4FFFE0" : "#2299E9F0" }
  Ola { id: cerca; periodo: 150; alto: 4; nivel: 20; velocidad: 2.2; color: f.deNoche ? "#22031A2C" : "#33053B57" }

  // Destellos de sol en la superficie (de día) o plancton (de noche).
  Repeater {
    id: brillos
    model: Math.max(f.dentro ? 3 : 8, Math.round(m.width / 110))
    Rectangle {
      property real fase: Math.random() * 6.28
      width: f.deNoche ? 3 : 6; height: f.deNoche ? 3 : 1.5; radius: height / 2
      x: Math.random() * m.width
      y: f.deNoche ? 14 + Math.random() * (m.height - 18) : 8 + Math.random() * 8
      color: f.deNoche ? "#4FFFE0" : "#FFFFFF"
      opacity: 0.15 + 0.5 * Math.max(0, Math.sin(fase))
    }
  }

  Repeater {
    id: burbujas
    model: Math.max(f.dentro ? 2 : 5, Math.round(m.width / 160))
    Rectangle {
      property real v: 0.5 + Math.random() * 0.8
      width: 3 + Math.random() * 4; height: width; radius: width / 2
      color: "transparent"
      border.width: 1
      border.color: f.deNoche ? "#664FFFE0" : "#99E6FBFF"
      Component.onCompleted: { x = Math.random() * m.width; y = m.height * Math.random() }
      function subir() {
        y -= v
        x += Math.sin(y / 5) * 0.4
        if (y < 14) { y = m.height + 4; x = Math.random() * m.width }
      }
    }
  }

  Timer {
    interval: barra.ritmo; repeat: true
    running: f.visible && barra.mover
    onTriggered: {
      lejos.avanzar(); cerca.avanzar()
      for (var i = 0; i < burbujas.count; i++) burbujas.itemAt(i).subir()
      for (var j = 0; j < brillos.count; j++) brillos.itemAt(j).fase += 0.25
    }
  }
  }
}
