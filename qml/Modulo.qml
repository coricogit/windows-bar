import QtQuick

// Un módulo de la barra, por su nombre.
Loader {
  id: mod
  property string nombre
  property var tema
  property real alto: 40
  property real limite: 600
  readonly property var c: tema.colores
  height: alto
  sourceComponent: ({ inicio: inicio, tareas: tareasC, titulo: titulo, musica: musicaC, sistema: sistemaC,
                      bandeja: bandejaC, volumen: volumen, reloj: reloj, temas: temasC, claudito: clauditoC })[nombre]

  Component {
    id: inicio
    Boton {
      alto: mod.alto
      texto: mod.tema.inicio
      tam: mod.tema.tamano + 6
      colorTexto: mod.c.acento
      ayuda: "Inicio"
      onPulsado: function(b) { barra.accion(b === Qt.RightButton ? "menu_inicio" : "inicio") }
    }
  }

  Component {
    id: tareasC
    ListView {
      orientation: ListView.Horizontal
      width: Math.min(contentWidth, mod.limite)
      height: mod.alto
      clip: true
      interactive: contentWidth > width
      spacing: 2
      model: tareas
      // La gota de vidrio se desliza hasta la ventana activa.
      property Item activaItem: null
      Rectangle {
        parent: contentItem
        z: -1
        visible: mod.tema.indicador === "gota" && !!activaItem
        x: activaItem ? activaItem.x + 2 : 0
        y: 3
        width: activaItem ? activaItem.width - 4 : 0
        height: mod.alto - 6
        radius: height / 2
        color: "#3DFFFFFF"
        border.color: "#8CFFFFFF"
        border.width: 1
        Behavior on x { SpringAnimation { spring: 3.2; damping: 0.32; epsilon: 0.3 } }
      }
      add: Transition { NumberAnimation { property: "scale"; from: 0.4; to: 1; duration: 160; easing.type: Easing.OutBack } }
      displaced: Transition { NumberAnimation { property: "x"; duration: 160 } }
      delegate: Tarea {
        tema: mod.tema
        alto: mod.alto
        clave: model.key
        titulo: model.titulo || ""
        icono: model.icono || ""
        activa: !!model.activa
        abierta: !!model.abierta
        minimizada: !!model.minimizada
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
      width: Math.min(implicitWidth, 420)
      height: mod.alto
      elide: Text.ElideRight
      text: barra.titulo
    }
  }

  Component {
    id: musicaC
    Row {
      height: mod.alto
      // No `visible`: dentro de un grupo oculto siempre sería falso.
      readonly property bool hay: barra.cancion.titulo !== ""
      width: hay ? implicitWidth : 0
      spacing: 0
      Boton { alto: mod.alto; texto: "\uE892"; fuente: "Segoe Fluent Icons"; tam: 13; ayuda: "Anterior"; ancho: 28; colorTexto: mod.c.tenue; onPulsado: barra.accion("anterior") }
      Boton {
        alto: mod.alto
        texto: barra.cancion.sonando ? "\uE769" : "\uE768"; fuente: "Segoe Fluent Icons"; tam: 13; ancho: 28; colorTexto: mod.c.acento
        ayuda: barra.cancion.sonando ? "Pausar" : "Reproducir"
        onPulsado: barra.accion("pausa")
      }
      Boton { alto: mod.alto; texto: "\uE893"; fuente: "Segoe Fluent Icons"; tam: 13; ayuda: "Siguiente"; ancho: 28; colorTexto: mod.c.tenue; onPulsado: barra.accion("siguiente") }
      Texto {
        height: mod.alto
        width: Math.min(implicitWidth, 300)
        elide: Text.ElideRight
        leftPadding: 4
        rightPadding: 6
        text: barra.cancion.titulo + (barra.cancion.artista ? " — " + barra.cancion.artista : "")
      }
    }
  }

  Component {
    id: sistemaC
    Row {
      height: mod.alto
      spacing: 8
      leftPadding: 4
      rightPadding: 4
      Repeater {
        model: [["CPU", "cpu"], ["RAM", "ram"], ["GPU", "gpu"]]
        Row {
          readonly property int valor: barra.datos[modelData[1]]
          visible: valor >= 0
          height: mod.alto
          spacing: 4
          Texto { text: modelData[0]; height: mod.alto; color: mod.c.tenue; font.pixelSize: mod.tema.tamano - 2 }
          Texto {
            text: parent.valor + "%"
            width: medida.width
            height: mod.alto
            horizontalAlignment: Text.AlignRight
            color: parent.valor >= 85 ? mod.c.alerta : mod.c.texto
            TextMetrics { id: medida; text: "100%"; font.family: mod.tema.fuente; font.pixelSize: mod.tema.tamano; font.bold: mod.tema.negrita }
          }
        }
      }
    }
  }

  Component {
    id: bandejaC
    Row {
      height: mod.alto
      Rectangle {      // en temas claros, para que se vean los iconos blancos
        z: -1
        parent: mod
        visible: mod.item && mod.item.width > 0
        anchors { fill: parent; topMargin: 5; bottomMargin: 5 }
        radius: height / 2
        color: mod.c.fondoBandeja
      }
      Repeater {
        model: bandeja
        Item {
          width: mod.tema.compacto ? 24 : 28
          height: mod.alto
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
      texto: (barra.datos.silencio ? "✕" : "♪") + " " + barra.datos.volumen + "%"
      ayuda: "Clic: ajustes rápidos · Rueda: volumen · Clic central: silencio"
      onPulsado: function(b) { barra.accion(b === Qt.MiddleButton ? "silencio" : "rapidos") }
      onRueda: function(p) { barra.accion(p > 0 ? "mas" : "menos") }
    }
  }

  Component {
    id: reloj
    Boton {
      alto: mod.alto
      id: hora
      property date ahora: new Date()
      texto: Qt.formatTime(ahora, mod.tema.reloj) + (mod.tema.fecha ? "  " + ahora.toLocaleDateString(Qt.locale(), mod.tema.fecha) : "")
      ayuda: ahora.toLocaleDateString(Qt.locale(), Locale.LongFormat)
      onPulsado: barra.accion("avisos")
      Timer { interval: 1000; running: true; repeat: true; onTriggered: hora.ahora = new Date() }
    }
  }

  Component {
    id: temasC
    Boton {
      alto: mod.alto
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
      width: 60
      height: mod.alto
      clip: true
      Loader {
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: mod.tema.compacto ? -3 : 0 }
        width: 60; height: 50
        source: barra.personaje
        onLoaded: {
          item.mode = Qt.binding(function() { return barra.claude.modo })
          item.seasonHat = Qt.binding(function() { return barra.ropa.gorro })
          item.seasonOutfit = Qt.binding(function() { return barra.ropa.traje })
          item.visible = Qt.binding(function() { return barra.animar })
        }
      }
      Aviso { texto: barra.claude.texto; fuente: zc }
      MouseArea { id: zc; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
    }
  }
}
