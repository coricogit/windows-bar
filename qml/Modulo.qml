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
  sourceComponent: ({ inicio: inicio, buscar: buscarC, tareas: tareasC, titulo: titulo, musica: musicaC, sistema: sistemaC,
                      bandeja: bandejaC, vista: vistaC, volumen: volumen, reloj: reloj, widgets: widgetsC, temas: temasC, claudito: clauditoC })[nombre]

  Component {
    id: inicio
    Boton {
      id: botonInicio
      alto: mod.alto
      colores: mod.c
      ancho: mod.tema.burbujas ? mod.alto : mod.tema.compacto ? 30 : 38
      ayuda: "Inicio · Clic central: buscar · Rueda: cambiar de tema (" + mod.tema.nombre + ")"
      onPulsado: function(b) { barra.accion(b === Qt.RightButton ? "menu_inicio" : b === Qt.MiddleButton ? "buscador" : "inicio") }
      onRueda: function(p) { barra.girar_tema(-p) }
      Rectangle {        // Burbujas: también en su círculo, como los programas
        visible: mod.tema.burbujas
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) - 2; height: width
        radius: mod.tema.pixelado ? 0 : width / 2
        color: botonInicio.encima ? Qt.lighter(mod.c.isla, 1.25) : mod.c.isla
        border.width: 1
        border.color: mod.c.borde
      }
      Logo { anchors.centerIn: parent; tema: mod.tema; encima: botonInicio.encima }
    }
  }

  Component {          // Vista de tareas: Win+Tab; con varios escritorios, en cuál estás
    id: vistaC
    Boton {
      id: botonVista
      alto: mod.alto
      colores: mod.c
      readonly property string numero: mod.tema.vista || "insignia"
      readonly property bool varios: barra.escritorio.total > 1
      // El de Windows 11 se dibuja (IconoVista); con el número al lado, el glifo de reserva.
      readonly property bool win11: mod.tema.icono_vista === "windows" && !(numero === "texto" && varios)
      ancho: numero === "texto" && varios ? natural : mod.tema.burbujas ? mod.alto : mod.tema.compacto ? 30 : 38
      fuente: numero === "texto" && varios ? mod.tema.fuente : "Segoe Fluent Icons"
      tam: numero === "texto" && varios ? mod.tema.tamano : 16
      glifo: numero === "texto" && varios ? (mod.tema.glifoVista || "\uE7C4") : ""
      texto: numero === "texto" && varios ? barra.escritorio.n : win11 ? "" : (mod.tema.glifoVista || "\uE7C4")
      ayuda: "Vista de tareas" + (barra.escritorio.total > 1 ? " · Escritorio " + barra.escritorio.n + " de " + barra.escritorio.total : "")
             + " · Rueda: cambiar de escritorio · Clic central: escritorio nuevo"
      onPulsado: function(b) { barra.accion(b === Qt.MiddleButton ? "escritorio_nuevo" : "vista") }
      onRueda: function(p) { barra.accion(p > 0 ? "escritorio_ant" : "escritorio_sig") }
      Rectangle {        // Burbujas: también en su círculo
        visible: mod.tema.burbujas
        z: -1
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) - 2; height: width
        radius: mod.tema.pixelado ? 0 : width / 2
        color: botonVista.encima ? Qt.lighter(mod.c.isla, 1.25) : mod.c.isla
        border.width: 1
        border.color: mod.c.borde
      }
      IconoVista {
        visible: botonVista.win11
        anchors.centerIn: parent
        anchors.verticalCenterOffset: botonVista.numero === "puntos" && botonVista.varios && !mod.v ? -2 : 0
        lado: Math.round(Math.min(20, mod.alto * 0.42))
        tinta: mod.c.texto
      }
      Row {              // Puntos: uno por escritorio, el tuyo encendido
        visible: botonVista.numero === "puntos" && botonVista.varios
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: mod.tema.compacto ? 2 : 5 }
        spacing: 2
        Repeater {
          model: Math.min(6, barra.escritorio.total)
          Rectangle {
            width: index + 1 === barra.escritorio.n ? 6 : 3; height: 3
            radius: mod.tema.pixelado ? 0 : 1.5
            color: index + 1 === barra.escritorio.n ? mod.c.acento : mod.c.tenue
          }
        }
      }
      Rectangle {        // el número del escritorio, si hay más de uno
        visible: botonVista.numero === "insignia" && barra.escritorio.total > 1
        anchors { right: parent.right; bottom: parent.bottom; rightMargin: 3; bottomMargin: mod.tema.compacto ? 3 : 6 }
        width: Math.max(13, num.implicitWidth + 5); height: 13
        radius: mod.tema.pixelado ? 0 : 6.5
        color: mod.c.acento
        Texto {
          id: num
          anchors.centerIn: parent
          text: barra.escritorio.n
          font.pixelSize: 9
          font.bold: true
          color: mod.c.acento.hslLightness > 0.55 ? "#000000" : "#FFFFFF"
        }
      }
    }
  }

  Component {          // el campo «Buscar»: abre el buscador (barra/buscador.py)
    id: buscarC
    Item {
      id: campo
      // Automática: en barras estrechas (compacta, dock, burbujas) solo la lupa, como hace Windows.
      // Una forma elegida se respeta en cualquier formato; en vertical no cabe más que la lupa.
      readonly property string elegida: mod.tema.busqueda || "auto"
      readonly property bool corto: mod.v || elegida === "lupa"
                                    || (elegida === "auto" && (mod.tema.compacto || mod.tema.dock || mod.tema.burbujas))
      readonly property string forma: elegida === "auto" ? "campo" : elegida
      readonly property bool win11: forma === "windows"
      readonly property real f: Math.max(0.8, Math.min(1.4, mod.alto / 46))
      // Fondo oscuro si el texto del tema es claro: con eso se eligen la lupa y los colores de Windows.
      // (los colores del tema llegan como texto: pasan por una propiedad `color` para leer su luz)
      readonly property color colorTexto: mod.c.texto
      readonly property bool oscuro: colorTexto.hslLightness > 0.5
      readonly property string lupa: mod.tema.lupaWindows ? (mod.tema.lupaWindows[oscuro ? "oscuro" : "claro"] || "") : ""
      width: mod.v ? mod.alto : corto ? (mod.tema.burbujas ? mod.alto : mod.tema.compacto ? 30 : 38)
             : Math.round((win11 ? 214 : 200) * f)
      height: mod.v ? 38 : mod.alto
      Rectangle {
        id: caja
        anchors.centerIn: parent
        width: campo.corto ? Math.min(parent.width, parent.height) - (mod.tema.burbujas ? 2 : 8) : parent.width - 6
        height: campo.corto ? width : campo.win11 ? Math.round(Math.min(36, mod.alto * 0.72)) : Math.round(mod.alto * 0.66)
        radius: mod.tema.pixelado && !campo.win11 ? 0
                : campo.corto ? (mod.tema.burbujas ? width / 2 : Math.min(Math.max(mod.tema.radio, mod.tema.radioBoton), 8))
                : campo.forma === "pastilla" || campo.win11 ? height / 2 : Math.min(height / 2, Math.max(mod.tema.radio, 6))
        // Como Windows 11: los rellenos y bordes de sus controles (Fluent), en claro y en oscuro.
        color: campo.win11 && !campo.corto
               ? (campo.oscuro ? (raton.pressed ? "#08FFFFFF" : raton.containsMouse ? "#15FFFFFF" : "#0FFFFFFF")
                               : (raton.pressed ? "#4DF9F9F9" : raton.containsMouse ? "#80F9F9F9" : "#B3FFFFFF"))
               : raton.containsMouse ? mod.c.encima : campo.corto || campo.forma === "subrayado" ? "transparent"
               : Qt.rgba(mod.c.texto.r, mod.c.texto.g, mod.c.texto.b, campo.forma === "pastilla" ? 0.13 : 0.07)
        border.width: campo.corto ? 0 : campo.win11 ? 1 : campo.forma !== "campo" ? 0 : 1
        border.color: campo.win11 ? (campo.oscuro ? "#17FFFFFF" : "#0F000000")
                      : raton.containsMouse ? mod.c.acento : mod.c.borde
        Behavior on color { ColorAnimation { duration: 120 } }
        Rectangle {          // Subrayado: solo una raya debajo
          visible: campo.forma === "subrayado" && !campo.corto
          anchors { left: parent.left; right: parent.right; bottom: parent.bottom; leftMargin: 6; rightMargin: 6 }
          height: raton.containsMouse ? 2 : 1
          color: raton.containsMouse ? mod.c.acento : mod.c.tenue
        }
        Row {
          anchors.verticalCenter: parent.verticalCenter
          anchors.horizontalCenter: campo.corto ? parent.horizontalCenter : undefined
          x: campo.corto ? 0 : Math.round((campo.win11 ? 10 : 12) * campo.f)
          spacing: Math.round((campo.win11 ? 8 : 9) * campo.f)
          Image {            // la lupa de Windows 11, del propio sistema
            visible: campo.lupa !== ""
            anchors.verticalCenter: parent.verticalCenter
            source: campo.lupa
            width: Math.round((campo.corto ? 24 : 20) * campo.f); height: width
            // Se carga ya a su tamaño en pantalla: el dibujo por software no hace mipmaps y,
            // reduciendo 64 px al pintar, se salta píxeles y el aro sale dentado.
            sourceSize: Qt.size(Math.round(width * Screen.devicePixelRatio), Math.round(height * Screen.devicePixelRatio))
            smooth: true
            scale: raton.pressed ? 0.9 : 1
            Behavior on scale { NumberAnimation { duration: 90 } }
          }
          Texto {
            visible: campo.lupa === ""
            text: mod.tema.glifoBusqueda || ""
            font.family: "Segoe Fluent Icons"
            font.pixelSize: Math.round(15 * campo.f)
            font.bold: false
            color: campo.corto ? mod.c.texto : mod.c.tenue
          }
          Texto {
            visible: !campo.corto
            anchors.verticalCenter: parent.verticalCenter
            text: "Buscar"
            color: campo.win11 ? (campo.oscuro ? "#C5FFFFFF" : "#9E000000") : mod.c.tenue
            font.family: campo.win11 ? "Segoe UI Variable Text" : mod.tema.fuente
            font.pixelSize: Math.round((campo.win11 ? 14 : mod.tema.tamano) * campo.f)
            font.bold: false
          }
        }
      }
      Aviso { texto: "Buscar aplicaciones, configuración y archivos (Alt+Espacio)"; fuente: raton }
      MouseArea {
        id: raton
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(e) { barra.accion(e.button === Qt.RightButton ? "menu_inicio" : "buscador") }
      }
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
      spacing: 2 + mod.tema.aire / 2
      model: tareas
      // La gota: sus dos bordes van a distinta velocidad, así se estira al moverse.
      property Item activaItem: null
      property real ratonX: -1000          // en el dock: dónde está el ratón, para la lupa
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
        atencion: !!model.atencion
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
    Item {             // solo las barras; con el ratón se maneja la música
      // No `visible`: dentro de un grupo oculto siempre sería falso.
      // En pausa se queda 8 s (para seguir con un clic) y luego se recoge.
      readonly property bool sonando: barra.cancion.sonando === true
      property bool reciente: sonando
      onSonandoChanged: if (sonando) reciente = true; else recoger.restart()
      Timer { id: recoger; interval: 8000; onTriggered: if (!parent.sonando) parent.reciente = false }
      readonly property bool hay: barra.cancion.titulo !== "" && barra.conCava && (sonando || reciente)
      width: mod.v ? mod.alto : hay ? 122 : 0
      height: mod.v ? (hay ? 40 : 0) : mod.alto
      clip: true
      Behavior on width { enabled: barra.mover; NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
      Cava {
        anchors.centerIn: parent
        tema: mod.tema
        cuantas: mod.v ? 8 : 16
        visible: parent.hay
        width: mod.v ? mod.alto - 14 : 112
        height: mod.v ? 30 : Math.min(32, mod.alto - 8)
      }
      Aviso { texto: "Clic: pausar o seguir · Rueda: anterior o siguiente"; fuente: zc }
      MouseArea {
        id: zc
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(e) { if (e.button === Qt.RightButton) barra.menu(); else barra.accion("pausa") }
        onWheel: function(e) { barra.accion(e.angleDelta.y > 0 ? "anterior" : "siguiente") }
      }
    }
  }

  Component {
    id: sistemaC
    // Con «pequeños», tres barritas finas sin texto; se abren en los medidores
    // completos al pasar el ratón o cuando alguno pasa del 75 % (se cierran bajo 60).
    Item {
      id: sis
      readonly property var lista: [["CPU", "cpu"], ["RAM", "ram"], ["GPU", "gpu"]].filter(function(m) {
        return barra.medidores.indexOf(m[1]) >= 0 })
      readonly property bool mini: barra.medidoresMini && !mod.v
      property bool subido: false
      function revisar() {
        var m = 0
        for (var i = 0; i < lista.length; i++) m = Math.max(m, barra.datos[lista[i][1]])
        subido = m >= 75 || (subido && m >= 60)
      }
      Connections { target: barra; function onDatosChanged() { sis.revisar() } }
      Component.onCompleted: revisar()
      readonly property bool abierto: !mini || subido || zm.containsMouse
      width: abierto ? rejilla.width : barritas.width + 8
      height: mod.v ? rejilla.height : mod.alto
      clip: true
      Behavior on width {
        enabled: barra.mover
        NumberAnimation { duration: 220; easing.type: Easing.OutCubic }
      }

      Grid {
        id: rejilla
        anchors.verticalCenter: mod.v ? undefined : parent.verticalCenter
        columns: mod.v ? 1 : 3
        spacing: mod.v ? 6 : (mod.tema.compacto ? 8 : 10) + mod.tema.aire / 2
        leftPadding: mod.v ? 0 : 4
        rightPadding: mod.v ? 0 : 4
        topPadding: mod.v ? 4 : 0
        bottomPadding: mod.v ? 4 : 0
        opacity: sis.abierto ? 1 : 0
        visible: opacity > 0
        Behavior on opacity { enabled: barra.mover; NumberAnimation { duration: 180 } }
        Repeater {
          model: sis.lista
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
      }

      Row {
        id: barritas
        x: 4
        anchors.verticalCenter: parent.verticalCenter
        spacing: 3
        visible: sis.mini && opacity > 0
        opacity: sis.abierto ? 0 : 1
        Behavior on opacity { enabled: barra.mover; NumberAnimation { duration: 180 } }
        Repeater {
          model: sis.lista
          Rectangle {
            readonly property int valor: barra.datos[modelData[1]]
            readonly property color tono: valor >= 85 ? mod.c.alerta
                : ([mod.c.medidor1, mod.c.medidor2, mod.c.medidor3][index] || mod.c.acento)
            visible: valor >= 0         // sin GPU medible, no sale
            width: 4
            height: Math.round(mod.alto * 0.5)
            radius: mod.tema.pixelado ? 0 : 2
            color: Qt.rgba(tono.r, tono.g, tono.b, 0.22)
            Rectangle {
              anchors.bottom: parent.bottom
              width: parent.width
              height: Math.max(2, parent.height * Math.min(100, parent.valor) / 100)
              radius: parent.radius
              color: parent.tono
              Behavior on height { enabled: barra.mover; NumberAnimation { duration: 300 } }
            }
          }
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
      readonly property real celda: (mod.tema.compacto ? 24 : 28) + (mod.v ? 0 : mod.tema.aire / 2)
      columns: mod.v ? Math.max(1, Math.floor(mod.alto / celda)) : 99
      // Sin fondo propio: los iconos van directamente sobre la barra, en todos los temas.
      // Se pliega sola al rato de quitar el ratón.
      HoverHandler { id: sobre }
      Timer { interval: 6000; running: barra.bandejaAbierta && !sobre.hovered; onTriggered: barra.abrir_bandeja(false) }
      Item {           // micrófono en uso (barra/audio.py): solo mientras algún programa graba
        readonly property var quien: barra.datos.microfono || []
        visible: quien.length > 0
        width: rejilla.celda
        height: mod.v ? width : mod.alto
        Rectangle {
          anchors.centerIn: parent
          width: parent.width - 4; height: width
          radius: mod.tema.pixelado ? 0 : width / 2
          color: Qt.rgba(1, 0.6, 0.15, zmic.containsMouse ? 0.32 : 0.2)
        }
        Texto {
          anchors.centerIn: parent
          font.family: "Segoe Fluent Icons"
          font.pixelSize: 13
          font.bold: false
          color: "#FFB14A"
          text: ""
        }
        Aviso { texto: "Usando el micrófono: " + parent.quien.join(", "); fuente: zmic }
        MouseArea {
          id: zmic
          anchors.fill: parent
          hoverEnabled: true
          onClicked: barra.accion("microfono")
        }
      }
      Item {           // la flecha de los iconos ocultos
        visible: barra.ocultos > 0
        width: rejilla.celda
        height: mod.v ? width : mod.alto
        Rectangle {
          anchors.centerIn: parent
          width: parent.width; height: width
          radius: Math.min(Math.max(mod.tema.radio, mod.tema.radioBoton), 6)
          color: zf.containsMouse ? mod.c.encima : "transparent"
        }
        Texto {
          anchors.centerIn: parent
          font.family: "Segoe Fluent Icons"
          font.pixelSize: 11
          font.bold: false
          color: mod.c.texto
          text: mod.v ? (barra.bandejaAbierta ? "\uE70E" : "\uE70D") : (barra.bandejaAbierta ? "\uE76C" : "\uE76B")
        }
        Aviso { texto: barra.bandejaAbierta ? "Plegar" : "Iconos ocultos: " + barra.ocultos; fuente: zf }
        MouseArea {
          id: zf
          anchors.fill: parent
          hoverEnabled: true
          acceptedButtons: Qt.LeftButton | Qt.RightButton
          onClicked: function(e) { if (e.button === Qt.RightButton) barra.menu(); else barra.abrir_bandeja(!barra.bandejaAbierta) }
        }
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
            border.width: barra.seleccion === "b:" + model.key ? 2 : 0
            border.color: mod.c.acento
          }
          Image {
            anchors.centerIn: parent
            width: 16; height: 16
            sourceSize: Qt.size(16, 16)
            source: model.icono === "" ? "" : model.icono + mod.tema.estiloBandeja
            opacity: model.oculto ? 0.75 : 1
            smooth: !mod.tema.pixelado
            mipmap: !mod.tema.pixelado
            cache: false
          }
          Aviso { texto: model.tip + "\nClic central: " + (model.oculto ? "dejar a la vista" : "ocultar"); fuente: zona }
          MouseArea {
            id: zona
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
            onClicked: function(e) {
              if (e.button === Qt.MiddleButton) barra.ocultar_icono(model.key)
              else barra.pulsar_bandeja(model.key, e.button === Qt.RightButton)
            }
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
      readonly property bool mudo: barra.datos.silencio || barra.datos.volumen === 0
      texto: mod.tema.glifos ? (mudo ? "\uE74F" : ["\uE993", "\uE994", "\uE995"][Math.min(2, Math.floor(barra.datos.volumen / 34))])
             : (barra.datos.silencio ? "✕" : "♪") + (mod.v ? "\n" : " ") + barra.datos.volumen + "%"
      fuente: mod.tema.glifos ? "Segoe Fluent Icons" : mod.tema.fuente
      tam: mod.tema.glifos ? 16 : mod.tema.tamano
      glifo: (barra.datos.red || "") + (barra.datos.bateria ? (mod.v ? "
" : "") + barra.datos.bateria : "")
      ayuda: (barra.datos.redTexto ? barra.datos.redTexto + "
" : "")
             + (barra.datos.bateriaPct >= 0 ? "Batería " + barra.datos.bateriaPct + " %" + (barra.datos.cargando ? " (cargando)" : "") + "
" : "")
             + (mod.tema.glifos ? "Volumen " + barra.datos.volumen + " % · " : "") + "Clic: ajustes rápidos · Rueda: volumen · Clic central: silencio"
      onPulsado: function(b) {
        if (b === Qt.RightButton) barra.menu()
        else barra.accion(b === Qt.MiddleButton ? "silencio" : "rapidos")
      }
      onRueda: function(p) { barra.accion(p > 0 ? "mas" : "menos") }
    }
  }

  Component {
    id: reloj
    Grid {
    // Columnas justas: con alguna de más, Grid deja un hueco al final.
    columns: mod.v ? 1 : 1 + (foco.visible ? 1 : 0) + (crono.visible ? 1 : 0)
    verticalItemAlignment: Grid.AlignVCenter
    horizontalItemAlignment: Grid.AlignHCenter
    Item {             // modo concentración: una luna; clic para salir
      id: foco
      visible: barra.concentrado
      width: visible ? (mod.v ? mod.alto : 30) : 0
      height: visible ? (mod.v ? 30 : mod.alto) : 0
      Rectangle {
        anchors.centerIn: parent
        width: 26; height: 26
        radius: mod.tema.pixelado ? 0 : 13
        color: zf.containsMouse ? mod.c.encima : Qt.rgba(0, 0, 0, 0)
        border.width: 1
        border.color: mod.c.acento
        Texto {
          anchors.centerIn: parent
          text: ""
          font.family: "Segoe Fluent Icons"
          font.pixelSize: 13
          font.bold: false
          color: mod.c.acento
        }
      }
      Aviso { texto: "Concentración: tiempo, medidores y música escondidos; solo avisos importantes · Clic: salir"; fuente: zf }
      MouseArea { id: zf; anchors.fill: parent; hoverEnabled: true; onClicked: barra.concentrarse(false) }
    }
    Item {             // el temporizador en marcha: clic para quitarlo
      id: crono
      readonly property var c: barra.cuenta
      visible: !!c.texto
      width: visible ? (mod.v ? mod.alto : cronoFila.implicitWidth + 22) : 0
      height: visible ? (mod.v ? 34 : mod.alto) : 0
      Rectangle {
        anchors.centerIn: parent
        width: parent.width - 4; height: Math.min(parent.height - 12, 26)
        radius: mod.tema.pixelado ? 0 : height / 2
        color: crono.c.hecho ? mod.c.acento : zc.containsMouse ? mod.c.encima : Qt.rgba(mod.c.texto.r, mod.c.texto.g, mod.c.texto.b, 0.08)
        border.width: 1
        border.color: crono.c.fase === "descanso" ? "#6FCF97" : mod.c.acento
        Rectangle {      // lo que ya ha pasado
          visible: !crono.c.hecho
          x: 1; y: parent.height - 3; height: 2
          width: Math.max(0, (parent.width - 2) * (crono.c.parte || 0))
          color: crono.c.fase === "descanso" ? "#6FCF97" : mod.c.acento
        }
        SequentialAnimation on opacity {
          running: !!crono.c.hecho
          loops: Animation.Infinite
          NumberAnimation { to: 0.45; duration: 450 }
          NumberAnimation { to: 1; duration: 450 }
        }
        Row {
          id: cronoFila
          anchors.centerIn: parent
          spacing: 4
          Texto { visible: !mod.v; text: crono.c.pomodoro ? (crono.c.fase === "descanso" ? "☕" : "🍅") : "⏱"; font.pixelSize: 11; font.bold: false }
          Texto { text: crono.c.texto || ""; font.pixelSize: mod.v ? 10 : 12; color: crono.c.hecho ? "#FFFFFF" : mod.c.texto }
        }
      }
      Aviso { texto: (crono.c.hecho ? "Hecho" : crono.c.fase === "descanso" ? "Descanso" : "Temporizador") + " · Clic: quitar"; fuente: zc }
      MouseArea { id: zc; anchors.fill: parent; hoverEnabled: true; onClicked: barra.parar_cuenta() }
    }
    Boton {
      alto: mod.alto
      colores: mod.c
      id: hora
      property date ahora: new Date()
      // El estilo de la hora (Menú → Widgets → Hora y fecha); «tema» deja el de cada tema.
      readonly property string estilo: mod.tema.hora || "tema"
      readonly property bool doble: estilo === "windows" || estilo === "digital"
                                    || ((estilo === "tema" || estilo === "segundos") && mod.tema.relojDoble && !mod.tema.compacto)
      readonly property bool conFecha: !!mod.tema.fecha && estilo !== "grande"
      readonly property string formatoHora: estilo === "windows" ? "H:mm"
                                            : estilo === "segundos" ? mod.tema.reloj.replace(/mm$/, "mm:ss") : mod.tema.reloj
      readonly property string formatoFecha: ({ windows: "dd/MM/yyyy", una_linea: "ddd d MMM", pastilla: "ddd d",
                                                digital: "ddd dd.MM", agujas: "ddd d" })[estilo] || mod.tema.fecha
      readonly property string letra: estilo === "windows" ? "Segoe UI Variable Text"
                                      : estilo === "digital" ? "Cascadia Mono" : mod.tema.fuente
      readonly property color acento: mod.c.acento
      readonly property color tinta: estilo === "digital" ? mod.c.acento
                                     : estilo === "pastilla" ? (acento.hslLightness > 0.6 ? "#000000" : "#FFFFFF") : mod.c.texto
      // En vertical, un texto de dos líneas; en horizontal, la hora grande y en negrita
      // y la fecha debajo (o al lado), las dos a la medida del alto de la barra.
      readonly property real f: Math.max(0.8, Math.min(1.4, mod.alto / 46))
      alineado: Text.AlignHCenter
      texto: !mod.v ? "" : Qt.formatTime(ahora, "HH:mm") + (!mod.tema.fecha ? ""
             : "
" + ahora.toLocaleDateString(Qt.locale(), mod.tema.compacto || mod.tema.pixelado || mod.alto < 56 ? "d/M" : "d MMM"))
      tam: Math.min(mod.tema.tamano, 13)
      ancho: mod.v ? mod.alto : cara.implicitWidth + (estilo === "pastilla" ? 28 : mod.tema.compacto ? 14 : 20)
      Rectangle {        // En pastilla: la hora sobre el color de acento
        visible: hora.estilo === "pastilla" && !mod.v
        anchors.centerIn: parent
        width: parent.width - 8; height: Math.min(parent.height - 12, Math.round(30 * hora.f))
        radius: mod.tema.pixelado ? 0 : height / 2
        color: hora.encima ? Qt.lighter(mod.c.acento, 1.12) : mod.c.acento
        Behavior on color { ColorAnimation { duration: 120 } }
      }
      Row {              // la esfera (si es de agujas) y la hora con la fecha, centradas
        id: cara
        visible: !mod.v
        anchors.centerIn: parent
        spacing: esferaAgujas.visible ? 8 : 0
      Canvas {           // De agujas: una esfera pequeña; se repinta al cambiar el minuto
        id: esferaAgujas
        visible: hora.estilo === "agujas" && !mod.v
        width: visible ? Math.round(Math.min(30, mod.alto * 0.62)) : 0
        height: width
        anchors.verticalCenter: parent.verticalCenter
        renderStrategy: Canvas.Cooperative
        property int minuto: hora.ahora.getHours() * 60 + hora.ahora.getMinutes()
        onMinutoChanged: requestPaint()
        onVisibleChanged: requestPaint()
        onPaint: {
          var x = getContext("2d"), r = width / 2, h = hora.ahora.getHours() % 12, m = hora.ahora.getMinutes()
          x.reset()
          if (r < 6) return
          x.translate(r, r)
          x.lineCap = "round"
          x.strokeStyle = mod.c.texto
          x.globalAlpha = 0.9
          x.lineWidth = 1.2
          x.beginPath(); x.arc(0, 0, r - 1, 0, 2 * Math.PI); x.stroke()
          x.globalAlpha = 0.5
          for (var i = 0; i < 12; i += 3) {
            var a = i / 12 * 2 * Math.PI
            x.beginPath(); x.moveTo(Math.sin(a) * (r - 3), -Math.cos(a) * (r - 3)); x.lineTo(Math.sin(a) * (r - 5), -Math.cos(a) * (r - 5)); x.stroke()
          }
          x.globalAlpha = 1
          var ah = (h + m / 60) / 12 * 2 * Math.PI, am = m / 60 * 2 * Math.PI
          x.lineWidth = 2
          x.beginPath(); x.moveTo(0, 0); x.lineTo(Math.sin(ah) * r * 0.5, -Math.cos(ah) * r * 0.5); x.stroke()
          x.strokeStyle = mod.c.acento
          x.lineWidth = 1.5
          x.beginPath(); x.moveTo(0, 0); x.lineTo(Math.sin(am) * r * 0.75, -Math.cos(am) * r * 0.75); x.stroke()
          x.fillStyle = mod.c.acento
          x.beginPath(); x.arc(0, 0, 1.6, 0, 2 * Math.PI); x.fill()
        }
      }
      Grid {
        id: esfera
        anchors.verticalCenter: parent.verticalCenter
        columns: hora.doble ? 1 : 2
        columnSpacing: Math.round((hora.estilo === "una_linea" ? 6 : 8) * hora.f)
        rowSpacing: hora.estilo === "windows" ? 0 : Math.round(-3 * hora.f)
        horizontalItemAlignment: hora.estilo === "windows" ? Grid.AlignRight : hora.doble ? Grid.AlignHCenter : Grid.AlignLeft
        verticalItemAlignment: Grid.AlignVCenter
        Texto {
          text: Qt.formatTime(hora.ahora, hora.formatoHora)
          color: hora.tinta
          font.family: hora.letra
          font.bold: hora.estilo !== "windows"
          font.letterSpacing: hora.estilo === "digital" ? 1 : 0
          // En temas con un fondo muy dibujado (bosque), una sombra suave para que se lea.
          style: mod.tema.sombraReloj && hora.estilo !== "pastilla" ? Text.Raised : Text.Normal
          styleColor: "#B0000000"
          font.pixelSize: Math.round((hora.estilo === "windows" ? 12
                                      : hora.estilo === "grande" ? Math.max(20, mod.tema.tamano + 8)
                                      : hora.estilo === "una_linea" || hora.estilo === "pastilla" ? Math.max(14, mod.tema.tamano + 1)
                                      : hora.doble ? Math.max(16, mod.tema.tamano + 3) : Math.max(15, mod.tema.tamano + 2)) * hora.f)
        }
        Texto {
          visible: hora.conFecha
          text: (hora.estilo === "una_linea" ? "·  " : "")
                + (hora.estilo === "digital" ? hora.ahora.toLocaleDateString(Qt.locale(), hora.formatoFecha).toUpperCase()
                                             : hora.ahora.toLocaleDateString(Qt.locale(), hora.formatoFecha))
          color: hora.estilo === "una_linea" || hora.estilo === "digital" ? mod.c.tenue : hora.tinta
          opacity: mod.tema.sombraReloj || hora.estilo === "windows" || hora.estilo === "pastilla" ? 1 : 0.88
          style: mod.tema.sombraReloj && hora.estilo !== "pastilla" ? Text.Raised : Text.Normal
          styleColor: "#B0000000"
          font.family: hora.letra
          font.bold: false
          font.pixelSize: Math.round((hora.estilo === "windows" ? 12 : hora.estilo === "digital" ? 10
                                      : Math.max(13, mod.tema.tamano)) * hora.f)
        }
      }
      }
      ayuda: ahora.toLocaleDateString(Qt.locale(), Locale.LongFormat) + "
Clic: calendario · Clic central: notificaciones"
      onPulsado: function(b) {
        if (b === Qt.RightButton) barra.menu()
        else if (b === Qt.MiddleButton) barra.accion("avisos")
        else { var p = hora.mapToGlobal(hora.width / 2, hora.height / 2); barra.calendario(p.x, p.y) }
      }
      Timer { interval: 1000; running: true; repeat: true; onTriggered: hora.ahora = new Date() }
    }
    }
  }

  Component {
    id: widgetsC
    Item {
      id: wid
      readonly property real ancho: mod.tema.clima === "emoji" ? icono.implicitWidth : dibujo.width
      width: mod.v ? mod.alto : ancho + (barra.tiempo.hay ? datos.width + 5 : 0) + 14
      height: mod.v ? 40 : mod.alto
      Rectangle {
        anchors { fill: parent; topMargin: mod.tema.compacto ? 2 : 4; bottomMargin: mod.tema.compacto ? 2 : 4 }
        radius: Math.min(Math.max(mod.tema.radio, mod.tema.radioBoton), 8)
        color: zw.containsMouse ? mod.c.encima : "transparent"
        Behavior on color { ColorAnimation { duration: 120 } }
      }
      Text {
        id: icono
        x: mod.v ? (parent.width - width) / 2 : 7
        y: mod.v ? 2 : (parent.height - height) / 2
        visible: mod.tema.clima === "emoji"
        text: barra.tiempo.icono
        font.family: "Segoe UI Emoji"
        font.pixelSize: mod.tema.compacto ? 15 : 19
        color: mod.c.texto
      }
      Clima {
        id: dibujo
        visible: mod.tema.clima !== "emoji"
        tema: mod.tema
        tipo: barra.tiempo.tipo
        noche: barra.tiempo.noche
        x: mod.v ? (parent.width - width) / 2 : 7
        y: mod.v ? 1 : (parent.height - height) / 2
      }
      Column {
        id: datos
        visible: barra.tiempo.hay
        x: mod.v ? (parent.width - width) / 2 : 12 + wid.ancho
        y: mod.v ? parent.height - height - 1 : (parent.height - height) / 2
        // Solo los grados: la descripción («Nublado») a 9 px no se leía; va en el aviso.
        Texto { text: barra.tiempo.grados; color: mod.c.texto; font.pixelSize: mod.v ? 10 : 14 }
      }
      Aviso { texto: "Widgets" + (barra.tiempo.hay ? " · " + barra.tiempo.ciudad + ": " + barra.tiempo.grados + ", " + barra.tiempo.texto : " · La ciudad del tiempo se elige en el menú"); fuente: zw }
      MouseArea {
        id: zw
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(e) { if (e.button === Qt.RightButton) barra.menu(); else barra.accion("widgets") }
      }
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
