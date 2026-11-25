import QtQuick

// Cuadrícula tenue y una línea de luz que recorre el borde de arriba.
Item {
  id: f
  property real fase: 0
  Timer { interval: 80; repeat: true; running: f.visible && barra.animar; onTriggered: f.fase = (f.fase + 0.004) % 1 }
  Repeater {
    model: Math.ceil(f.width / 48)
    Rectangle { x: index * 48; width: 1; height: f.height; color: "#0D00E5FF" }
  }
  Rectangle { width: parent.width; height: 2; color: "#FF2E97" }
  Rectangle {
    width: parent.width; height: 14; y: 2
    gradient: Gradient {
      GradientStop { position: 0; color: "#66FF2E97" }
      GradientStop { position: 1; color: "#00FF2E97" }
    }
  }
  Repeater {
    model: 2
    Rectangle {
      width: 360; height: 2
      x: ((f.fase + index * 0.5) % 1) * (f.width + 360) - 360
      gradient: Gradient {
        orientation: Gradient.Horizontal
        GradientStop { position: 0; color: "#0000E5FF" }
        GradientStop { position: 0.8; color: "#00E5FF" }
        GradientStop { position: 1; color: "#FFFFFF" }
      }
    }
  }
}
