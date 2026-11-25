import QtQuick

// El icono de Windows: cuatro paneles con la forma y los colores del tema.
// `fuera`, `dentro` y `lados` son el radio de cada esquina, de 0 a 1 (1 = media pieza).
Item {
  id: logo
  property var tema
  property bool encima: false
  readonly property var l: tema.logo
  readonly property real lado: tema.compacto ? 15 : 20
  readonly property real hueco: l.hueco * (tema.compacto ? 0.75 : 1)
  readonly property real pieza: (lado - hueco) / 2
  width: lado
  height: lado
  scale: encima ? 1.14 : 1
  Behavior on scale { NumberAnimation { duration: 130; easing.type: Easing.OutBack } }

  function color(n) { return tema.colores[n] || n }

  Repeater {
    model: 4
    Rectangle {
      id: panel
      readonly property bool der: index % 2 === 1
      readonly property bool aba: index > 1
      readonly property color tono: logo.color(logo.l.colores[index % logo.l.colores.length])
      readonly property real rf: logo.l.fuera * width / 2
      readonly property real rd: logo.l.dentro * width / 2
      readonly property real rl: logo.l.lados * width / 2
      x: der ? logo.pieza + logo.hueco : 0
      y: aba ? logo.pieza + logo.hueco : 0
      width: logo.pieza
      height: logo.pieza
      topLeftRadius: !der && !aba ? rf : der && aba ? rd : rl
      topRightRadius: der && !aba ? rf : !der && aba ? rd : rl
      bottomLeftRadius: !der && aba ? rf : der && !aba ? rd : rl
      bottomRightRadius: der && aba ? rf : !der && !aba ? rd : rl
      color: logo.l.contorno ? "transparent" : Qt.rgba(tono.r, tono.g, tono.b, logo.l.opacidad)
      border.width: logo.l.contorno ? 1.5 : logo.l.filo ? 1 : 0
      border.color: logo.l.contorno ? tono : logo.l.filo ? logo.color(logo.l.filo) : "transparent"
      Behavior on color { ColorAnimation { duration: 350 } }
      // Bisel de píxel: luz arriba y sombra abajo.
      Rectangle { visible: !!logo.l.bisel; width: parent.width; height: 2; color: "#73FFFFFF" }
      Rectangle { visible: !!logo.l.bisel; width: parent.width; height: 2; anchors.bottom: parent.bottom; color: "#4D000000" }
    }
  }
}
