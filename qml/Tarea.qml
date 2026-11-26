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
  property bool atencion: false        // el programa pide atención (el naranja de Windows)
  property int cuenta: 0
  property int indice: 0
  property var lista
  // Arrastre: el botón sigue al ratón y los demás se apartan.
  property bool arrastrando: false
  readonly property bool v: tema.vertical
  property real ratonX: 0          // en la lista, a lo largo de la barra
  property real agarre: 0          // dónde se cogió, dentro del botón
  z: arrastrando ? 10 : 0
  transform: Translate {
    x: tarea.arrastrando && !tarea.v ? tarea.ratonX - tarea.agarre - tarea.x : 0
    y: tarea.arrastrando && tarea.v ? tarea.ratonX - tarea.agarre - tarea.y : 0
  }
  readonly property var c: tema.colores
  readonly property string estilo: tema.indicador
  readonly property real paso: tema.dock ? tema.icono + 16 : tema.burbujas ? alto : tema.compacto ? 32 : 42
  // Dock: los iconos crecen cuanto más cerca está el ratón, hacia dentro de la pantalla.
  readonly property real lupa: {
    if (!tema.dock || !lista || lista.ratonX < -500) return 1
    var d = Math.abs((v ? y + height / 2 : x + width / 2) - lista.ratonX)
    return 1 + tema.lupa * Math.max(0, 1 - d / 120)
  }
  readonly property int origen: ({ abajo: Item.Bottom, arriba: Item.Top, izquierda: Item.Left, derecha: Item.Right })[tema.lado] || Item.Bottom
  readonly property real hacia: tema.dock ? 3 : 0        // un poco hacia el borde: así cabe al crecer
  width: v ? alto : paso
  height: v ? paso : alto

  // Burbujas: un círculo por botón; la activa, con aro del color de acento.
  Rectangle {
    visible: tarea.tema.burbujas
    anchors.centerIn: parent
    width: Math.min(tarea.width, tarea.height) - 2; height: width
    radius: tarea.tema.pixelado ? 0 : width / 2
    color: raton.containsMouse || suelta.containsDrag ? Qt.lighter(tarea.c.isla, 1.25) : tarea.c.isla
    border.width: tarea.activa ? 2 : 1
    border.color: tarea.activa ? tarea.c.acento : tarea.abierta ? tarea.c.tenue : tarea.c.borde
    opacity: tarea.abierta || raton.containsMouse ? 1 : 0.8
    Behavior on color { ColorAnimation { duration: 140 } }
  }
  Rectangle {
    visible: !tarea.tema.burbujas
    anchors { fill: parent; margins: tarea.tema.compacto ? 1 : 3 }
    radius: Math.min(Math.max(tema.radio, tema.radioBoton), 10)
    color: tarea.activa && tarea.estilo === "relleno" ? tarea.c.acento
           : (raton.containsMouse && !tarea.tema.dock) || suelta.containsDrag || (tarea.activa && tarea.tema.fondoActiva && tarea.estilo !== "corchetes" && tarea.estilo !== "gota") ? tarea.c.encima : "transparent"
    border.width: tarea.elegida ? 2 : 0        // elegida con el teclado
    border.color: tarea.c.acento
    Behavior on color { ColorAnimation { duration: 140 } }
  }
  // Pide atención: un fondo cálido que late unas veces y se queda encendido.
  Rectangle {
    id: llama
    visible: tarea.atencion && !tarea.activa
    anchors { fill: parent; margins: tarea.tema.burbujas ? 1 : tarea.tema.compacto ? 1 : 3 }
    radius: tarea.tema.burbujas ? (tarea.tema.pixelado ? 0 : width / 2) : Math.min(Math.max(tarea.tema.radio, tarea.tema.radioBoton), 10)
    color: tarea.c.atencion || "#E8912D"
    opacity: 0.55
    SequentialAnimation on opacity {
      running: llama.visible && barra.animar
      loops: 4
      NumberAnimation { to: 0.85; duration: 450; easing.type: Easing.InOutSine }
      NumberAnimation { to: 0.35; duration: 450; easing.type: Easing.InOutSine }
      onFinished: llama.opacity = 0.55
    }
  }
  readonly property bool elegida: esPrimaria && barra.seleccion === "t:" + clave
  onElegidaChanged: {
    if (!elegida) { barra.soltar(clave); return }
    lista.positionViewAtIndex(indice, ListView.Contain)
    var p = tarea.mapToGlobal(tarea.width / 2, tarea.height / 2)
    barra.apuntar(clave, p.x, p.y)
  }

  Image {
    anchors.centerIn: parent
    anchors.verticalCenterOffset: tarea.v ? 0 : tarea.tema.lado === "arriba" ? -tarea.hacia : tarea.hacia
    anchors.horizontalCenterOffset: !tarea.v ? 0 : tarea.tema.lado === "izquierda" ? -tarea.hacia : tarea.hacia
    transformOrigin: tarea.tema.dock ? tarea.origen : Item.Center
    width: tarea.tema.icono; height: tarea.tema.icono
    sourceSize: Qt.size(32, 32)
    source: tarea.icono === "" ? "" : tarea.icono + tarea.tema.estiloIconos
    smooth: !tarea.tema.pixelado
    mipmap: !tarea.tema.pixelado
    opacity: tarea.minimizada ? 0.55 : 1
    scale: tarea.tema.dock ? tarea.lupa * (raton.pressed ? 0.9 : 1)
           : raton.pressed ? 0.85 : raton.containsMouse || suelta.containsDrag ? 1.1 : 1
    Behavior on scale { NumberAnimation { duration: tarea.tema.dock ? 70 : 110 } }
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

  // Archivos arrastrados desde otro programa: encima un momento, la ventana
  // pasa delante; soltados en el botón, se abren con este programa.
  DropArea {
    id: suelta
    anchors.fill: parent
    keys: ["text/uri-list"]
    onEntered: function(d) {
      if (!d.hasUrls) { d.accepted = false; return }
      d.acceptProposedAction()
      if (tarea.abierta) espera.restart()
    }
    onExited: espera.stop()
    onDropped: function(d) {
      espera.stop()
      if (!d.hasUrls) return
      d.acceptProposedAction()
      barra.soltar_archivos(tarea.clave, d.urls)
    }
    Timer { id: espera; interval: 600; onTriggered: barra.archivo_encima(tarea.clave) }
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
    function enLista(e) { var p = raton.mapToItem(tarea.lista.contentItem, e.x, e.y); return tarea.v ? p.y : p.x }
    onPressed: function(e) { movido = false; inicio = enLista(e); tarea.agarre = tarea.v ? e.y : e.x }
    onPositionChanged: function(e) {
      if (tarea.tema.dock && !tarea.arrastrando) tarea.lista.ratonX = enLista(e)
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
      var destino = Math.floor((x - tarea.agarre + tarea.paso / 2) / (tarea.paso + tarea.lista.spacing))
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
      if (!containsMouse && tarea.tema.dock) tarea.lista.ratonX = -1000
      if (!containsMouse) { barra.soltar(tarea.clave); return }
      var p = tarea.mapToGlobal(tarea.width / 2, tarea.height / 2)
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
