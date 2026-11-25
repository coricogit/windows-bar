import QtQuick

// La barra de una pantalla, en cualquiera de sus cuatro lados. Todo lo que
// cambia entre temas sale de `barra.tema`. En vertical, "izquierda" es arriba y
// "derecha" es abajo.
Item {
  id: root
  readonly property var t: barra.tema
  readonly property var c: t.colores
  readonly property bool v: t.vertical
  readonly property bool islas: t.forma === "islas"
  readonly property bool estrecha: !v && width < 1500
  readonly property real altoUtil: t.alto - 2 * (islas ? 0 : t.borde)
  readonly property real largo: v ? height : width

  // ---------- Fondo ----------
  Rectangle {
    id: cuerpo
    x: root.v && root.t.lado === "derecha" ? root.width - width - root.t.margen : root.t.margen
    y: !root.v && root.t.lado === "abajo" ? root.height - height - root.t.margen : root.t.margen
    width: root.v ? root.t.alto : root.width - 2 * root.t.margen
    height: root.v ? root.height - 2 * root.t.margen : root.t.alto
    radius: root.t.radio
    clip: !root.islas      // la ciudad de Tokyo Night llega hasta el borde
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

  // Los huecos sin nada: clic derecho, menú; arrastrar, mover la barra de lado.
  MouseArea {
    anchors.fill: parent
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    property point inicio
    property bool lejos: false
    cursorShape: lejos ? Qt.SizeAllCursor : Qt.ArrowCursor
    onPressed: function(e) { inicio = Qt.point(e.x, e.y); lejos = false }
    onPositionChanged: function(e) {
      if (pressedButtons & Qt.LeftButton) lejos = Math.max(Math.abs(e.x - inicio.x), Math.abs(e.y - inicio.y)) > 80
    }
    onReleased: function(e) { if (lejos && e.button === Qt.LeftButton) barra.mover_al_raton(); lejos = false }
    onCanceled: lejos = false
    onClicked: function(e) { if (e.button === Qt.RightButton) barra.menu() }
    onWheel: function(e) { barra.girar_tema(e.angleDelta.y > 0 ? -1 : 1) }
  }

  // ---------- Módulos ----------
  function visibles(grupos) {
    var out = []
    for (var i = 0; i < grupos.length; i++) {
      var g = []
      for (var j = 0; j < grupos[i].length; j++) {
        var m = grupos[i][j]
        if (m === "claudito" && (!barra.personaje || (t.paseo && !t.vertical))) continue
        if (m === "temas" && !barra.pincel) continue
        if (estrecha && (m === "sistema" || m === "musica" || m === "titulo")) continue
        if (t.vertical && m === "titulo") continue
        if (!esPrimaria && m === "bandeja") continue
        g.push(m)
      }
      if (g.length) out.push(g)
    }
    return out
  }

  // Formato "una isla": todo va en la zona del centro, sobre esta pieza.
  Rectangle {
    visible: root.t.unica
    readonly property real aire: 10 + root.t.aire
    x: root.v ? cuerpo.x : centro.x - aire
    y: root.v ? centro.y - aire : cuerpo.y
    width: root.v ? cuerpo.width : centro.width + 2 * aire
    height: root.v ? centro.height + 2 * aire : cuerpo.height
    radius: Math.min(root.t.radio, root.t.alto / 2)
    color: root.c.isla
    border.width: root.t.borde
    border.color: root.c.borde
    Behavior on color { ColorAnimation { duration: 350 } }
  }

  Zona {
    id: izquierda
    tema: root.t
    alto: root.altoUtil
    limite: root.largo * (root.estrecha ? 0.5 : 0.4)
    grupos: root.visibles(root.t.modulos.izquierda)
    x: root.v ? cuerpo.x + (cuerpo.width - width) / 2 : cuerpo.x + root.t.relleno
    y: root.v ? cuerpo.y + root.t.relleno : cuerpo.y + (cuerpo.height - height) / 2
  }
  Zona {
    id: derecha
    tema: root.t
    alto: root.altoUtil
    limite: root.largo * (root.estrecha ? 0.5 : 0.4)
    grupos: root.visibles(root.t.modulos.derecha)
    x: root.v ? cuerpo.x + (cuerpo.width - width) / 2 : cuerpo.x + cuerpo.width - width - root.t.relleno
    y: root.v ? cuerpo.y + cuerpo.height - height - root.t.relleno : cuerpo.y + (cuerpo.height - height) / 2
  }
  Zona {
    id: centro
    tema: root.t
    alto: root.altoUtil
    readonly property real antes: root.v ? izquierda.y + izquierda.height : izquierda.x + izquierda.width
    readonly property real despues: root.v ? derecha.y : derecha.x
    readonly property real mio: root.v ? height : width
    readonly property real hueco: despues - antes - 24
    // Con las ventanas aquí, se encogen antes que desaparecer.
    limite: root.t.unica ? Math.max(80, root.largo - otros - 80) : root.t.centrado ? Math.max(120, Math.min(root.largo * 0.5, hueco - 90)) : root.largo * 0.4
    grupos: root.visibles(root.t.modulos.centro)
    // En el medio, salvo que tape a los lados.
    readonly property real sitio: Math.max(antes + 12, Math.min((root.largo - mio) / 2, despues - mio - 12))
    x: root.v ? cuerpo.x + (cuerpo.width - width) / 2 : sitio
    y: root.v ? sitio : cuerpo.y + (cuerpo.height - height) / 2
    visible: root.t.centrado || hueco > mio
  }

  // ---------- Claudito de paseo (tema Píxel) ----------
  Paseo {
    activo: root.t.paseo && !root.v && barra.personaje !== ""
    // Con los iconos en el centro, pasea por la izquierda.
    desde: (root.t.centrado ? izquierda.x + izquierda.width
            : Math.max(izquierda.x + izquierda.width, centro.visible && centro.width > 0 ? centro.x + centro.width : 0)) + 10
    hasta: (root.t.centrado ? centro.x : derecha.x) - 10
    y: cuerpo.y + cuerpo.height - height
    height: 48
  }
}
