import QtQuick

// Solo un filo de un píxel por el lado de las ventanas, para separarla de ellas.
Item {
  property real radio: 0
  property real desde: 0
  property real total: 0
  readonly property string lado: barra.tema.lado
  Rectangle {
    visible: !barra.tema.dentro
    color: barra.tema.colores.borde
    x: lado === "izquierda" ? parent.width - 1 : 0
    y: lado === "arriba" ? parent.height - 1 : 0
    width: lado === "izquierda" || lado === "derecha" ? 1 : parent.width
    height: lado === "izquierda" || lado === "derecha" ? parent.height : 1
  }
}
