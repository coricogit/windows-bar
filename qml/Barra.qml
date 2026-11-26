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
  readonly property real altoUtil: t.alto - 2 * (islas ? 0 : t.borde)
  readonly property real largo: v ? height : width

  // ---------- Módulos ----------
  function visibles(grupos) {
    var out = []
    for (var i = 0; i < grupos.length; i++) {
      var g = []
      for (var j = 0; j < grupos[i].length; j++) {
        var m = grupos[i][j]
        if (m === "claudito" && (!barra.personaje || (t.paseo && !t.vertical))) continue
        if (m === "temas" && !barra.pincel) continue
        if (m === "widgets" && !barra.widgets) continue
        if (t.vertical && m === "titulo") continue
        if (!esPrimaria && m === "bandeja") continue
        g.push(m)
      }
      if (g.length) out.push(g)
    }
    return out
  }

  // Los iconos mandan: van en el centro exacto o al principio, y lo demás se
  // reparte lo que queda a sus lados (Zona esconde lo que no quepa).
  readonly property bool unica: t.unica
  readonly property real aire: 10 + t.aire
  readonly property real margen: t.relleno + (unica ? aire : 0)
  readonly property real sep: unica ? t.separacion : 12
  readonly property real total: largo - 2 * margen      // sitio para todo

  // En una isla con los iconos al principio va todo seguido; con ellos en el
  // centro, la isla es simétrica y cada lado se pega a su borde.
  readonly property real seguido: izquierda.mio + (centro.mio > 0 ? sep + centro.mio : 0) + (derecha.mio > 0 ? sep + derecha.mio : 0)
  readonly property real mitad: centro.mio / 2 + sep + Math.max(izquierda.mio, derecha.mio)
  readonly property real anchoIsla: t.centrado ? 2 * mitad : seguido
  readonly property real inicio: (largo - anchoIsla) / 2
  readonly property real pIzq: unica ? inicio : (v ? cuerpo.y : cuerpo.x) + t.relleno
  readonly property real pDer: !unica ? (v ? cuerpo.y + cuerpo.height : cuerpo.x + cuerpo.width) - derecha.mio - t.relleno
                               : inicio + anchoIsla - derecha.mio
  readonly property real pCen: {
    if (t.centrado) return (largo - centro.mio) / 2
    var antes = pIzq + izquierda.mio + sep
    return unica ? antes : Math.max(antes, Math.min((largo - centro.mio) / 2, pDer - centro.mio - sep))
  }

  // ---------- Escondida ----------
  // Todo se desliza hacia el borde; queda una rayita para saber dónde está.
  // Lo que sale de la ventana no se ve y, transparente, deja pasar los clics.
  readonly property bool escondida: typeof oculta !== "undefined" && oculta
  property real fuera: escondida ? (v ? width : height) : 0
  Behavior on fuera { NumberAnimation { duration: 190; easing.type: Easing.OutCubic } }
  Rectangle {
    id: raya
    opacity: root.escondida ? 0.75 : 0
    Behavior on opacity { NumberAnimation { duration: 190 } }
    visible: opacity > 0
    color: root.c.acento
    radius: 1.5
    width: root.v ? 3 : Math.min(240, root.width * 0.18)
    height: root.v ? Math.min(240, root.height * 0.18) : 3
    x: root.v ? (root.t.lado === "izquierda" ? 0 : root.width - width) : (root.width - width) / 2
    y: root.v ? (root.height - height) / 2 : (root.t.lado === "arriba" ? 0 : root.height - height)
  }

  Item {
  id: contenido
  anchors.fill: parent
  visible: root.fuera < (root.v ? root.width : root.height)
  transform: Translate {
    x: !root.v ? 0 : root.t.lado === "izquierda" ? -root.fuera : root.fuera
    y: root.v ? 0 : root.t.lado === "arriba" ? -root.fuera : root.fuera
  }

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
      source: root.t.dentro ? "" : root.t.fondoUrl
      // Flotante: el paisaje no asoma por las esquinas redondeadas.
      onLoaded: item.radio = Qt.binding(function() { return root.islas ? 0 : Math.max(0, root.t.radio - root.t.borde) })
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

  // ---------- Esquinas: una pieza por zona; las de los lados, en las esquinas ----------
  component Pieza: Rectangle {
    id: pieza
    property Item zona
    property string cual          // "ini", "cen" o "fin"
    readonly property real aire: root.aire
    readonly property string ini: root.v ? "arriba" : "izquierda"
    readonly property string fin: root.v ? "abajo" : "derecha"
    // Sin redondear lo que toca el borde de la pantalla.
    function recta(a, b) {
      var l = [a, b]
      return l.indexOf(root.t.lado) >= 0 || (cual === "ini" && l.indexOf(ini) >= 0) || (cual === "fin" && l.indexOf(fin) >= 0)
    }
    readonly property real r: Math.min(root.t.radio, root.t.alto / 2)
    visible: root.t.esquinas && zona.mio > 0
    readonly property real desde: cual === "ini" ? 0 : (root.v ? zona.y : zona.x) - aire
    readonly property real hasta: cual === "fin" ? root.largo : (root.v ? zona.y + zona.height : zona.x + zona.width) + aire
    x: root.v ? cuerpo.x : desde
    y: root.v ? desde : cuerpo.y
    width: root.v ? cuerpo.width : hasta - desde
    height: root.v ? hasta - desde : cuerpo.height
    color: root.c.isla
    border.width: root.t.borde
    border.color: root.c.borde
    topLeftRadius: recta("arriba", "izquierda") ? 0 : r
    topRightRadius: recta("arriba", "derecha") ? 0 : r
    bottomLeftRadius: recta("abajo", "izquierda") ? 0 : r
    bottomRightRadius: recta("abajo", "derecha") ? 0 : r
    Behavior on color { ColorAnimation { duration: 350 } }
    Loader {
      anchors { fill: parent; margins: root.t.borde }
      active: pieza.visible && root.t.fondoUrl !== "" && pieza.width > 20
      source: active ? root.t.fondoUrl : ""
      onLoaded: {
        item.radio = Qt.binding(function() { return Math.max(0, pieza.r - root.t.borde) })
        item.desde = Qt.binding(function() { return pieza.desde })
        item.total = Qt.binding(function() { return root.largo })
      }
    }
  }
  Pieza { zona: izquierda; cual: "ini" }
  Pieza { zona: centro; cual: "cen" }
  Pieza { zona: derecha; cual: "fin" }

  Rectangle {          // el fondo de "una isla"
    id: isla
    visible: root.unica
    // Pegada al borde: sin redondear por ese lado.
    readonly property real r: Math.min(root.t.radio, root.t.alto / 2)
    readonly property string pegado: root.t.pegada ? root.t.lado : ""
    topLeftRadius: pegado === "arriba" || pegado === "izquierda" ? 0 : r
    topRightRadius: pegado === "arriba" || pegado === "derecha" ? 0 : r
    bottomLeftRadius: pegado === "abajo" || pegado === "izquierda" ? 0 : r
    bottomRightRadius: pegado === "abajo" || pegado === "derecha" ? 0 : r
    x: root.v ? cuerpo.x : root.inicio - root.aire
    y: root.v ? root.inicio - root.aire : cuerpo.y
    width: root.v ? cuerpo.width : root.anchoIsla + 2 * root.aire
    height: root.v ? root.anchoIsla + 2 * root.aire : cuerpo.height
    radius: Math.min(root.t.radio, root.t.alto / 2)
    color: root.c.isla
    border.width: root.t.borde
    border.color: root.c.borde
    Behavior on color { ColorAnimation { duration: 350 } }

    // El degradado, por dentro: en el mismo rectángulo deja huecos junto al borde.
    Rectangle {
      visible: root.t.fondoUrl !== "" && root.t.dentro
      anchors { fill: parent; margins: root.t.borde }
      radius: Math.max(0, parent.radius - root.t.borde)
      topLeftRadius: Math.max(0, isla.topLeftRadius - root.t.borde)
      topRightRadius: Math.max(0, isla.topRightRadius - root.t.borde)
      bottomLeftRadius: Math.max(0, isla.bottomLeftRadius - root.t.borde)
      bottomRightRadius: Math.max(0, isla.bottomRightRadius - root.t.borde)
      gradient: Gradient {
        GradientStop { position: 0; color: root.c.fondo2 }
        GradientStop { position: 1; color: root.c.fondo }
      }
    }
    // El paisaje del tema, dentro de la pieza.
    Loader {
      anchors { fill: parent; margins: root.t.borde }
      active: root.unica && root.t.dentro && root.t.fondoUrl !== ""
      source: active ? root.t.fondoUrl : ""
      onLoaded: {
        item.radio = Qt.binding(function() { return Math.max(0, Math.min(root.t.radio, root.t.alto / 2) - root.t.borde) })
        item.desde = Qt.binding(function() { return 0 })
        item.total = Qt.binding(function() { return 0 })
      }
    }
  }

  Zona {
    id: izquierda
    tema: root.t
    alto: root.altoUtil
    // Con las ventanas aquí, todas las que dejen sitio a lo imprescindible.
    limite: Math.max(80, root.total - derecha.esencial - otros - 2 * root.sep)
    hueco: root.t.centrado ? (root.total - centro.mio) / 2 - root.sep : 100000
    total: root.largo
    grupos: root.visibles(root.t.modulos.izquierda)
    x: root.v ? cuerpo.x + (cuerpo.width - width) / 2 : root.pIzq
    y: root.v ? root.pIzq : cuerpo.y + (cuerpo.height - height) / 2
  }
  Zona {
    id: derecha
    tema: root.t
    alto: root.altoUtil
    hueco: root.t.centrado ? (root.total - centro.mio) / 2 - root.sep : root.total - izquierda.mio - root.sep
    total: root.largo
    grupos: root.visibles(root.t.modulos.derecha)
    x: root.v ? cuerpo.x + (cuerpo.width - width) / 2 : root.pDer
    y: root.v ? root.pDer : cuerpo.y + (cuerpo.height - height) / 2
  }
  Zona {
    id: centro
    tema: root.t
    alto: root.altoUtil
    limite: Math.max(80, root.total - 2 * (Math.max(izquierda.esencial, derecha.esencial) + root.sep) - otros)
    hueco: root.t.centrado ? 100000 : root.total - izquierda.mio - derecha.mio - 2 * root.sep
    total: root.largo
    grupos: root.visibles(root.t.modulos.centro)
    x: root.v ? cuerpo.x + (cuerpo.width - width) / 2 : root.pCen
    y: root.v ? root.pCen : cuerpo.y + (cuerpo.height - height) / 2
  }

  // ---------- Claudito de paseo (tema Píxel) ----------
  Paseo {
    activo: root.t.paseo && !root.v && barra.personaje !== ""
    // Con los iconos en el centro, pasea por la izquierda.
    desde: (root.t.centrado ? izquierda.x + izquierda.width
            : Math.max(izquierda.x + izquierda.width, centro.width > 0 ? centro.x + centro.width : 0)) + 10
    hasta: (root.t.centrado ? centro.x : derecha.x) - 10
    y: cuerpo.y + cuerpo.height - height
    height: 48
  }
  }
}
