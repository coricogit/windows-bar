import QtQuick

// Gris de escritorio de los noventa: un filo claro arriba y otro oscuro abajo,
// como una pieza en relieve.
Item {
  id: f
  property real radio: 0
  property real desde: 0
  property real total: 0
  readonly property bool deNoche: barra.momento === "noche"
  readonly property color luz: deNoche ? "#5A5A5A" : "#FFFFFF"
  readonly property color sombra: deNoche ? "#141414" : "#808080"
  readonly property bool arriba: barra.tema.lado === "arriba"
  readonly property bool vertical: barra.tema.vertical
  // El filo claro mira hacia la pantalla.
  Rectangle { visible: !f.vertical; width: parent.width; height: 1; y: f.arriba ? parent.height - 2 : 0; color: f.arriba ? f.sombra : "#DFDFDF" }
  Rectangle { visible: !f.vertical; width: parent.width; height: 1; y: f.arriba ? parent.height - 1 : 1; color: f.arriba ? "#000000" : f.luz }
  Rectangle { visible: f.vertical; height: parent.height; width: 2; x: barra.tema.lado === "izquierda" ? parent.width - 2 : 0; color: f.luz }
}
