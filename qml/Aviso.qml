import QtQuick
import QtQuick.Controls

// Texto que sale junto a la barra, en su propia ventana. `fuente` es el MouseArea.
Item {
  id: aviso
  property string texto: ""
  property var fuente
  readonly property string lado: barra.tema.lado
  anchors.fill: parent
  ToolTip {
    id: globo
    popupType: Popup.Window
    parent: aviso
    x: aviso.lado === "izquierda" ? aviso.width + 6 : aviso.lado === "derecha" ? -width - 6 : (aviso.width - width) / 2
    y: aviso.lado === "arriba" ? aviso.height + 6 : aviso.lado === "abajo" ? -height - 6 : (aviso.height - height) / 2
    delay: 450
    // WCAG 1.4.13: se puede pasar el ratón al globo sin que se vaya (y cruzar el hueco),
    // se queda mientras no te vayas y se cierra con Esc sin mover el ratón.
    property bool cerrado: false
    readonly property bool encima: aviso.fuente.containsMouse || sobreGlobo.hovered || cruzando.running
    visible: aviso.texto !== "" && encima && !aviso.fuente.pressed && !cerrado
    Connections {
      target: aviso.fuente
      function onContainsMouseChanged() {
        if (aviso.fuente.containsMouse) globo.cerrado = false
        else cruzando.restart()
      }
    }
    Timer { id: cruzando; interval: 350 }
    Timer {          // Esc: se mira la tecla mientras hay globo, sin gancho de teclado
      interval: 120; repeat: true; running: globo.visible
      // Al abrirse, se borra la marca de «se pulsó» de antes: es de todo Windows y podía
      // venir de un Esc pulsado hace rato en otro programa.
      onRunningChanged: if (running) barra.tecla_esc()
      onTriggered: if (barra.tecla_esc()) globo.cerrado = true
    }
    contentItem: Text {
      text: aviso.texto
      color: barra.tema.colores.texto
      font.family: barra.tema.fuente
      font.pixelSize: Math.round(12 * barra.escala)
      textFormat: Text.PlainText
      HoverHandler { id: sobreGlobo }
    }
    background: Rectangle {
      color: Qt.rgba(fondo.r, fondo.g, fondo.b, 1)
      readonly property color fondo: barra.tema.colores.fondo
      border.color: barra.tema.colores.acento
      radius: Math.min(6, barra.tema.radio)
    }
  }
}
