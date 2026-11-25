import QtQuick

Row {
  id: zona
  property var grupos: []
  property var tema
  property real alto: 40
  property real limite: 600
  height: tema.alto
  spacing: tema.separacion
  Repeater {
    model: zona.grupos
    Grupo { modulos: modelData; tema: zona.tema; alto: zona.alto; limite: zona.limite }
  }
}
