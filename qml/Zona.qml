import QtQuick

// Una parte de la barra. Si no cabe en `hueco`, esconde primero lo menos importante.
Grid {
  id: zona
  property var grupos: []
  property var tema
  property real alto: 40
  property real limite: 600          // lo que pueden ocupar las ventanas
  property real hueco: 100000
  property int piezas: 0
  property real total: 0             // lo que mide la barra
  readonly property bool v: tema.vertical
  readonly property real mio: v ? height : width

  function suma(f) {
    var s = piezas * 0
    for (var i = 0; i < rep.count; i++) { var g = rep.itemAt(i); if (g) s += f(g) }
    return s
  }
  // Todo menos las ventanas, y lo que nunca se esconde (sin las ventanas).
  readonly property real otros: suma(function(g) { return g.otros > 0 || g.conTareas ? g.otros + spacing : 0 })
  readonly property real esencial: suma(function(g) { return g.rango >= 99 && g.otros > 0 ? g.otros + spacing : 0 })
  readonly property var fuera: {
    var l = [], total = -spacing, out = []
    for (var i = 0; i < rep.count + piezas * 0; i++) {
      var g = rep.itemAt(i)
      if (!g || g.natural <= 0) continue
      total += g.natural + spacing
      if (g.rango < 99) l.push({ i: i, rango: g.rango, n: g.natural + spacing })
    }
    l.sort(function(a, b) { return a.rango - b.rango })
    for (var j = 0; j < l.length && total > hueco; j++) { out.push(l[j].i); total -= l[j].n }
    return out
  }
  readonly property bool desborda: suma(function(g) { return g.desborda ? 1 : 0 }) > 0
  // Columnas justas: si sobran, Grid deja un hueco de más al final.
  readonly property int llenos: suma(function(g) { return g.width > 0 ? 1 : 0 })
  columns: v ? 1 : Math.max(1, llenos)
  spacing: tema.separacion
  horizontalItemAlignment: Grid.AlignHCenter
  verticalItemAlignment: Grid.AlignVCenter
  Repeater {
    id: rep
    onItemAdded: zona.piezas++
    onItemRemoved: zona.piezas--
    model: zona.grupos
    Grupo {
      modulos: modelData
      tema: zona.tema
      alto: zona.alto
      limite: zona.limite
      desde: zona.x + x
      total: zona.total
      oculto: zona.fuera.indexOf(index) >= 0
    }
  }
}
