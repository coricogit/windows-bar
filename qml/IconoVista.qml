import QtQuick

// El icono de la vista de tareas de Windows 11: dos ventanas cuadradas, la de
// atrás solo con el borde y la de delante rellena. Windows lo dibuja con una
// animación compilada dentro de Taskbar.View.dll, sin imagen que copiar; esta
// es una reconstrucción a 20 px que crece o encoge con `lado`.
Item {
  id: icono
  property real lado: 20
  property color tinta: "#FFFFFF"
  property bool pulsado: false
  readonly property real u: lado / 20
  width: lado
  height: lado
  scale: pulsado ? 0.88 : 1
  Behavior on scale { NumberAnimation { duration: 90 } }

  Rectangle {          // la de atrás
    x: 7 * icono.u; y: 1.5 * icono.u
    width: 11.5 * icono.u; height: 11.5 * icono.u
    radius: 2.5 * icono.u
    color: "transparent"
    border.width: Math.max(1, 1.5 * icono.u)
    border.color: icono.tinta
    antialiasing: true
  }
  Rectangle {          // la de delante, rellena; tapa la esquina de la otra
    x: 1.5 * icono.u; y: 7 * icono.u
    width: 11.5 * icono.u; height: 11.5 * icono.u
    radius: 2.5 * icono.u
    antialiasing: true
    border.width: Math.max(1, 1.5 * icono.u)
    border.color: icono.tinta
    gradient: Gradient {
      GradientStop { position: 0; color: Qt.rgba(icono.tinta.r, icono.tinta.g, icono.tinta.b, 0.95) }
      GradientStop { position: 1; color: Qt.rgba(icono.tinta.r, icono.tinta.g, icono.tinta.b, 0.72) }
    }
  }
}
