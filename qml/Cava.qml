import QtQuick

// Las barras de sonido (barra/cava.py), con la forma de cada tema (`cava` en
// tema.json): "barras", "neon", "petalos", "hojas" o "bloques".
Item {
  id: cava
  property var tema
  property int cuantas: 16
  readonly property var c: tema.colores
  readonly property string forma: tema.cava
  readonly property color uno: c.cava1 || c.acento
  readonly property color dos: c.cava2 || c.acento2
  readonly property real paso: width / cuantas
  readonly property real gruesa: Math.max(2, Math.floor(paso) - (paso >= 4 ? 2 : 1))
  readonly property bool tallos: forma === "petalos" || forma === "hojas"
  readonly property real punta: Math.min(7, gruesa + 2)
  // Una sola lectura por fotograma: leer `barra.cava` desde cada barra pedía la
  // lista entera a Python 16 veces.
  readonly property var datos: barra.cava
  function valor(i) { return datos[Math.floor(i * 16 / cuantas)] || 0 }

  function mezcla(a, b, m) { return Qt.rgba(a.r + (b.r - a.r) * m, a.g + (b.g - a.g) * m, a.b + (b.b - a.b) * m, 1) }

  Repeater {
    model: cava.forma === "bloques" ? 0 : cava.cuantas
    Item {
      id: una
      readonly property real valor: cava.valor(index)
      readonly property color tono: cava.mezcla(cava.uno, cava.dos, index / Math.max(1, cava.cuantas - 1))
      x: Math.round(index * cava.paso)
      width: cava.gruesa
      height: Math.round(Math.max(2, (cava.height - (cava.tallos ? 3 : 0)) * valor / 100))
      y: cava.height - height

      Rectangle {        // el resplandor del neón
        visible: cava.forma === "neon"
        anchors { fill: parent; margins: -2 }
        radius: 3
        color: Qt.rgba(una.tono.r, una.tono.g, una.tono.b, 0.20)
      }
      Rectangle {
        x: cava.tallos ? Math.floor((parent.width - width) / 2) : 0
        width: cava.tallos ? 2 : parent.width
        height: parent.height
        radius: Math.min(1.5, width / 2)
        color: cava.tallos ? Qt.rgba(una.tono.r, una.tono.g, una.tono.b, 0.6) : una.tono
      }
      Rectangle {        // la punta clara del neón
        visible: cava.forma === "neon" && parent.height > 4
        width: parent.width; height: 2; radius: 1
        color: "#E6FFFFFF"
      }
      Rectangle {        // un pétalo o una hoja en la punta
        visible: cava.tallos
        readonly property bool izq: index % 2 === 1
        width: cava.punta; height: cava.punta
        x: (parent.width - width) / 2
        y: -height / 2 + 1
        rotation: cava.forma === "petalos" ? 45 : izq ? 8 : -8
        topLeftRadius: cava.forma === "petalos" || !izq ? width : 1
        bottomRightRadius: topLeftRadius === width ? width : 1
        topRightRadius: topLeftRadius === width ? 1 : width
        bottomLeftRadius: topRightRadius
        color: una.tono
      }
    }
  }

  // Bloques: cada barra, una pila de ladrillos; los de arriba, del color de aviso.
  readonly property int filas: cava.forma === "bloques" ? Math.max(3, Math.floor((height + 1) / 5)) : 0
  // Cada pila es una columna fija de ladrillos dentro de un recorte que crece desde
  // abajo: por fotograma cambia un alto, no la visibilidad de cada ladrillo.
  Repeater {
    model: cava.filas > 0 ? cava.cuantas : 0
    Item {
      id: pila
      readonly property int llenos: Math.max(1, Math.round(cava.valor(index) / 100 * cava.filas))
      x: Math.round(index * cava.paso)
      y: cava.height - height
      width: cava.gruesa
      height: llenos * 5
      clip: true
      Item {
        y: pila.height - cava.height
        width: pila.width; height: cava.height
        Repeater {
          model: cava.filas
          Rectangle {
            width: pila.width; height: 4
            y: cava.height - 4 - index * 5
            color: index >= cava.filas - 1 ? cava.c.alerta : cava.mezcla(cava.uno, cava.dos, index / Math.max(1, cava.filas - 2))
          }
        }
      }
    }
  }
}
