import QtQuick

// CPU, RAM o GPU, con un dibujo distinto según `tema.medidor`.
Row {
  id: med
  property var tema
  property real alto: 40
  property string nombre
  property int valor: 0
  property var historia: []
  property int orden: 0
  readonly property var c: tema.colores
  readonly property string estilo: tema.medidor
  readonly property color tono: valor >= 85 ? c.alerta : ([c.medidor1, c.medidor2, c.medidor3][orden] || c.acento)
  readonly property bool conNombre: estilo !== "pildora"
  readonly property bool conNumero: ["anillo", "corazones", "pildora"].indexOf(estilo) < 0
  readonly property var anchos: ({ onda: 34, flor: 22, anillo: 26, corazones: 62, rama: 36 })
  height: alto
  spacing: 4

  onValorChanged: lienzo.requestPaint()
  onHistoriaChanged: if (estilo === "onda") lienzo.requestPaint()
  onTemaChanged: lienzo.requestPaint()
  onTonoChanged: lienzo.requestPaint()

  Texto {
    visible: med.conNombre
    text: med.nombre
    height: med.alto
    color: med.c.tenue
    font.pixelSize: med.tema.tamano - 2
  }

  Canvas {
    id: lienzo
    visible: width > 0
    width: med.anchos[med.estilo] || 0
    height: med.alto
    renderStrategy: Canvas.Cooperative
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
      var x = getContext("2d"), v = Math.max(0, Math.min(1, med.valor / 100)), cy = height / 2
      x.reset()
      var t = med.tono
      function rgba(a) { return Qt.rgba(t.r, t.g, t.b, a) }
      if (med.estilo === "onda") {
        var h = med.historia.length > 1 ? med.historia : [med.valor, med.valor]
        var al = Math.min(22, height - 10), y0 = cy + al / 2
        function punto(i) { return [i * (width - 2) / (h.length - 1) + 1, y0 - 1 - (al - 2) * Math.min(100, h[i]) / 100] }
        x.beginPath(); x.moveTo(1, y0)
        for (var i = 0; i < h.length; i++) { var p = punto(i); x.lineTo(p[0], p[1]) }
        x.lineTo(width - 1, y0); x.closePath()
        x.fillStyle = rgba(0.22); x.fill()
        x.beginPath()
        for (var j = 0; j < h.length; j++) { var q = punto(j); if (j) x.lineTo(q[0], q[1]); else x.moveTo(q[0], q[1]) }
        x.strokeStyle = rgba(1); x.lineWidth = 1.5; x.stroke()
      } else if (med.estilo === "flor") {
        var r = Math.min(10, height / 2 - 4)
        for (var k = 0; k < 5; k++) {
          var lleno = Math.max(0, Math.min(1, v * 5 - k)), a = -Math.PI / 2 + k * 2 * Math.PI / 5
          x.fillStyle = rgba(0.16 + 0.84 * lleno)
          x.beginPath(); x.arc(width / 2 + Math.cos(a) * r * 0.58, cy + Math.sin(a) * r * 0.58, r * 0.44, 0, 2 * Math.PI); x.fill()
        }
        x.fillStyle = med.c.acento2
        x.beginPath(); x.arc(width / 2, cy, r * 0.24, 0, 2 * Math.PI); x.fill()
      } else if (med.estilo === "anillo") {
        var ra = Math.min(11, height / 2 - 4)
        x.lineWidth = 3; x.lineCap = "round"
        x.strokeStyle = rgba(0.25)
        x.beginPath(); x.arc(width / 2, cy, ra, 0, 2 * Math.PI); x.stroke()
        if (v > 0) {
          x.strokeStyle = rgba(1)
          x.beginPath(); x.arc(width / 2, cy, ra, -Math.PI / 2, -Math.PI / 2 + 2 * Math.PI * v); x.stroke()
        }
      } else if (med.estilo === "corazones") {
        var forma = [".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."], px = 2, mitades = Math.round(v * 8)
        var y1 = Math.round(cy - 6)
        for (var n = 0; n < 4; n++)
          for (var f = 0; f < 6; f++)
            for (var col = 0; col < 7; col++) {
              if (forma[f][col] !== "#") continue
              var on = mitades >= 2 * n + 2 || (mitades === 2 * n + 1 && col < 4)
              x.fillStyle = on ? (f === 1 && col === 1 ? "#FFFFFF" : rgba(1)) : "rgba(0,0,0,0.38)"
              x.fillRect(n * 16 + col * px, y1 + f * px, px, px)
            }
      } else if (med.estilo === "rama") {
        x.strokeStyle = med.c.tenue; x.lineWidth = 1.4
        x.beginPath(); x.moveTo(1, cy + 3); x.quadraticCurveTo(width / 2, cy - 4, width - 2, cy - 1); x.stroke()
        for (var m = 0; m < 5; m++) {
          var ll = Math.max(0, Math.min(1, v * 5 - m)), arriba = m % 2 === 0, hx = 5 + m * 6.6
          x.save()
          x.translate(hx, cy + (arriba ? -4 : 4)); x.rotate(arriba ? -0.6 : 0.6)
          x.fillStyle = rgba(0.18 + 0.82 * ll)
          x.beginPath(); x.ellipse(-4.5, -2.4, 9, 4.8); x.fill()
          x.restore()
        }
      }
    }
    Texto {
      anchors.centerIn: parent
      visible: med.estilo === "anillo"
      text: med.valor
      color: med.c.texto
      font.pixelSize: med.valor > 99 ? 8 : 9
      font.bold: true
    }
  }

  Texto {
    visible: med.conNumero
    text: med.valor + "%"
    width: medida.width
    height: med.alto
    horizontalAlignment: Text.AlignRight
    color: med.valor >= 85 ? med.c.alerta : med.c.texto
    TextMetrics { id: medida; text: "100%"; font.family: med.tema.fuente; font.pixelSize: med.tema.tamano; font.bold: med.tema.negrita }
    Rectangle {        // Minimalista: una raya que crece
      visible: med.estilo === "linea"
      y: parent.height / 2 + 10
      height: 2
      width: Math.max(2, parent.width * med.valor / 100)
      color: med.tono
    }
  }

  Item {               // Camaleón: píldora que se llena
    visible: med.estilo === "pildora"
    width: visible ? letra.implicitWidth + 18 : 0
    height: med.alto
    Rectangle {
      anchors.centerIn: parent
      width: parent.width
      height: Math.min(22, med.alto - 8)
      radius: height / 2
      color: "#33000000"
      border.color: Qt.rgba(med.tono.r, med.tono.g, med.tono.b, 0.55)
      border.width: 1
      Rectangle {
        x: 2; y: 2
        height: parent.height - 4
        width: Math.max(height, (parent.width - 4) * med.valor / 100)
        radius: height / 2
        color: Qt.rgba(med.tono.r, med.tono.g, med.tono.b, 0.35)
        Behavior on width { NumberAnimation { duration: 300 } }
      }
      Texto { id: letra; anchors.centerIn: parent; text: med.nombre + " " + med.valor + "%"; color: med.c.texto; font.pixelSize: med.tema.tamano - 1 }
    }
  }
}
