import QtQuick

Grid {
  id: zona
  property var grupos: []
  property var tema
  property real alto: 40
  property real limite: 600
  columns: tema.vertical ? 1 : 99
  spacing: tema.separacion
  horizontalItemAlignment: Grid.AlignHCenter
  verticalItemAlignment: Grid.AlignVCenter
  Repeater {
    model: zona.grupos
    Grupo { modulos: modelData; tema: zona.tema; alto: zona.alto; limite: zona.limite }
  }
}
