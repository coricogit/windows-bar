import QtQuick
import QtQuick.Controls

// Texto que sale encima de la barra, en su propia ventana. `fuente` es el MouseArea.
Item {
  id: aviso
  property string texto: ""
  property var fuente
  anchors.fill: parent
  ToolTip {
    id: globo
    popupType: Popup.Window
    parent: aviso
    y: -height - 6
    x: (aviso.width - width) / 2
    delay: 450
    visible: aviso.texto !== "" && aviso.fuente.containsMouse && !aviso.fuente.pressed
    contentItem: Text {
      text: aviso.texto
      color: barra.tema.colores.texto
      font.family: barra.tema.fuente
      font.pixelSize: 12
      textFormat: Text.PlainText
    }
    background: Rectangle {
      color: Qt.rgba(fondo.r, fondo.g, fondo.b, 1)
      readonly property color fondo: barra.tema.colores.fondo
      border.color: barra.tema.colores.acento
      radius: Math.min(6, barra.tema.radio)
    }
  }
}
