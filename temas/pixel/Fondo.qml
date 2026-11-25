import QtQuick

// Cielo según la hora, en bloques de 3 px: sol o luna, nubes o estrellas, colinas y hierba.
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
  readonly property string momento: barra.momento
  onMomentoChanged: { paisaje.requestPaint() }
  readonly property bool deNoche: momento === "noche" || momento === "atardecer"
  readonly property var tonos: ({
    noche: { colina: "#2C2358", lejos: "#1F1843", hierba: "#3B7A4C", hierba2: "#2F6440" },
    amanecer: { colina: "#D98F7A", lejos: "#E8A988", hierba: "#7FB069", hierba2: "#6A9A58" },
    dia: { colina: "#7FC08A", lejos: "#9AD3D6", hierba: "#63B874", hierba2: "#4C9A5F" },
    atardecer: { colina: "#4A2C62", lejos: "#693868", hierba: "#4C8A5F", hierba2: "#3B7350" }
  })[momento]

  Canvas {
    id: paisaje
    anchors.fill: parent
    renderStrategy: Canvas.Cooperative
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    readonly property real trozo: f.desde + f.largo
    onTrozoChanged: requestPaint()
    onPaint: {
      var x = getContext("2d"), p = 3, s = 11, t = f.tonos
      function azar() { s = (s * 16807) % 2147483647; return s / 2147483647 }
      var quita = Math.floor(f.desde / p), caben = Math.ceil(width / p)
      function px(cx, cy, w, h, c) {
        cx -= quita
        if (cx + w < 0 || cx > caben) return
        x.fillStyle = c; x.fillRect(cx * p, cy * p, w * p, h * p)
      }
      function disco(cx, cy, r, c) {
        for (var dy = -r; dy <= r; dy++)
          for (var dx = -r; dx <= r; dx++) if (dx * dx + dy * dy <= r * r + 1) px(cx + dx, cy + dy, 1, 1, c)
      }
      x.reset()
      f.recortar(x, width, height)
      var n = Math.ceil(f.largo / p), alto = Math.floor(height / p), astro = Math.floor(n * 0.73)
      x.translate(0, height - alto * p)        // la tierra llega justo al borde
      px(0, 0, n, 1, f.deNoche ? "#17122E" : "#4D14203A")
      if (f.deNoche)
        for (var i = 0; i < n / (f.momento === "noche" ? 7 : 16); i++)
          px(Math.floor(azar() * n), 2 + Math.floor(azar() * 6), 1, 1, azar() > 0.85 ? "#C9BFF2" : "#6A5AAE")
      if (f.momento === "noche") { disco(astro, 5, 3, "#F1EFD8"); disco(astro + 1, 4, 2, "#221A48") }
      else if (f.momento === "dia") disco(astro, 5, 3, "#FFE27A")
      else disco(astro, alto - 9, 4, f.momento === "amanecer" ? "#FFD07A" : "#FF8C5A")
      for (var a = 0; a < n; a++) {
        var h1 = Math.round(5 + 2 * Math.sin(a / 23 + 1)), h = Math.round(3 + 2 * Math.sin(a / 17) + 1.5 * Math.sin(a / 7 + 2))
        px(a, alto - 2 - h1, 1, h1, t.lejos)
        px(a, alto - 2 - h, 1, h, t.colina)
      }
      for (var b = 0; b < n; b++) {
        px(b, alto - 2, 1, 1, b % 2 ? t.hierba2 : t.hierba)
        px(b, alto - 1, 1, 1, azar() > 0.8 ? "#5A3A28" : "#6E4A33")
        if (azar() > 0.95) px(b, alto - 3, 1, 1, t.hierba)
      }
    }
  }

  Item {               // lo que se mueve, sin asomar por las esquinas
    id: marco
    anchors { fill: parent; leftMargin: f.radio * 0.55; rightMargin: f.radio * 0.55; topMargin: f.radio > 0 ? 1 : 0; bottomMargin: f.radio > 0 ? 1 : 0 }
    clip: f.dentro
    // Nubes, de día y al amanecer
    Repeater {
      id: nubes
      model: f.deNoche || f.width < 110 ? 0 : Math.max(f.dentro ? 1 : 3, Math.round(f.width / 320))
      Item {
        y: 4 + (index % 3) * 5
        opacity: f.momento === "dia" ? 0.75 : 0.5
        Component.onCompleted: x = (index + Math.random() * 0.6) * f.width / nubes.count
        Rectangle { x: 6; width: 24; height: 3; color: "#FFFFFF" }
        Rectangle { y: 3; width: 39; height: 6; color: "#FFFFFF" }
        Rectangle { x: 3; y: 9; width: 33; height: 3; color: "#E6F4FC" }
      }
    }
    Timer {
      interval: 400; repeat: true; running: !f.deNoche && f.visible && barra.mover
      onTriggered: {
        for (var i = 0; i < nubes.count; i++) { var o = nubes.itemAt(i); o.x = o.x > f.width ? -45 : o.x + 3 }
      }
    }
    // Estrellas que titilan
    Repeater {
      id: brillos
      model: f.momento === "noche" ? Math.max(1, Math.round(14 * f.width / f.largo)) : 0
      Rectangle {
        width: 3; height: 3; color: "#FFF4D6"
        x: Math.floor(Math.random() * f.width / 3) * 3
        y: 6 + Math.floor(Math.random() * 5) * 3
        opacity: Math.random() > 0.5 ? 0.9 : 0.1
      }
    }
    Timer {
      interval: 700; repeat: true; running: f.momento === "noche" && f.visible && barra.mover
      onTriggered: {
        var o = brillos.itemAt(Math.floor(Math.random() * brillos.count))
        if (o) o.opacity = o.opacity > 0.5 ? 0.1 : 0.9
      }
    }
  }
}
