import QtQuick

// Las barras de sonido (barra/cava.py). Crecen desde abajo, del color del acento
// al segundo acento; en los temas pixelados, a escalones.
Item {
  id: cava
  property var tema
  property int cuantas: 16
  readonly property var c: tema.colores
  readonly property color uno: c.cava1 || c.acento
  readonly property color dos: c.cava2 || c.acento2
  readonly property real paso: width / cuantas
  readonly property real gruesa: Math.max(2, Math.floor(paso) - (paso >= 4 ? 2 : 1))

  Repeater {
    model: cava.cuantas
    Rectangle {
      readonly property real valor: barra.cava[Math.floor(index * 16 / cava.cuantas)] || 0
      readonly property real alta: Math.max(2, cava.height * valor / 100)
      readonly property real m: index / Math.max(1, cava.cuantas - 1)
      x: Math.round(index * cava.paso)
      width: cava.gruesa
      height: cava.tema.pixelado ? Math.max(2, Math.round(alta / 3) * 3) : Math.round(alta)
      y: cava.height - height
      radius: cava.tema.pixelado ? 0 : Math.min(1.5, width / 2)
      color: Qt.rgba(cava.uno.r + (cava.dos.r - cava.uno.r) * m, cava.uno.g + (cava.dos.g - cava.uno.g) * m,
                     cava.uno.b + (cava.dos.b - cava.uno.b) * m, 1)
    }
  }
}
