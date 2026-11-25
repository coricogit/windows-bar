import QtQuick

// Un módulo de la barra, por su nombre.
Loader {
  id: mod
  property string nombre
  property var tema
  property real alto: 40
  property real limite: 600
  readonly property var c: tema.colores
  readonly property bool v: tema.vertical
  // Sin tamaño propio: cada módulo pone el suyo. Si el Loader lo impusiera,
  // rompería sus enlaces y al girar la barra se quedaría con el anterior.
  sourceComponent: ({ inicio: inicio, tareas: tareasC, titulo: titulo, musica: musicaC, sistema: sistemaC,
                      bandeja: bandejaC, volumen: volumen, reloj: reloj, temas: temasC, claudito: clauditoC })[nombre]

  Component {
    id: inicio
    Boton {
      id: botonInicio
      alto: mod.alto
      colores: mod.c
      ancho: mod.tema.compacto ? 30 : 38
      ayuda: "Inicio · Rueda: cambiar de tema (" + mod.tema.nombre + ")"
      onPulsado: function(b) { barra.accion(b === Qt.RightButton ? "menu_inicio" : "inicio") }
      onRueda: function(p) { barra.girar_tema(-p) }
      Logo { anchors.centerIn: parent; tema: mod.tema; encima: botonInicio.encima }
    }
  }

  Component {
    id: tareasC
    ListView {
      orientation: mod.v ? ListView.Vertical : ListView.Horizontal
      width: mod.v ? mod.alto : Math.min(contentWidth, mod.limite)
      height: mod.v ? Math.min(contentHeight, mod.limite) : mod.alto
      clip: true
      interactive: mod.v ? contentHeight > height : contentWidth > width
      spacing: 2
      model: tareas
      // La gota: sus dos bordes van a distinta velocidad, así se estira al moverse.
      property Item activaItem: null
      Item {
        id: gota
        parent: contentItem
        z: -1
        visible: mod.tema.indicador === "gota" && !mod.v && !!activaItem
        property real izq: activaItem ? activaItem.x + 2 : 0
        property real der: activaItem ? activaItem.x + activaItem.width - 2 : 0
        Behavior on izq { SpringAnimation { spring: 3.6; damping: 0.36; epsilon: 0.3 } }
        Behavior on der { SpringAnimation { spring: 2.2; damping: 0.30; epsilon: 0.3 } }
        x: Math.min(izq, der)
        width: Math.max(12, Math.abs(der - izq))
        y: 4
        height: mod.alto - 8
        Rectangle {
          anchors.fill: parent
          radius: height / 2
          border.width: 1
          border.color: "#99FFFFFF"
          gradient: Gradient {
            GradientStop { position: 0; color: "#73FFFFFF" }
            GradientStop { position: 0.45; color: "#24FFFFFF" }
            GradientStop { position: 1; color: "#4DFFFFFF" }
          }
        }
      }
      add: Transition { NumberAnimation { property: "scale"; from: 0.4; to: 1; duration: 160; easing.type: Easing.OutBack } }
      displaced: Transition { NumberAnimation { properties: "x,y"; duration: 160; easing.type: Easing.OutCubic } }
      delegate: Tarea {
        tema: mod.tema
        alto: mod.alto
        clave: model.key
        titulo: model.titulo || ""
        icono: model.icono || ""
        activa: !!model.activa
        abierta: !!model.abierta
        minimizada: !!model.minimizada
        cuenta: model.cuenta || 0
        indice: index
        lista: ListView.view
        onActivaChanged: marcar()
        Component.onCompleted: marcar()
        Component.onDestruction: if (ListView.view && ListView.view.activaItem === this) ListView.view.activaItem = null
        function marcar() {
          if (activa) ListView.view.activaItem = this
          else if (ListView.view && ListView.view.activaItem === this) ListView.view.activaItem = null
        }
      }
    }
  }

  Component {
    id: titulo
    Texto {
      width: Math.min(implicitWidth, mod.tema.centrado ? 300 : 420)
      height: mod.alto
      elide: Text.ElideRight
      text: barra.titulo
      color: mod.c.texto
    }
  }

  Component {
    id: musicaC
    Row {
      height: mod.v ? (hay ? implicitHeight : 0) : mod.alto
      // No `visible`: dentro de un grupo oculto siempre sería falso.
      readonly property bool hay: barra.cancion.titulo !== ""
      width: mod.v ? mod.alto : hay ? implicitWidth : 0
      spacing: 0
      Boton { visible: !mod.v; alto: mod.alto; colores: mod.c; texto: "\uE892"; fuente: "Segoe Fluent Icons"; tam: 13; ayuda: "Anterior"; ancho: 28; colorTexto: mod.c.tenue; onPulsado: barra.accion("anterior") }
      Boton {
        alto: mod.alto
        colores: mod.c
        texto: barra.cancion.sonando ? "\uE769" : "\uE768"; fuente: "Segoe Fluent Icons"; tam: 13; ancho: 28; colorTexto: mod.c.acento
        ayuda: mod.v ? barra.cancion.titulo + (barra.cancion.artista ? " — " + barra.cancion.artista : "") : barra.cancion.sonando ? "Pausar" : "Reproducir"
        onRueda: function(p) { barra.accion(p > 0 ? "anterior" : "siguiente") }
        onPulsado: barra.accion("pausa")
      }
      Boton { visible: !mod.v; alto: mod.alto; colores: mod.c; texto: "\uE893"; fuente: "Segoe Fluent Icons"; tam: 13; ayuda: "Siguiente"; ancho: 28; colorTexto: mod.c.tenue; onPulsado: barra.accion("siguiente") }
      Texto {
        visible: !mod.v
        height: mod.alto
        width: Math.min(implicitWidth, mod.tema.centrado ? 190 : 300)
        elide: Text.ElideRight
        leftPadding: 4
        rightPadding: 6
        color: mod.c.texto
        text: barra.cancion.titulo + (barra.cancion.artista ? " — " + barra.cancion.artista : "")
      }
    }
  }

  Component {
    id: sistemaC
    Grid {
      columns: mod.v ? 1 : 3
      spacing: mod.v ? 6 : mod.tema.compacto ? 7 : 9
      leftPadding: mod.v ? 0 : 4
      rightPadding: mod.v ? 0 : 4
      topPadding: mod.v ? 4 : 0
      bottomPadding: mod.v ? 4 : 0
      Repeater {
        model: [["CPU", "cpu"], ["RAM", "ram"], ["GPU", "gpu"]]
        Medidor {
          tema: mod.tema
          alto: mod.alto
          nombre: modelData[0]
          orden: index
          valor: barra.datos[modelData[1]]
          historia: barra.datos.historia ? barra.datos.historia[modelData[1]] : []
          visible: valor >= 0
        }
      }
      Item {
        parent: mod
        anchors.fill: parent
        Aviso {
          texto: "CPU " + barra.datos.cpu + " %  ·  RAM " + barra.datos.ram + " %" + (barra.datos.gpu >= 0 ? "  ·  GPU " + barra.datos.gpu + " %" : "")
          fuente: zm
        }
        MouseArea { id: zm; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
      }
    }
  }

  Component {
    id: bandejaC
    Grid {
      id: rejilla
      readonly property real celda: mod.tema.compacto ? 24 : 28
      columns: mod.v ? Math.max(1, Math.floor(mod.alto / celda)) : 99
      Rectangle {      // en temas claros, para que se vean los iconos blancos
        z: -1
        parent: mod
        visible: mod.item && mod.item.width > 0
        anchors { fill: parent; topMargin: mod.v ? -2 : 5; bottomMargin: mod.v ? -2 : 5; leftMargin: mod.v ? 1 : 0; rightMargin: mod.v ? 1 : 0 }
        radius: mod.v ? 12 : height / 2
        color: mod.c.fondoBandeja
      }
      Repeater {
        model: bandeja
        Item {
          width: rejilla.celda
          height: mod.v ? width : mod.alto
          Rectangle {
            anchors.centerIn: parent
            width: parent.width; height: width
            radius: Math.min(mod.tema.radio, 6)
            color: zona.containsMouse ? mod.c.encima : "transparent"
          }
          Image {
            anchors.centerIn: parent
            width: 16; height: 16
            sourceSize: Qt.size(32, 32)
            source: model.icono
            smooth: !mod.tema.pixelado
            mipmap: !mod.tema.pixelado
            cache: false
          }
          Aviso { texto: model.tip; fuente: zona }
          MouseArea {
            id: zona
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onClicked: function(e) { barra.pulsar_bandeja(model.key, e.button === Qt.RightButton) }
          }
        }
      }
    }
  }

  Component {
    id: volumen
    Boton {
      alto: mod.alto
      colores: mod.c
      texto: (barra.datos.silencio ? "✕" : "♪") + (mod.v ? "\n" : " ") + barra.datos.volumen + "%"
      ayuda: "Clic: ajustes rápidos · Rueda: volumen · Clic central: silencio"
      onPulsado: function(b) {
        if (b === Qt.RightButton) barra.menu()
        else barra.accion(b === Qt.MiddleButton ? "silencio" : "rapidos")
      }
      onRueda: function(p) { barra.accion(p > 0 ? "mas" : "menos") }
    }
  }

  Component {
    id: reloj
    Boton {
      alto: mod.alto
      colores: mod.c
      id: hora
      property date ahora: new Date()
      texto: Qt.formatTime(ahora, mod.v ? "HH:mm" : mod.tema.reloj) + (!mod.tema.fecha ? ""
             : mod.v ? "\n" + ahora.toLocaleDateString(Qt.locale(), mod.tema.compacto || mod.tema.pixelado || mod.alto < 56 ? "d/M" : "d MMM")
             : "  " + ahora.toLocaleDateString(Qt.locale(), mod.tema.fecha))
      tam: mod.v ? Math.min(mod.tema.tamano, 13) : mod.tema.tamano
      ayuda: ahora.toLocaleDateString(Qt.locale(), Locale.LongFormat)
      onPulsado: function(b) { if (b === Qt.RightButton) barra.menu(); else barra.accion("avisos") }
      Timer { interval: 1000; running: true; repeat: true; onTriggered: hora.ahora = new Date() }
    }
  }

  Component {
    id: temasC
    Boton {
      alto: mod.alto
      colores: mod.c
      texto: "\uE771"
      fuente: "Segoe Fluent Icons"
      colorTexto: mod.c.acento2
      tam: mod.tema.tamano + 3
      ayuda: mod.tema.nombre + " · Clic: temas · Rueda: cambiar"
      onPulsado: barra.menu()
      onRueda: function(p) { barra.girar_tema(-p) }
    }
  }

  Component {
    id: clauditoC
    Item {
      width: mod.v ? mod.alto : 60
      height: mod.v ? 50 : mod.alto
      clip: true
      Rectangle {       // late cuando Claude te necesita
        anchors { fill: parent; margins: 2 }
        radius: Math.min(mod.tema.radio, height / 2)
        color: mod.c.alerta
        opacity: 0
        SequentialAnimation on opacity {
          running: barra.claude.modo === "waiting" && barra.animar
          loops: Animation.Infinite
          alwaysRunToEnd: true
          NumberAnimation { to: 0.45; duration: 500 }
          NumberAnimation { to: 0; duration: 500 }
          PauseAnimation { duration: 300 }
        }
      }
      Loader {
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: mod.tema.compacto && !mod.v ? -3 : 0 }
        width: 60; height: 50
        source: barra.personaje
        onLoaded: {
          item.mode = Qt.binding(function() { return barra.claude.modo })
          if ("minimo" in item) item.minimo = Qt.binding(function() { return barra.paso * (esPrimaria ? 1 : 2) })
          item.seasonHat = Qt.binding(function() { return barra.ropa.gorro })
          item.seasonOutfit = Qt.binding(function() { return barra.ropa.traje })
          item.visible = Qt.binding(function() { return barra.animar })
        }
      }
      ZonaClaude { anchors.fill: parent }
    }
  }
}
