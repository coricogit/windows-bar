import QtQuick

// Líneas de monitor antiguo y una barra de barrido.
Item {
  id: f
  Repeater {
    model: Math.ceil(f.height / 3)
    Rectangle { y: index * 3; width: f.width; height: 1; color: "#38000000" }
  }
  Rectangle {
    id: barrido
    width: f.width; height: 10
    color: "#124DFF88"
    Timer {
      interval: 120; repeat: true; running: f.visible && barra.animar
      onTriggered: barrido.y = barrido.y > f.height ? -40 : barrido.y + 2
    }
  }
}
