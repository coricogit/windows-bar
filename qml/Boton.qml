import QtQuick

Item {
  id: boton
  property real alto: 40
  property var colores: barra.tema.colores
  property alias texto: et.text
  property alias colorTexto: et.color
  property real tam: barra.tema.tamano
  property string fuente: barra.tema.fuente
  property int alineado: Text.AlignHCenter
  property string ayuda: ""
  property string glifo: ""          // iconos de Segoe Fluent delante del texto (red, batería)
  property string nombre: ""         // para el lector de pantalla; si no, lo primero de la ayuda
  // Lector de pantalla (WCAG 4.1.2): un botón con nombre, que se pulsa también desde él.
  Accessible.role: Accessible.Button
  Accessible.name: nombre !== "" ? nombre : ayuda !== "" ? ayuda.split(" · ")[0] : et.text
  Accessible.description: ayuda
  Accessible.focusable: true
  Accessible.onPressAction: boton.pulsado(Qt.LeftButton)
  readonly property real natural: fila.implicitWidth + (barra.tema.compacto ? 12 : 16)
  property real ancho: natural
  readonly property alias encima: raton.containsMouse
  signal pulsado(int b)
  signal rueda(int paso)
  readonly property bool v: barra.tema.vertical
  width: v ? alto : ancho
  height: v ? (et.text === "" && glifo === "" ? ancho : fila.implicitHeight + 12) : alto
  Rectangle {
    anchors { fill: parent; topMargin: barra.tema.compacto ? 2 : 4; bottomMargin: barra.tema.compacto ? 2 : 4 }
    radius: Math.min(Math.max(barra.tema.radio, barra.tema.radioBoton), 8)
    color: raton.containsMouse ? boton.colores.encima : "transparent"
    Behavior on color { ColorAnimation { duration: 120 } }
  }
  Grid {
    id: fila
    anchors.centerIn: parent
    columns: boton.v ? 1 : 2
    columnSpacing: boton.glifo !== "" && et.text !== "" ? 7 : 0
    rowSpacing: boton.glifo !== "" && et.text !== "" ? 4 : 0
    horizontalItemAlignment: Grid.AlignHCenter
    verticalItemAlignment: Grid.AlignVCenter
    Texto {
      visible: boton.glifo !== ""
      text: boton.glifo
      color: et.color
      font.family: "Segoe Fluent Icons"
      font.pixelSize: 15
      font.bold: false
      font.letterSpacing: 5
    }
    Texto { id: et; horizontalAlignment: boton.alineado; color: boton.colores.texto; font.pixelSize: boton.tam; font.family: boton.fuente }
  }
  Aviso { texto: boton.ayuda; fuente: raton }
  MouseArea {
    id: raton
    anchors.fill: parent
    hoverEnabled: true
    acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
    onClicked: function(e) { boton.pulsado(e.button) }
    onWheel: function(e) { boton.rueda(e.angleDelta.y > 0 ? 1 : -1) }
  }
}
