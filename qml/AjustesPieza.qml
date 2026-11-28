import QtQuick

// Una opción del menú de ajustes (qml/Ajustes.qml), en cualquiera de sus formas:
// "baldosa" (con imagen, dibujo o muestras de color), "opcion" (pastilla), "interruptor",
// "boton" o "categoria". Con teclado (Tab, flechas, Intro, Espacio), con el foco a la vista
// y con nombre, papel y estado para el lector de pantalla (WCAG 2.1.1, 2.4.7, 4.1.2).
FocusScope {
  id: pieza
  property var o: ({})               // la opción: id, texto, elegido / marcado, imagen, muestra, glifo, prueba
  property string forma: "opcion"
  property string seccion: ""        // para el lector de pantalla: «Hora y fecha: Agujas»
  property var c: ({})               // colores del menú
  property real esc: 1
  property string imagen: ""         // la miniatura (puede llegar después)
  property var muestra: o.muestra
  readonly property bool elegido: !!o.elegido || !!o.marcado
  readonly property bool encima: raton.containsMouse
  signal activar()
  signal probar()
  signal dejar()
  signal flecha(int paso)            // categorías: se cambia con las flechas (una sola parada de Tab)
  property bool quiereFoco: false    // al rehacer el menú tras elegir, el foco vuelve aquí (WCAG 2.4.3)
  onQuiereFocoChanged: if (quiereFoco) forceActiveFocus(Qt.OtherFocusReason)
  Component.onCompleted: if (quiereFoco) forceActiveFocus(Qt.OtherFocusReason)

  activeFocusOnTab: forma !== "categoria" || elegido
  implicitWidth: forma === "baldosa" ? Math.round(176 * esc)
                 : forma === "categoria" ? Math.round(88 * esc)
                 : etiqueta.implicitWidth + Math.round((forma === "interruptor" ? 52 : 30) * esc)
  implicitHeight: forma === "baldosa" ? Math.round(98 * esc) : forma === "categoria" ? Math.round(64 * esc) : Math.round(34 * esc)
  width: implicitWidth
  height: implicitHeight

  Accessible.role: forma === "interruptor" ? Accessible.CheckBox : forma === "boton" ? Accessible.Button
                   : forma === "categoria" ? Accessible.PageTab : Accessible.RadioButton
  Accessible.name: (seccion !== "" && forma !== "categoria" && forma !== "boton" ? seccion + ": " : "") + (o.texto || "")
  Accessible.checkable: forma !== "boton"
  Accessible.checked: elegido
  Accessible.focusable: true
  Accessible.onPressAction: pieza.activar()
  Accessible.onToggleAction: pieza.activar()

  Keys.onReturnPressed: pieza.activar()
  Keys.onEnterPressed: pieza.activar()
  Keys.onSpacePressed: pieza.activar()
  function mover(paso) {
    if (forma === "categoria") { pieza.flecha(paso); return }
    pieza.nextItemInFocusChain(paso > 0).forceActiveFocus(paso > 0 ? Qt.TabFocusReason : Qt.BacktabFocusReason)
  }
  Keys.onRightPressed: mover(1)
  Keys.onDownPressed: forma === "categoria" ? pieza.nextItemInFocusChain(true).forceActiveFocus(Qt.TabFocusReason) : mover(1)
  Keys.onLeftPressed: mover(-1)
  Keys.onUpPressed: forma === "categoria" ? undefined : mover(-1)
  onActiveFocusChanged: if (activeFocus && o.prueba) pieza.probar()

  // ---- el foco: un anillo del color del texto, fuera de la pieza (3:1 con el fondo) ----
  Rectangle {
    visible: pieza.activeFocus
    anchors { fill: forma === "baldosa" ? cuadro : parent; margins: -3 }
    radius: (forma === "opcion" || forma === "interruptor" || forma === "categoria" ? height / 2 : Math.round(10 * esc))
    color: "transparent"
    border.width: 2
    border.color: pieza.c.foco || "#FFFFFF"
    z: 5
  }

  // ---- baldosa: la imagen (o el dibujo) y el nombre debajo ----
  Rectangle {
    id: cuadro
    visible: forma === "baldosa"
    width: parent.width; height: Math.round(70 * esc)
    radius: Math.round(8 * esc)
    color: pieza.c.hueco || "#1A1A1A"
    border.width: pieza.elegido ? 2 : 1
    border.color: pieza.elegido ? pieza.c.acento : pieza.encima ? pieza.c.tenue : pieza.c.linea
    clip: true
    Image {
      visible: pieza.imagen !== ""
      anchors.centerIn: parent
      source: pieza.imagen
      width: parent.width - Math.round(12 * esc); height: parent.height - Math.round(12 * esc)
      fillMode: Image.PreserveAspectFit
      sourceSize: Qt.size(width * 2, height * 2)
      smooth: true; mipmap: true
      asynchronous: true
    }
    // Sin imagen todavía (o «Oculto»): su icono.
    Text {
      visible: pieza.imagen === "" && pieza.muestra === undefined
      anchors.centerIn: parent
      text: o.glifo || ""
      font.family: "Segoe Fluent Icons"
      font.pixelSize: Math.round(20 * esc)
      color: pieza.c.tenue
    }
    // Posición: la pantalla con la barra en ese lado.
    Rectangle {
      visible: typeof pieza.muestra === "string"
      anchors.centerIn: parent
      width: Math.round(96 * esc); height: Math.round(54 * esc); radius: 3
      gradient: Gradient { GradientStop { position: 0; color: "#3B5A78" } GradientStop { position: 1; color: "#7B5E8C" } }
      Rectangle {
        readonly property string l: typeof pieza.muestra === "string" ? pieza.muestra : ""
        readonly property bool lado: l === "izquierda" || l === "derecha"
        color: "#141414"; radius: 2
        border.width: 1; border.color: pieza.c.acento
        x: l === "derecha" ? parent.width - width - 2 : lado ? 2 : 10
        y: l === "abajo" ? parent.height - height - 2 : l === "arriba" ? 2 : 6
        width: lado ? Math.round(7 * esc) : parent.width - 20
        height: lado ? parent.height - 12 : Math.round(7 * esc)
      }
    }
    // Colores: tres muestras.
    Row {
      visible: Array.isArray(pieza.muestra)
      anchors.centerIn: parent
      spacing: Math.round(6 * esc)
      Repeater {
        model: Array.isArray(pieza.muestra) ? pieza.muestra : []
        Rectangle { width: Math.round(22 * esc); height: width; radius: width / 2; color: modelData; border.width: 1; border.color: "#80FFFFFF" }
      }
    }
    Rectangle {          // lo elegido no se dice solo con color (WCAG 1.4.1): una marca
      visible: pieza.elegido
      anchors { right: parent.right; top: parent.top; margins: Math.round(5 * esc) }
      width: Math.round(18 * esc); height: width; radius: width / 2
      color: pieza.c.acento
      Text { anchors.centerIn: parent; text: ""; font.family: "Segoe Fluent Icons"; font.pixelSize: Math.round(10 * esc); color: pieza.c.sobreAcento }
    }
  }

  // ---- pastilla (opción, interruptor, botón, categoría) ----
  Rectangle {
    visible: forma !== "baldosa"
    anchors.fill: parent
    radius: forma === "boton" ? Math.round(6 * esc) : height / 2
    color: forma === "categoria" ? (pieza.elegido ? pieza.c.acento : pieza.encima ? pieza.c.tarjetaEncima : pieza.c.tarjeta)
           : (forma === "opcion" && pieza.elegido) ? pieza.c.acentoSuave
           : pieza.encima ? pieza.c.tarjetaEncima : pieza.c.tarjeta
    border.width: (forma === "opcion" || forma === "interruptor") && pieza.elegido ? 2 : 1
    border.color: (forma === "opcion" || forma === "interruptor") && pieza.elegido ? pieza.c.acento : pieza.c.linea
  }
  // Interruptor: la casilla, con marca si está puesto.
  Rectangle {
    visible: forma === "interruptor"
    x: Math.round(12 * esc); anchors.verticalCenter: parent.verticalCenter
    width: Math.round(18 * esc); height: width; radius: Math.round(4 * esc)
    color: pieza.elegido ? pieza.c.acento : "transparent"
    border.width: 2; border.color: pieza.elegido ? pieza.c.acento : pieza.c.tenue
    Text { visible: pieza.elegido; anchors.centerIn: parent; text: ""; font.family: "Segoe Fluent Icons"; font.pixelSize: Math.round(11 * esc); color: pieza.c.sobreAcento }
  }
  // Categoría: icono arriba y nombre debajo.
  Text {
    visible: forma === "categoria"
    anchors.horizontalCenter: parent.horizontalCenter
    y: Math.round(10 * esc)
    text: o.glifo || ""
    font.family: "Segoe Fluent Icons"
    font.pixelSize: Math.round(18 * esc)
    color: pieza.elegido ? pieza.c.sobreAcento : pieza.c.texto
  }
  Text {
    id: etiqueta
    text: (forma === "opcion" && pieza.elegido ? "✓  " : "") + (o.texto || "")
    color: forma === "categoria" && pieza.elegido ? pieza.c.sobreAcento : pieza.c.texto
    font.family: pieza.c.fuente || "Segoe UI"
    font.pixelSize: Math.round((forma === "categoria" ? 12 : 13) * esc)
    font.bold: forma === "baldosa" && pieza.elegido
    elide: Text.ElideRight
    width: forma === "baldosa" ? parent.width : implicitWidth
    horizontalAlignment: Text.AlignHCenter
    x: forma === "interruptor" ? Math.round(40 * esc) : forma === "baldosa" ? 0 : (parent.width - width) / 2
    y: forma === "baldosa" ? cuadro.height + Math.round(6 * esc)
       : forma === "categoria" ? Math.round(38 * esc) : (parent.height - height) / 2
  }

  MouseArea {
    id: raton
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onEntered: if (o.prueba) pieza.probar()
    onExited: if (o.prueba) pieza.dejar()
    onClicked: { pieza.forceActiveFocus(Qt.MouseFocusReason); pieza.activar() }
  }
}
