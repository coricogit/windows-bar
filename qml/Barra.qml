import QtQuick

// La barra de una pantalla. Todo lo que cambia entre temas sale de `barra.tema`.
Item {
  id: root
  readonly property var t: barra.tema
  readonly property var c: t.colores
  readonly property bool islas: t.forma === "islas"
  readonly property bool estrecha: width < 1500
  readonly property real altoUtil: t.alto - 2 * (islas ? 0 : t.borde)

  // ---------- Fondo ----------
  Rectangle {
    id: cuerpo
    anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: root.t.margen }
    height: root.t.alto
    radius: root.t.radio
    clip: true
    border.width: root.islas ? 0 : root.t.borde
    border.color: root.c.borde
    gradient: Gradient {
      GradientStop { position: 0; color: root.islas ? "transparent" : root.c.fondo2
        Behavior on color { ColorAnimation { duration: 350 } } }
      GradientStop { position: 1; color: root.islas ? "transparent" : root.c.fondo
        Behavior on color { ColorAnimation { duration: 350 } } }
    }
    Loader {
      id: adorno
      anchors.fill: parent
      source: root.t.fondoUrl
      opacity: status === Loader.Ready ? 1 : 0
      Behavior on opacity { NumberAnimation { duration: 400 } }
    }
  }

  // Los huecos sin nada: menú de temas con el botón derecho.
  MouseArea {
    anchors.fill: parent
    acceptedButtons: Qt.RightButton
    onClicked: barra.menu()
    onWheel: function(e) { barra.girar_tema(e.angleDelta.y > 0 ? -1 : 1) }
  }

  // ---------- Módulos ----------
  function visibles(grupos) {
    var out = []
    for (var i = 0; i < grupos.length; i++) {
      var g = []
      for (var j = 0; j < grupos[i].length; j++) {
        var m = grupos[i][j]
        if (m === "claudito" && (!barra.personaje || t.paseo)) continue
        if (m === "temas" && !barra.pincel) continue
        if (estrecha && (m === "sistema" || m === "musica" || m === "titulo")) continue
        if (!esPrimaria && m === "bandeja") continue
        g.push(m)
      }
      if (g.length) out.push(g)
    }
    return out
  }

  Zona {
    id: izquierda
    tema: root.t
    alto: root.altoUtil
    limite: root.width * (root.estrecha ? 0.5 : 0.4)
    grupos: root.visibles(root.t.modulos.izquierda)
    anchors { left: cuerpo.left; leftMargin: root.t.relleno; verticalCenter: cuerpo.verticalCenter }
  }
  Zona {
    id: derecha
    tema: root.t
    alto: root.altoUtil
    limite: root.width * (root.estrecha ? 0.5 : 0.4)
    grupos: root.visibles(root.t.modulos.derecha)
    anchors { right: cuerpo.right; rightMargin: root.t.relleno; verticalCenter: cuerpo.verticalCenter }
  }
  Zona {
    id: centro
    tema: root.t
    alto: root.altoUtil
    readonly property real hueco: derecha.x - (izquierda.x + izquierda.width) - 24
    // Con las ventanas aquí, se encogen antes que desaparecer.
    limite: root.t.centrado ? Math.max(120, Math.min(root.width * 0.5, hueco - 90)) : root.width * 0.4
    grupos: root.visibles(root.t.modulos.centro)
    anchors.verticalCenter: cuerpo.verticalCenter
    // En el medio, salvo que tape a los lados.
    x: Math.max(izquierda.x + izquierda.width + 12,
                Math.min((root.width - width) / 2, derecha.x - width - 12))
    visible: root.t.centrado || hueco > width
  }

  // ---------- Claudito de paseo (tema Píxel) ----------
  Paseo {
    activo: root.t.paseo && barra.personaje !== ""
    desde: Math.max(izquierda.x + izquierda.width, centro.visible && centro.width > 0 ? centro.x + centro.width : 0) + 10
    hasta: derecha.x - 10
    anchors.bottom: cuerpo.bottom
    height: 48
  }
}
