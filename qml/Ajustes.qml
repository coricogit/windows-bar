import QtQuick

// El menú de ajustes (barra/menu.py): la barra en grande arriba, que prueba cada opción
// al pasar el ratón o el teclado, las categorías y sus opciones con imagen.
// Teclado: Tab y Mayús+Tab entre piezas, flechas dentro, Intro o Espacio para elegir,
// Esc para cerrar; Ctrl+Tab cambia de categoría.
FocusScope {
  id: raiz
  readonly property var d: menu.datos
  // Hasta que llegan los datos, unos colores de reserva (que no falte ninguno).
  readonly property var c: d.colores || ({ fondo: "#202020", tarjeta: "#2B2B2B", tarjetaEncima: "#383838", hueco: "#181818",
                                           acentoSuave: "#24384A", texto: "#FFFFFF", tenue: "#B0B0B0", acento: "#4CC2FF",
                                           sobreAcento: "#000000", foco: "#FFFFFF", linea: "#5A5A5A", fuente: "Segoe UI" })
  readonly property real esc: d.escala || 1
  property int cat: 0
  property var nuevas: ({})             // miniaturas que llegan después: id -> url
  property string probando: ""
  property string focoId: ""            // la opción con el foco, para devolvérselo al rehacer el menú
  property bool restaurando: false
  width: Math.round(820 * esc)
  height: Math.min(d.maxAlto || 9999, Math.round(640 * esc))
  focus: true

  Accessible.role: Accessible.Dialog
  Accessible.name: "Ajustes de la barra"

  Connections {
    target: menu
    function onMiniaturaCambio(ident, url) { var n = Object.assign({}, raiz.nuevas); n[ident] = url; raiz.nuevas = n }
    function onDatosCambio() {
      raiz.cat = Math.min(raiz.cat, Math.max(0, (raiz.d.categorias || []).length - 1))
      raiz.restaurando = true
      Qt.callLater(function() { raiz.restaurando = false })
    }
  }
  Keys.onEscapePressed: menu.cerrar()
  Keys.onPressed: function(e) {
    if (e.key === Qt.Key_Tab && (e.modifiers & Qt.ControlModifier)) {
      raiz.elegirCategoria((raiz.cat + ((e.modifiers & Qt.ShiftModifier) ? -1 : 1) + d.categorias.length) % d.categorias.length)
      e.accepted = true
    }
  }
  function elegirCategoria(i) {
    // Si la pestaña que se deja tiene el foco, pasa antes a la nueva (si no, Qt protesta).
    var antes = repCategorias.itemAt(cat)
    if (antes && antes.activeFocus && repCategorias.itemAt(i)) repCategorias.itemAt(i).forceActiveFocus(Qt.TabFocusReason)
    cat = i; lista.contentY = 0; menu.dejar(); menu.categoria(i); probando = ""
  }

  Rectangle {
    anchors.fill: parent
    radius: d.radio === undefined ? 8 : d.radio
    color: raiz.c.fondo || "#202020"
    border.width: 1
    border.color: raiz.c.linea || "#3A3A3A"
  }

  // ---------- vista previa ----------
  Rectangle {
    id: previa
    x: Math.round(14 * esc); y: Math.round(14 * esc)
    width: parent.width - 2 * x; height: Math.round(132 * esc)
    radius: Math.round(8 * esc)
    clip: true
    gradient: Gradient { GradientStop { position: 0; color: "#2E4A66" } GradientStop { position: 0.6; color: "#5E4A72" } GradientStop { position: 1; color: "#8E5E6E" } }
    Accessible.role: Accessible.Graphic
    Accessible.name: raiz.probando !== "" ? "Vista previa probando " + raiz.probando : "Vista previa de la barra"
    Text {
      x: Math.round(12 * esc); y: Math.round(10 * esc)
      text: "Vista previa"; color: "#FFFFFF"
      font.family: raiz.c.fuente || "Segoe UI"; font.pixelSize: Math.round(12 * esc)
    }
    Rectangle {
      visible: raiz.probando !== ""
      anchors { right: parent.right; top: parent.top; margins: Math.round(8 * esc) }
      width: prueba.implicitWidth + Math.round(20 * esc); height: Math.round(24 * esc); radius: height / 2
      color: "#B0000000"
      Text { id: prueba; anchors.centerIn: parent; text: "Probando: " + raiz.probando; color: "#FFFFFF"
             font.family: raiz.c.fuente || "Segoe UI"; font.pixelSize: Math.round(11 * esc) }
    }
    Image {
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.bottom: parent.bottom; anchors.bottomMargin: Math.round(12 * esc)
      source: menu.previa
      width: Math.min(parent.width - Math.round(24 * esc), sourceSize.width * (parent.height - 44 * raiz.esc) / Math.max(1, sourceSize.height))
      height: Math.min(parent.height - 44 * raiz.esc, sourceSize.height * width / Math.max(1, sourceSize.width))
      fillMode: Image.PreserveAspectFit
      smooth: true; mipmap: true
      cache: false
    }
  }

  // ---------- categorías ----------
  Row {
    id: categorias
    x: previa.x; y: previa.y + previa.height + Math.round(12 * esc)
    spacing: Math.round(6 * esc)
    Repeater {
      id: repCategorias
      model: d.categorias || []
      AjustesPieza {
        forma: "categoria"
        onFlecha: function(paso) {
          var n = (d.categorias || []).length
          var nueva = (raiz.cat + paso + n) % n
          repCategorias.itemAt(nueva).forceActiveFocus(Qt.TabFocusReason)   // primero el foco, luego la categoría
          raiz.elegirCategoria(nueva)
        }
        o: ({ texto: modelData.titulo, glifo: modelData.glifo, elegido: index === raiz.cat })
        c: raiz.c; esc: raiz.esc
        width: Math.round((previa.width - 7 * categorias.spacing) / Math.max(1, (d.categorias || []).length))
        focus: index === raiz.cat
        onActivar: raiz.elegirCategoria(index)
      }
    }
  }

  // ---------- opciones de la categoría ----------
  Flickable {
    id: lista
    x: previa.x
    y: categorias.y + categorias.height + Math.round(10 * esc)
    width: previa.width
    height: rapidos.y - y - Math.round(10 * esc)
    contentHeight: columna.height
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    // Que la pieza con el foco se vea siempre (WCAG 2.4.7).
    function mostrar(it) {
      var p = it.mapToItem(columna, 0, 0)
      if (p.y < contentY) contentY = Math.max(0, p.y - 8)
      else if (p.y + it.height > contentY + height) contentY = Math.min(contentHeight - height, p.y + it.height - height + 8)
    }
    Column {
      id: columna
      width: lista.width
      spacing: Math.round(14 * esc)
      Repeater {
        model: (d.categorias && d.categorias[raiz.cat]) ? d.categorias[raiz.cat].secciones : []
        Column {
          id: sec
          readonly property var s: modelData
          width: columna.width
          spacing: Math.round(8 * esc)
          Text {
            text: sec.s.titulo
            color: raiz.c.texto || "#FFFFFF"
            font.family: raiz.c.fuente || "Segoe UI"; font.pixelSize: Math.round(15 * esc); font.bold: true
            Accessible.role: Accessible.Heading
            Accessible.name: text
          }
          Text {
            visible: !!sec.s.ayuda
            width: parent.width
            wrapMode: Text.WordWrap
            text: sec.s.ayuda || ""
            color: raiz.c.tenue || "#A0A0A0"
            font.family: raiz.c.fuente || "Segoe UI"; font.pixelSize: Math.round(12 * esc)
          }
          Flow {
            width: parent.width
            spacing: Math.round(8 * esc)
            Repeater {
              model: sec.s.opciones
              AjustesPieza {
                o: modelData
                forma: ({ imagenes: "baldosa", temas: "baldosa", posicion: "baldosa", colores: "baldosa",
                          interruptores: "interruptor", botones: "boton" })[sec.s.tipo] || "opcion"
                seccion: sec.s.titulo
                c: raiz.c; esc: raiz.esc
                imagen: raiz.nuevas[modelData.id] || modelData.imagen || ""
                onActivar: menu.pulsar(modelData.id)
                onProbar: { raiz.probando = modelData.texto; menu.probar(modelData.id) }
                onDejar: { raiz.probando = ""; menu.dejar() }
                quiereFoco: raiz.restaurando && modelData.id === raiz.focoId
                onActiveFocusChanged: if (activeFocus) { lista.mostrar(this); raiz.focoId = modelData.id }
              }
            }
          }
        }
      }
    }
  }
  // Una pista de que hay más abajo.
  Rectangle {
    visible: lista.contentHeight > lista.height && !lista.atYEnd
    x: lista.x; width: lista.width; height: Math.round(18 * esc)
    y: lista.y + lista.height - height
    gradient: Gradient { GradientStop { position: 0; color: "transparent" } GradientStop { position: 1; color: raiz.c.fondo || "#202020" } }
  }

  // ---------- interruptores rápidos ----------
  Row {
    id: rapidos
    x: previa.x
    y: raiz.height - height - Math.round(14 * esc)
    spacing: Math.round(8 * esc)
    Repeater {
      model: d.rapidos || []
      AjustesPieza {
        forma: "interruptor"
        o: modelData
        quiereFoco: raiz.restaurando && modelData.id === raiz.focoId
        onActiveFocusChanged: if (activeFocus) raiz.focoId = modelData.id
        c: raiz.c; esc: raiz.esc
        onActivar: menu.pulsar(modelData.id)
      }
    }
  }
}
