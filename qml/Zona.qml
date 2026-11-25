import QtQuick

Grid {
  id: zona
  property var grupos: []
  property var tema
  property real alto: 40
  property real limite: 600
  property int piezas: 0
  // Lo que ocupa todo menos las ventanas.
  readonly property real otros: {
    var s = piezas * 0
    for (var i = 0; i < rep.count; i++) {
      var g = rep.itemAt(i)
      if (g) s += g.otros + spacing
    }
    return s
  }
  // Columnas justas: si sobran, Grid deja un hueco de más al final.
  readonly property int llenos: {
    var n = piezas * 0
    for (var i = 0; i < rep.count; i++) { var g = rep.itemAt(i); if (g && g.width > 0) n++ }
    return n
  }
  columns: tema.vertical ? 1 : Math.max(1, llenos)
  spacing: tema.separacion
  horizontalItemAlignment: Grid.AlignHCenter
  verticalItemAlignment: Grid.AlignVCenter
  Repeater {
    id: rep
    onItemAdded: zona.piezas++
    onItemRemoved: zona.piezas--
    model: zona.grupos
    Grupo { modulos: modelData; tema: zona.tema; alto: zona.alto; limite: zona.limite }
  }
}
