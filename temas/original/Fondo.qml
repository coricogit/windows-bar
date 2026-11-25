import QtQuick

// El filo de un píxel de la barra de Windows; se va con la opacidad.
Item {
  Rectangle {
    width: parent.width
    height: 1
    y: barra.tema.lado === "arriba" ? parent.height - 1 : 0
    color: barra.tema.colores.borde
  }
}
