import QtQuick

Text {
  color: barra.tema.colores.texto
  font.family: barra.tema.fuente
  font.pixelSize: barra.tema.tamano
  font.bold: barra.tema.negrita
  textFormat: Text.PlainText
  // Con poca opacidad, un contorno para que se lea sobre cualquier fondo.
  style: barra.tema.contorno ? Text.Outline : Text.Normal
  styleColor: color.hslLightness > 0.5 ? "#A6000000" : "#8CFFFFFF"
  verticalAlignment: Text.AlignVCenter
  Behavior on color { ColorAnimation { duration: 350 } }
}
