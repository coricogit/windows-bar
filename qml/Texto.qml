import QtQuick

Text {
  color: barra.tema.colores.texto
  font.family: barra.tema.fuente
  font.pixelSize: barra.tema.tamano
  font.bold: barra.tema.negrita
  textFormat: Text.PlainText
  verticalAlignment: Text.AlignVCenter
  Behavior on color { ColorAnimation { duration: 350 } }
}
