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
  property int cuenta: 0
  property int indice: 0
  property var lista
  // Arrastre: el botón sigue al ratón y los demás se apartan.
  property bool arrastrando: false
  property real ratonX: 0          // en la lista
  property real agarre: 0          // dónde se cogió, dentro del botón
  z: arrastrando ? 10 : 0
  transform: Translate { x: tarea.arrastrando ? tarea.ratonX - tarea.agarre - tarea.x : 0 }
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

  // Indicador de abierta / activa: un trozo por ventana, hasta tres.
  Row {
    visible: tarea.abierta && (tarea.estilo === "linea" || tarea.estilo === "punto")
    anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: tarea.tema.compacto ? 0 : 2 }
    spacing: 2
    Repeater {
      model: Math.max(1, Math.min(3, tarea.cuenta))
      Rectangle {
        readonly property int n: Math.max(1, Math.min(3, tarea.cuenta))
        width: tarea.estilo === "punto" ? 4 : (tarea.activa ? 22 : n > 1 ? 14 : 8) / n - (n > 1 ? 1 : 0)
        height: tarea.estilo === "punto" ? 4 : tarea.tema.compacto ? 2 : 3
        radius: tarea.tema.pixelado ? 0 : height / 2
        color: tarea.activa ? tarea.c.acento : tarea.c.tenue
        Behavior on width { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
        Behavior on color { ColorAnimation { duration: 140 } }
      }
    }
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
    preventStealing: true
    acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
    property bool movido: false
    property real inicio: 0
    function enLista(e) { return raton.mapToItem(tarea.lista.contentItem, e.x, 0).x }
    onPressed: function(e) { movido = false; inicio = enLista(e); tarea.agarre = e.x }
    onPositionChanged: function(e) {
      if (!(pressedButtons & Qt.LeftButton)) return
      var x = enLista(e)
      if (!tarea.arrastrando) {
        if (Math.abs(x - inicio) < 10 || tarea.lista.count < 2) return
        tarea.ratonX = x
        movido = true
        tarea.arrastrando = true
        barra.empezar_arrastre()
      }
      tarea.ratonX = x
      var paso = tarea.width + tarea.lista.spacing
      var destino = Math.floor((x - tarea.agarre + tarea.width / 2) / paso)
      destino = Math.max(0, Math.min(tarea.lista.count - 1, destino))
      if (destino !== tarea.indice) tareas.mover(tarea.indice, destino)
    }
    function acabar() {
      if (!tarea.arrastrando) return
      tarea.arrastrando = false
      barra.terminar_arrastre(tareas)
    }
    onReleased: acabar()
    onCanceled: acabar()
    onContainsMouseChanged: {
      if (!containsMouse) { barra.soltar(tarea.clave); return }
      var p = tarea.mapToGlobal(tarea.width / 2, 0)
      barra.apuntar(tarea.clave, p.x, p.y)
    }
    onWheel: function(e) { if (!tarea.arrastrando) barra.rodar_tarea(tarea.clave, e.angleDelta.y > 0 ? -1 : 1) }
    onClicked: function(e) {
      if (movido) return
      if (e.button === Qt.RightButton) barra.menu_tarea(tarea.clave)
      else barra.pulsar_tarea(tarea.clave, e.button === Qt.MiddleButton)
    }
  }
}
