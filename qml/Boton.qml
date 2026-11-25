import QtQuick

Item {
  id: boton
  property real alto: 40
  property var colores: barra.tema.colores
  property alias texto: et.text
  property alias colorTexto: et.color
  property real tam: barra.tema.tamano
  property string fuente: barra.tema.fuente
  property string ayuda: ""
  property real ancho: et.implicitWidth + (barra.tema.compacto ? 12 : 16)
  readonly property alias encima: raton.containsMouse
  signal pulsado(int b)
  signal rueda(int paso)
  readonly property bool v: barra.tema.vertical
  width: v ? alto : ancho
  height: v ? (et.text === "" ? ancho : et.implicitHeight + 12) : alto
  Rectangle {
    anchors { fill: parent; topMargin: barra.tema.compacto ? 2 : 4; bottomMargin: barra.tema.compacto ? 2 : 4 }
    radius: Math.min(barra.tema.radio, 8)
    color: raton.containsMouse ? boton.colores.encima : "transparent"
    Behavior on color { ColorAnimation { duration: 120 } }
  }
  Texto { id: et; anchors.centerIn: parent; horizontalAlignment: Text.AlignHCenter; color: boton.colores.texto; font.pixelSize: boton.tam; font.family: boton.fuente }
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
