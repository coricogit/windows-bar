import QtQuick

// Claudito camina por el hueco libre cuando no hace nada; si Claude trabaja o
// te necesita, se para y lo muestra.
Item {
  id: paseo
  property bool activo: false
  property real desde: 0
  property real hasta: 0
  readonly property bool cabe: hasta - desde > 90
  readonly property string modo: barra.claude.modo
  readonly property bool andando: cabe && (modo === "idle" || modo === "wake")
  property real pos: 0          // dentro del hueco
  property int sentido: 1
  readonly property real tramo: Math.max(0, hasta - desde - 60)

  x: desde + Math.min(pos, tramo)
  width: 60
  visible: activo && cabe

  Timer {
    interval: 90
    repeat: true
    running: paseo.visible && paseo.andando && barra.animar
    onTriggered: {
      var n = paseo.pos + 2 * paseo.sentido
      if (n >= paseo.tramo) { n = paseo.tramo; paseo.sentido = -1 }
      if (n <= 0) { n = 0; paseo.sentido = 1 }
      paseo.pos = n
    }
  }

  Loader {
    anchors.bottom: parent.bottom
    width: 60; height: 50
    active: paseo.activo
    source: active ? barra.personaje : ""
    anchors.bottomMargin: barra.tema.compacto ? -3 : 0
    onLoaded: {
      item.seasonHat = Qt.binding(function() { return barra.ropa.gorro })
      item.seasonOutfit = Qt.binding(function() { return barra.ropa.traje })
      item.mode = Qt.binding(function() { return paseo.andando ? "explore" : paseo.modo })
      item.hat = Qt.binding(function() { return paseo.andando ? "" : item.hatFor(item.mode) })
      item.visible = Qt.binding(function() { return barra.animar })
    }
  }
  ZonaClaude { anchors.fill: parent }
}
