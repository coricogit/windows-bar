import QtQuick

// El icono del tiempo, dibujado al estilo del tema (`clima` en tema.json): "neon",
// "flor", "hoja" o "pixel". `tipo`: despejado, parcial, nublado, niebla, lluvia,
// nieve o tormenta.
Canvas {
  id: cl
  property var tema
  property string tipo: "parcial"
  property bool noche: false
  readonly property string estilo: tema.clima
  readonly property var c: tema.colores
  readonly property bool pixel: estilo === "pixel"
  width: pixel ? 22 : tema.compacto ? 19 : 25
  height: pixel ? 20 : width
  renderStrategy: Canvas.Cooperative
  onTipoChanged: requestPaint()
  onNocheChanged: requestPaint()
  onTemaChanged: requestPaint()
  onWidthChanged: requestPaint()

  // ----- píxel: rejillas de 11 x 10, a 2 px -----
  readonly property var dibujos: ({
    sol: ["....Y......", ".Y..Y..Y...", "..YYYYY....", "..YAAAY....", "YYYAAAYYY..", "..YAAAY....", "..YYYYY....", ".Y..Y..Y...", "....Y......"],
    luna: ["..MMMM.....", ".MMNN......", "MMN........", "MMN........", "MMN........", "MMMN....M..", ".MMMNNNMM..", "..MMMMMM...", "....MM....."],
    solito: ["......Y....", "...Y..Y..Y.", "....YYYY...", "...YYAAYY..", ".YYYAAAAYY.", "...YYAAYY.."],
    lunita: [".....MMM...", "....MMN....", "....MN.....", "....MMN..M.", ".....MMMM..", "......MM..."],
    nube: ["", "", "", "...WWW.....", ".WWWWWWW...", "WWWWWWWWWW.", "WWWWWWWWWWW", "GWWWWWWWWWG", ".GGGGGGGGG."],
    alta: ["...WWW.....", ".WWWWWWW...", "WWWWWWWWWW.", "WWWWWWWWWWW", "GWWWWWWWWWG", ".GGGGGGGGG."],
    gotas: ["", "", "", "", "", "", "..B...B..B.", ".B...B..B..", "...B...B...", "..B...B...."],
    copos: ["", "", "", "", "", "", "..F....F...", "....F....F.", ".F....F....", "...F....F.."],
    rayo: ["", "", "", "", "", ".....LL....", "....LL.....", "...LLLL....", ".....LL....", "....LL....."],
    niebla: ["", "..WWWWWWW..", "", "WWWWWWWWW..", "", "..GGGGGGGGG", "", "GGGGGGGG...", ""]
  })
  function poner(x, nombre, dy) {
    var d = dibujos[nombre], t = { Y: "#FFB02E", A: "#FFE27A", M: "#F1EFD8", N: "#B9B49A", W: "#FFFFFF", G: "#A9B8D8", B: "#2F7FE0", F: "#E8F4FF", L: "#FFD23F" }
    function hay(a, b) { return d[a] !== undefined && d[a][b] !== undefined && d[a][b] !== "." }
    for (var f = -1; f <= d.length; f++)
      for (var k = -1; k <= 11; k++) {
        if (hay(f, k)) x.fillStyle = t[d[f][k]]
        else if (nombre !== "gotas" && nombre !== "copos" && nombre !== "niebla" && (hay(f - 1, k) || hay(f + 1, k) || hay(f, k - 1) || hay(f, k + 1))) x.fillStyle = "#17122E"
        else continue
        x.fillRect(k * 2, (f + dy) * 2, 2, 2)
      }
  }
  function enPixel(x) {
    var t = cl.tipo, n = cl.noche
    if (t === "despejado") poner(x, n ? "luna" : "sol", 0.5)
    else if (t === "niebla") poner(x, "niebla", 0)
    else if (t === "nublado") poner(x, "nube", -1)
    else if (t === "parcial") { poner(x, n ? "lunita" : "solito", 0); poner(x, "nube", 0.5) }
    else { poner(x, "alta", 0.5); poner(x, t === "nieve" ? "copos" : "gotas", 0); if (t === "tormenta") poner(x, "rayo", 0) }
  }

  // ----- los demás, en un lienzo de 24 x 24 -----
  function nube(x, dx, dy) {
    x.beginPath()
    x.moveTo(6.5 + dx, 19 + dy)
    x.bezierCurveTo(1.5 + dx, 19 + dy, 1.5 + dx, 13 + dy, 6.5 + dx, 13 + dy)
    x.bezierCurveTo(7 + dx, 7 + dy, 15 + dx, 6.5 + dy, 16.2 + dx, 12 + dy)
    x.bezierCurveTo(21.5 + dx, 11.5 + dy, 22.3 + dx, 19 + dy, 17 + dx, 19 + dy)
    x.closePath()
  }
  function pintar(x, relleno, trazo) {
    if (relleno) { x.fillStyle = relleno; x.fill() }
    if (!trazo) return
    if (estilo === "neon") { x.strokeStyle = Qt.rgba(trazo.r, trazo.g, trazo.b, 0.25); x.lineWidth = 4; x.stroke() }
    x.strokeStyle = trazo; x.lineWidth = estilo === "neon" ? 1.5 : 1; x.stroke()
  }
  function circulo(x, cx, cy, r) { x.beginPath(); x.arc(cx, cy, r, 0, 2 * Math.PI) }
  function gota(x, cx, cy, r) {          // también pétalo u hoja, según el color
    x.beginPath(); x.moveTo(cx + r * 0.5, cy - r * 1.6)
    x.quadraticCurveTo(cx + r * 1.3, cy + r * 0.6, cx, cy + r * 0.9)
    x.quadraticCurveTo(cx - r * 1.1, cy + r * 0.2, cx + r * 0.5, cy - r * 1.6)
    x.closePath()
  }
  function astro(x, cx, cy, r) {
    var neon = estilo === "neon", flor = estilo === "flor", a, i
    if (noche) {
      x.beginPath()
      x.arc(cx, cy, r, 0.6, 5.1); x.quadraticCurveTo(cx - r * 0.35, cy + r * 0.25, cx + r * 0.825, cy + r * 0.565)
      x.closePath()
      pintar(x, neon ? "" : "#F3EBC8", neon ? Qt.color("#C0CAF5") : Qt.color("#B9A97A"))
      return
    }
    if (flor) {                          // el sol es una flor de cerezo
      for (i = 0; i < 5; i++) {
        a = -Math.PI / 2 + i * 2 * Math.PI / 5
        circulo(x, cx + Math.cos(a) * r * 0.72, cy + Math.sin(a) * r * 0.72, r * 0.56)
        pintar(x, "#F48FB1", Qt.color("#D6517D"))
      }
      circulo(x, cx, cy, r * 0.42); pintar(x, "#FFD76B", null)
      return
    }
    for (i = 0; i < 8; i++) {
      a = i * Math.PI / 4
      if (neon) {
        x.beginPath(); x.moveTo(cx + Math.cos(a) * r * 1.1, cy + Math.sin(a) * r * 1.1); x.lineTo(cx + Math.cos(a) * r * 1.55, cy + Math.sin(a) * r * 1.55)
        pintar(x, "", Qt.color("#E0AF68"))
      } else {                           // rayos con forma de hoja
        x.save(); x.translate(cx + Math.cos(a) * r * 1.18, cy + Math.sin(a) * r * 1.18); x.rotate(a)
        x.fillStyle = i % 2 ? "#E0A458" : "#F2C879"; x.beginPath(); x.ellipse(-r * 0.42, -r * 0.2, r * 0.84, r * 0.4); x.fill()
        x.restore()
      }
    }
    circulo(x, cx, cy, r * 0.72)
    pintar(x, neon ? "" : "#F4B955", neon ? Qt.color("#E0AF68") : null)
  }
  function dibujar(x) {
    var neon = estilo === "neon", flor = estilo === "flor", t = tipo, i
    var rn = neon ? "#FF1A1B26" : flor ? "#FFFFFF" : "#EDE6CF", tn = neon ? Qt.color("#7AA2F7") : flor ? Qt.color("#D98CA6") : Qt.color("#8E9A6E")
    if (t === "despejado") { astro(x, 12, 12, neon ? 6.4 : flor ? 8 : 8); return }
    if (t === "niebla") {
      var l = [[4, 8, 17], [2, 12, 20], [5, 16, 21], [3, 20, 15]]
      x.lineCap = "round"
      for (i = 0; i < 4; i++) { x.beginPath(); x.moveTo(l[i][0], l[i][1]); x.lineTo(l[i][2], l[i][1]); x.strokeStyle = tn; x.lineWidth = neon ? 1.6 : 2; x.stroke() }
      return
    }
    if (t === "parcial") astro(x, 16, 8.2, neon ? 4.2 : 5)
    var baja = t === "lluvia" || t === "nieve" || t === "tormenta"
    nube(x, baja ? 0 : -1, baja ? -3.5 : t === "parcial" ? 2 : 0.5)
    pintar(x, rn, tn)
    if (t === "lluvia" || t === "tormenta")
      for (i = 0; i < 3; i++) {
        if (t === "tormenta" && i === 1) continue
        gota(x, 7 + i * 5, 20 + (i % 2), 1.7)
        pintar(x, neon ? "#7DCFFF" : flor ? "#E0709A" : "#7FB3C8", null)
      }
    if (t === "nieve") for (i = 0; i < 4; i++) { circulo(x, 6 + i * 4, 18.5 + (i % 2) * 3, 1.3); pintar(x, neon ? "#C0CAF5" : "#FFFFFF", neon ? null : tn) }
    if (t === "tormenta") {
      x.beginPath(); x.moveTo(13, 13.5); x.lineTo(9.8, 18.6); x.lineTo(12.2, 18.6); x.lineTo(10.6, 23); x.lineTo(15.2, 17); x.lineTo(12.6, 17); x.lineTo(14.4, 13.5); x.closePath()
      pintar(x, "#F4C04E", neon ? Qt.color("#E0AF68") : null)
    }
  }
  onPaint: {
    var x = getContext("2d")
    x.reset()
    if (pixel) { enPixel(x); return }
    x.scale(width / 24, height / 24)
    x.lineJoin = "round"
    dibujar(x)
  }
}
