import QtQuick

// Cielo al anochecer con estrellas, colinas y hierba, en bloques de 3 px.
Canvas {
  renderStrategy: Canvas.Cooperative
  onWidthChanged: requestPaint()
  onPaint: {
    var x = getContext("2d"), p = 3, s = 11
    function azar() { s = (s * 16807) % 2147483647; return s / 2147483647 }
    function px(cx, cy, w, h, c) { x.fillStyle = c; x.fillRect(cx * p, cy * p, w * p, h * p) }
    x.reset()
    var n = Math.ceil(width / p), alto = Math.floor(height / p)
    px(0, 0, n, 1, "#17122E")
    for (var i = 0; i < n / 9; i++)
      px(Math.floor(azar() * n), 2 + Math.floor(azar() * 6), 1, 1, azar() > 0.85 ? "#A99BE0" : "#6A5AAE")
    for (var a = 0; a < n; a++) {
      var h = Math.round(3 + 2 * Math.sin(a / 17) + 1.5 * Math.sin(a / 7 + 2))
      px(a, alto - 2 - h, 1, h, "#352B63")
    }
    for (var b = 0; b < n; b++) {
      px(b, alto - 2, 1, 1, b % 2 ? "#4C9A5F" : "#63B874")
      px(b, alto - 1, 1, 1, azar() > 0.8 ? "#5A3A28" : "#6E4A33")
      if (azar() > 0.95) px(b, alto - 3, 1, 1, "#63B874")
    }
  }
}
