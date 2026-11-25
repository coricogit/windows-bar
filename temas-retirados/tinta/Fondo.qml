import QtQuick

// Papel con grano, un trazo de pincel arriba y ondas a la derecha.
Canvas {
  renderStrategy: Canvas.Cooperative
  onWidthChanged: requestPaint()
  onPaint: {
    var x = getContext("2d"), s = 7
    function azar() { s = (s * 16807) % 2147483647; return s / 2147483647 }
    x.reset()
    for (var i = 0; i < width * 0.8; i++) {
      x.fillStyle = azar() > 0.5 ? "rgba(240,230,210,0.035)" : "rgba(0,0,0,0.10)"
      x.fillRect(azar() * width, azar() * height, 1 + azar() * 5, 1)
    }
    for (var k = 0; k < 14; k++) {
      var fin = width * (0.45 + azar() * 0.5), y = 1 + k * 0.35
      x.strokeStyle = "rgba(200,85,61," + (0.10 + azar() * 0.25) + ")"
      x.lineWidth = 0.6 + azar()
      x.beginPath(); x.moveTo(0, y)
      x.bezierCurveTo(fin * 0.3, y + 2, fin * 0.7, y - 1.5, fin, y + azar() * 2)
      x.stroke()
    }
    x.strokeStyle = "rgba(240,230,210,0.07)"; x.lineWidth = 1
    for (var c = 0; c < 9; c++)
      for (var r = 8; r <= 26; r += 6) {
        x.beginPath(); x.arc(width - 30 - c * 46, height + 4, r, Math.PI, 2 * Math.PI); x.stroke()
      }
  }
}
