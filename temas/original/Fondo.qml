import QtQuick

// El filo de un píxel de la barra de Windows; se va con la opacidad.
Item {
  property real radio: 0
  property real desde: 0
  property real total: 0
  Rectangle {
    visible: !barra.tema.dentro
    width: parent.width
    height: 1
    y: barra.tema.lado === "arriba" ? parent.height - 1 : 0
    color: barra.tema.colores.borde
  }
}
