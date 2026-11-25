import QtQuick

// Uno o varios módulos juntos; en los temas de islas, con su propio fondo.
Rectangle {
  id: grupo
  property var modulos: []
  property var tema
  property real alto: 40
  property real limite: 600
  readonly property bool isla: tema.forma === "islas"

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

  // Vidrio: velo, borde interior, luz arriba, reflejo abajo y un destello que sigue al ratón.
  HoverHandler { id: raton; enabled: grupo.isla && grupo.tema.vidrio }
  Loader {
    anchors.fill: parent
    active: grupo.isla && grupo.tema.vidrio
    sourceComponent: Item {
      Rectangle {
        anchors { fill: parent; margins: 1 }
        radius: grupo.radius - 1
        border.width: 1
        border.color: "#2EFFFFFF"
        gradient: Gradient {
          GradientStop { position: 0; color: "#5CFFFFFF" }
          GradientStop { position: 0.35; color: "#1AFFFFFF" }
          GradientStop { position: 0.7; color: "#0AFFFFFF" }
          GradientStop { position: 1; color: "#3DFFFFFF" }
        }
      }
      Rectangle {
        anchors { left: parent.left; right: parent.right; top: parent.top; leftMargin: grupo.radius * 0.7; rightMargin: grupo.radius * 0.7; topMargin: 2 }
        height: 2; radius: 1
        gradient: Gradient {
          orientation: Gradient.Horizontal
          GradientStop { position: 0; color: "#00FFFFFF" }
          GradientStop { position: 0.3; color: "#D9FFFFFF" }
          GradientStop { position: 0.75; color: "#66FFFFFF" }
          GradientStop { position: 1; color: "#00FFFFFF" }
        }
      }
      Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; leftMargin: grupo.radius; rightMargin: grupo.radius; bottomMargin: 2 }
        height: 1
        gradient: Gradient {
          orientation: Gradient.Horizontal
          GradientStop { position: 0; color: "#008FD3FF" }
          GradientStop { position: 0.4; color: "#998FD3FF" }
          GradientStop { position: 0.7; color: "#99FFC6E8" }
          GradientStop { position: 1; color: "#00FFC6E8" }
        }
      }
      Rectangle {
        visible: raton.hovered && grupo.width > 90
        width: 70; height: parent.height - 4; y: 2
        x: Math.max(grupo.radius / 2, Math.min(grupo.width - width - grupo.radius / 2, raton.point.position.x - width / 2))
        gradient: Gradient {
          orientation: Gradient.Horizontal
          GradientStop { position: 0; color: "#00FFFFFF" }
          GradientStop { position: 0.5; color: "#38FFFFFF" }
          GradientStop { position: 1; color: "#00FFFFFF" }
        }
      }
    }
  }

  Row {
    id: fila
    anchors.centerIn: parent
    height: grupo.alto
    spacing: 2
    Texto { text: "["; height: grupo.alto; color: grupo.tema.colores.tenue; visible: grupo.tema.corchetes }
    Repeater {
      model: grupo.modulos
      Modulo { nombre: modelData; tema: grupo.tema; alto: grupo.alto; limite: grupo.limite }
    }
    Texto { text: "]"; height: grupo.alto; color: grupo.tema.colores.tenue; visible: grupo.tema.corchetes }
  }
}
