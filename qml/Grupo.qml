import QtQuick
import BarraTemas

// Uno o varios módulos juntos; en los temas de islas, con su propio fondo.
Rectangle {
  id: grupo
  property var modulos: []
  property var tema
  property real alto: 40
  property real limite: 600
  property real desde: 0             // dónde está y cuánto mide la barra, para el paisaje
  property real total: 0
  // Sin pieza propia: con una isla para todo, en Esquinas (la pone la zona) y,
  // en Burbujas, la de los programas (cada uno lleva su círculo).
  readonly property bool isla: tema.forma === "islas" && !tema.unica && !tema.esquinas && !(tema.burbujas && conTareas)
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
    return vacio ? 0 : s + (isla && (s > 0 || conTareas) ? 12 : 0)
  }
  // Sobre un fondo claro, el vidrio usa los colores oscuros del tema.
  readonly property bool clara: vidrio.item ? vidrio.item.clara : tema.clara
  readonly property var temaPieza: clara ? Object.assign({}, tema, { colores: Object.assign({}, tema.colores, tema.coloresClaros),
    logo: Object.assign({}, tema.logo, { colores: tema.logoClaros }) }) : tema

  readonly property bool v: tema.vertical
  // Al no caber se queda sin tamaño, pero sus piezas siguen midiendo lo suyo.
  property bool oculto: false
  readonly property bool conTareas: modulos.indexOf("tareas") >= 0
  readonly property bool vacio: modulos.length === 1 && modulos[0] === "musica" && (barra.cancion.titulo === "" || !barra.conCava)
  readonly property real natural: vacio ? 0 : (v ? fila.height : fila.width) + (isla ? 12 : 0)
  readonly property int rango: {        // lo de menos rango se esconde antes
    var orden = { titulo: 0, musica: 1, widgets: 2, sistema: 3, claudito: 4, temas: 5 }, r = 0
    for (var i = 0; i < modulos.length; i++) r = Math.max(r, modulos[i] in orden ? orden[modulos[i]] : 99)
    return r
  }
  width: v ? alto : oculto ? 0 : natural
  height: v ? (oculto ? 0 : natural) : alto
  opacity: oculto || vacio ? 0 : 1
  enabled: opacity > 0
  radius: Math.min(tema.radio, alto / 2)
  color: isla ? tema.colores.isla : "transparent"
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

  // El paisaje del tema, dentro de la pieza.
  Loader {
    anchors { fill: parent; margins: grupo.tema.borde }
    active: grupo.isla && grupo.tema.dentro && grupo.tema.fondoUrl !== "" && grupo.width > 20
    source: active ? grupo.tema.fondoUrl : ""
    opacity: (grupo.tema.variante === "pastel" ? 0.35 : 1) * (grupo.tema.adorno === undefined ? 1 : grupo.tema.adorno)
    onLoaded: {
      item.radio = Qt.binding(function() { return Math.max(0, grupo.radius - grupo.tema.borde) })
      item.desde = Qt.binding(function() { return grupo.desde })
      item.total = Qt.binding(function() { return grupo.total })
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
