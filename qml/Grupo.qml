import QtQuick
import BarraTemas

// Uno o varios módulos juntos; en los temas de islas, con su propio fondo.
Rectangle {
  id: grupo
  property var modulos: []
  property var tema
  property real alto: 40
  property real limite: 600
  readonly property bool isla: tema.forma === "islas" && !tema.unica
  readonly property int llenos: {        // columnas justas, como en Zona
    var n = piezas * 0
    for (var i = 0; i < rep.count; i++) { var m = rep.itemAt(i); if (m && m.width > 0) n++ }
    return n
  }
  // Lo que ocupa todo menos las ventanas, para saber cuánto les queda.
  property int piezas: 0
  readonly property real otros: {
    var s = piezas * 0
    for (var i = 0; i < rep.count; i++) {
      var m = rep.itemAt(i)
      if (m && m.nombre !== "tareas") s += (v ? m.height : m.width) + fila.spacing
    }
    return s
  }
  // Sobre un fondo claro, el vidrio usa los colores oscuros del tema.
  readonly property bool clara: vidrio.item ? vidrio.item.clara : tema.clara
  readonly property var temaPieza: clara ? Object.assign({}, tema, { colores: Object.assign({}, tema.colores, tema.coloresClaros),
    logo: Object.assign({}, tema.logo, { colores: tema.logoClaros }) }) : tema

  readonly property bool v: tema.vertical
  width: v ? alto : fila.width + (isla ? 12 : 0)
  height: v ? fila.height + (isla ? 12 : 0) : alto
  opacity: modulos.length === 1 && modulos[0] === "musica" && barra.cancion.titulo === "" ? 0 : 1
  enabled: opacity > 0
  radius: Math.min(tema.radio, alto / 2)
  color: tema.unica ? "transparent" : tema.colores.isla
  border.width: isla ? tema.borde : 0
  border.color: tema.colores.borde
  Behavior on color { ColorAnimation { duration: 350 } }

  // Vidrio de verdad (barra/vidrio.py), con un destello que sigue al ratón.
  HoverHandler { id: raton; enabled: grupo.isla && grupo.tema.vidrio }
  Loader {
    id: vidrio
    anchors.fill: parent
    active: grupo.isla && (grupo.tema.vidrio || grupo.tema.adapta)
    sourceComponent: Vidrio {
      pintar: grupo.tema.vidrio
      radio: grupo.radius
      luzX: raton.hovered ? raton.point.position.x : -1
    }
  }

  // Clic derecho donde no hay botón: menú de temas.
  MouseArea { anchors.fill: parent; acceptedButtons: Qt.RightButton; onClicked: barra.menu() }

  Grid {
    id: fila
    anchors.centerIn: parent
    columns: grupo.v ? 1 : Math.max(1, grupo.llenos + (grupo.tema.corchetes ? 2 : 0))
    spacing: 2 + grupo.tema.aire
    horizontalItemAlignment: Grid.AlignHCenter
    verticalItemAlignment: Grid.AlignVCenter
    Texto { text: "["; height: grupo.alto; color: grupo.tema.colores.tenue; visible: grupo.tema.corchetes && !grupo.v }
    Repeater {
      id: rep
      onItemAdded: grupo.piezas++
      onItemRemoved: grupo.piezas--
      model: grupo.modulos
      Modulo { nombre: modelData; tema: grupo.temaPieza; alto: grupo.alto; limite: grupo.limite }
    }
    Texto { text: "]"; height: grupo.alto; color: grupo.tema.colores.tenue; visible: grupo.tema.corchetes && !grupo.v }
  }
}
