import QtQuick

// El botón de una ventana (o de un programa anclado).
Item {
  id: tarea
  property var tema
  property real alto: 40
  property string clave
  property string titulo
  property string icono
  property bool activa: false
  property bool abierta: false
  property bool minimizada: false
  readonly property var c: tema.colores
  readonly property string estilo: tema.indicador
  width: tema.compacto ? 32 : 42
  height: alto

  Rectangle {
    anchors { fill: parent; margins: tarea.tema.compacto ? 1 : 3 }
    radius: Math.min(tema.radio, 10)
    color: tarea.activa && tarea.estilo === "relleno" ? tarea.c.acento
           : raton.containsMouse || (tarea.activa && tarea.estilo !== "corchetes" && tarea.estilo !== "gota") ? tarea.c.encima : "transparent"
    Behavior on color { ColorAnimation { duration: 140 } }
  }

  Image {
    anchors.centerIn: parent
    width: tarea.tema.icono; height: tarea.tema.icono
    sourceSize: Qt.size(32, 32)
    source: tarea.icono
    smooth: !tarea.tema.pixelado
    mipmap: !tarea.tema.pixelado
    opacity: tarea.minimizada ? 0.55 : 1
    scale: raton.pressed ? 0.85 : raton.containsMouse ? 1.1 : 1
    Behavior on scale { NumberAnimation { duration: 110 } }
  }
  Text {         // sin icono: la inicial
    anchors.centerIn: parent
    visible: tarea.icono === ""
    text: tarea.titulo.charAt(0).toUpperCase()
    color: tarea.c.texto
    font.family: tarea.tema.fuente
    font.pixelSize: 18
  }

  // Indicador de abierta / activa
  Rectangle {
    visible: tarea.abierta && (tarea.estilo === "linea" || tarea.estilo === "punto")
    anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: tarea.tema.compacto ? 0 : 2 }
    width: tarea.estilo === "punto" ? 4 : tarea.activa ? 22 : 8
    height: tarea.estilo === "punto" ? 4 : tarea.tema.compacto ? 2 : 3
    radius: tarea.tema.pixelado ? 0 : height / 2
    color: tarea.activa ? tarea.c.acento : tarea.c.tenue
    Behavior on width { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
    Behavior on color { ColorAnimation { duration: 140 } }
  }
  Rectangle {
    visible: tarea.abierta && !tarea.activa && tarea.estilo === "relleno"
    anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 3 }
    width: 12; height: 2
    color: tarea.c.tenue
  }
  Repeater {
    model: tarea.estilo === "corchetes" && tarea.abierta ? ["[", "]"] : []
    Text {
      x: index ? tarea.width - width : 0
      height: tarea.height
      verticalAlignment: Text.AlignVCenter
      text: modelData
      color: tarea.activa ? tarea.c.acento : tarea.c.tenue
      font.family: tarea.tema.fuente
      font.pixelSize: tarea.tema.tamano + 4
    }
  }

  Aviso { texto: tarea.abierta ? "" : tarea.titulo; fuente: raton }   // abierta: vista previa
  MouseArea {
    id: raton
    anchors.fill: parent
    hoverEnabled: true
    acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
    onContainsMouseChanged: {
      if (!containsMouse) { barra.soltar(tarea.clave); return }
      var p = tarea.mapToGlobal(tarea.width / 2, 0)
      barra.apuntar(tarea.clave, p.x, p.y)
    }
    onClicked: function(e) {
      if (e.button === Qt.RightButton) barra.menu_tarea(tarea.clave)
      else barra.pulsar_tarea(tarea.clave, e.button === Qt.MiddleButton)
    }
  }
}
