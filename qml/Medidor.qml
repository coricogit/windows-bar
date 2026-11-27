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
  // Un dibujo y, a su lado, el nombre sobre el número.
  // Todo crece o encoge con el alto de la barra; 46 px es el tamaño de referencia.
  // Por debajo de 0,8 las letras ya no se leen; la barra compacta (30 px) se queda ahí.
  readonly property real f: Math.max(0.8, Math.min(1.4, alto / 46))
  readonly property real escala: 0.9 * f
  readonly property int letra: Math.round(13.5 * f)
  readonly property int letraNombre: Math.max(9, Math.round(10 * f))
  readonly property int px: Math.max(2, Math.round(2 * f))      // píxel de los corazones
  readonly property bool apilado: estilo !== "pildora" && !v
  readonly property var anchos: ({ onda: 34, flor: 22, anillo: 26, corazones: 22, rama: 36 })
  readonly property bool v: tema.vertical
  height: v ? pila.height : alto
  spacing: v ? 0 : Math.round(4 * f)

  onValorChanged: lienzo.requestPaint()
  onHistoriaChanged: if (estilo === "onda") lienzo.requestPaint()
  onEstiloChanged: lienzo.requestPaint()      // al cambiar de diseño, sin esperar a datos nuevos
  onTemaChanged: lienzo.requestPaint()
  onTonoChanged: lienzo.requestPaint()

  Canvas {
    id: lienzo
    visible: width > 0
    width: med.v ? 0 : med.estilo === "corazones" ? 9 * med.px : Math.round((med.anchos[med.estilo] || 0) * med.escala)
    height: med.alto
    renderStrategy: Canvas.Cooperative
    onWidthChanged: requestPaint()
    onVisibleChanged: if (visible) requestPaint()     // oculto no pinta: al aparecer, sí
    onCanvasSizeChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
      var x = getContext("2d"), v = Math.max(0, Math.min(1, med.valor / 100))
      var k = med.escala, width = lienzo.width / k, height = lienzo.height / k, cy = height / 2
      x.reset()
      x.scale(k, k)
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
        var forma = [".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."], px = med.px / k, x0 = 0
        // Un corazón con contorno que se llena de abajo arriba, en píxeles enteros.
        var y1 = Math.round(lienzo.height / 2 - 4 * med.px) / k
        function lleno(a, b) { return a >= 0 && a < 6 && b >= 0 && b < 7 && forma[a][b] === "#" }
        for (var f = -1; f < 7; f++)
          for (var col = -1; col < 8; col++) {
            var on = 6 - f <= Math.ceil(v * 6)
            if (lleno(f, col)) x.fillStyle = f === 1 && col === 1 ? "#FFFFFF" : on ? rgba(1) : "rgba(255,255,255,0.45)"
            else if (lleno(f - 1, col) || lleno(f + 1, col) || lleno(f, col - 1) || lleno(f, col + 1)) x.fillStyle = med.c.borde
            else continue
            x.fillRect(x0 + (col + 1) * px, y1 + (f + 1) * px, px, px)
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
  }

  Column {             // nombre y número
    visible: med.apilado
    anchors.verticalCenter: parent.verticalCenter
    spacing: Math.round(-2.5 * med.f)
    Texto { text: med.nombre; color: med.c.tenue; font.pixelSize: med.letraNombre; font.bold: false }
    Texto {
      text: med.valor + "%"
      width: medida.width
      color: med.valor >= 85 ? med.c.alerta : med.c.texto
      font.pixelSize: med.letra
      TextMetrics { id: medida; text: "00%"; font.family: med.tema.fuente; font.pixelSize: med.letra; font.bold: med.tema.negrita }
      Rectangle {        // una raya que crece
        visible: med.estilo === "linea"
        y: parent.height - 1
        height: Math.max(2, Math.round(2 * med.f))
        width: Math.max(2, parent.width * med.valor / 100)
        color: med.tono
      }
    }
  }

  Column {             // barra vertical: nombre, número y raya
    id: pila
    visible: med.v
    width: med.v ? med.alto : 0
    spacing: 0
    Texto { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: med.nombre; color: med.c.tenue; font.pixelSize: 9 }
    Texto {
      width: parent.width
      horizontalAlignment: Text.AlignHCenter
      text: med.valor + "%"
      font.pixelSize: Math.min(med.tema.tamano, 12)
      color: med.valor >= 85 ? med.c.alerta : med.c.texto
    }
    Item {
      width: parent.width; height: 5
      Rectangle { x: 10; y: 1; width: parent.width - 20; height: 3; radius: med.tema.pixelado ? 0 : 1.5; color: med.c.tenue; opacity: 0.3 }
      Rectangle { x: 10; y: 1; width: Math.max(3, (parent.width - 20) * med.valor / 100); height: 3; radius: med.tema.pixelado ? 0 : 1.5; color: med.tono }
    }
  }

  Item {               // Camaleón: píldora que se llena
    visible: med.estilo === "pildora" && !med.v
    width: visible ? letra.implicitWidth + Math.round(18 * med.f) : 0
    height: med.alto
    Rectangle {
      anchors.centerIn: parent
      width: parent.width
      height: Math.round(med.alto * 0.48)
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
      Texto { id: letra; anchors.centerIn: parent; text: med.nombre + " " + med.valor + "%"; color: med.c.texto; font.pixelSize: Math.max(9, Math.round((med.tema.tamano - 1) * med.f)) }
    }
  }
}
