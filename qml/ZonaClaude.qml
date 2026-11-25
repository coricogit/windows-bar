import QtQuick

// Ratón sobre Claudito: panel al pasar, clic para ir a la sesión que toca.
MouseArea {
  id: zona
  hoverEnabled: true
  acceptedButtons: Qt.LeftButton | Qt.RightButton
  cursorShape: Qt.PointingHandCursor
  onContainsMouseChanged: {
    if (!containsMouse) { barra.claude_salir(); return }
    var p = zona.mapToGlobal(zona.width / 2, 0)
    barra.claude_entrar(p.x, p.y)
  }
  onClicked: function(e) { if (e.button === Qt.RightButton) barra.menu(); else barra.ir_a_claude() }
}
