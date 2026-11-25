import QtQuick
import BarraTemas

// Uno o varios módulos juntos; en los temas de islas, con su propio fondo.
Rectangle {
  id: grupo
  property var modulos: []
  property var tema
  property real alto: 40
  property real limite: 600
  readonly property bool isla: tema.forma === "islas"
  // Sobre un fondo claro, el vidrio usa los colores oscuros del tema.
  readonly property bool clara: vidrio.item ? vidrio.item.clara : false
  readonly property var temaPieza: clara ? Object.assign({}, tema, { colores: Object.assign({}, tema.colores, tema.coloresClaros) }) : tema

  anchors.verticalCenter: parent ? parent.verticalCenter : undefined
  height: alto
  width: fila.width + (isla ? 12 : 0)
  opacity: modulos.length === 1 && modulos[0] === "musica" && barra.cancion.titulo === "" ? 0 : 1
  enabled: opacity > 0
  radius: Math.min(tema.radio, alto / 2)
  color: tema.colores.isla
  border.width: isla ? tema.borde : 0
  border.color: tema.colores.borde
  Behavior on color { ColorAnimation { duration: 350 } }

  // Vidrio de verdad (barra/vidrio.py), con un destello que sigue al ratón.
  HoverHandler { id: raton; enabled: grupo.isla && grupo.tema.vidrio }
  Loader {
    id: vidrio
    anchors.fill: parent
    active: grupo.isla && grupo.tema.vidrio
    sourceComponent: Vidrio {
      radio: grupo.radius
      luzX: raton.hovered ? raton.point.position.x : -1
    }
  }

  // Clic derecho donde no hay botón: menú de temas.
  MouseArea { anchors.fill: parent; acceptedButtons: Qt.RightButton; onClicked: barra.menu() }

  Row {
    id: fila
    anchors.centerIn: parent
    height: grupo.alto
    spacing: 2
    Texto { text: "["; height: grupo.alto; color: grupo.tema.colores.tenue; visible: grupo.tema.corchetes }
    Repeater {
      model: grupo.modulos
      Modulo { nombre: modelData; tema: grupo.temaPieza; alto: grupo.alto; limite: grupo.limite }
    }
    Texto { text: "]"; height: grupo.alto; color: grupo.tema.colores.tenue; visible: grupo.tema.corchetes }
  }
}
