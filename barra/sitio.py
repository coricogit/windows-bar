"""En qué lado de la pantalla está la barra y dónde salen sus ventanitas.
Los rectángulos son (x, y, ancho, alto)."""

LADOS = {"abajo": "Abajo", "arriba": "Arriba", "izquierda": "Izquierda", "derecha": "Derecha"}
VERTICALES = ("izquierda", "derecha")


def franja(lado, pantalla, grosor):
    """El rectángulo de la barra."""
    x, y, an, al = pantalla
    return {"abajo": (x, y + al - grosor, an, grosor), "arriba": (x, y, an, grosor),
            "izquierda": (x, y, grosor, al), "derecha": (x + an - grosor, y, grosor, al)}[lado]


def margenes(lado, grosor):
    """Lo reservado en cada borde: (izquierda, arriba, derecha, abajo)."""
    return tuple(grosor if lado == n else 0 for n in ("izquierda", "arriba", "derecha", "abajo"))


def colocar(lado, ancla, an, al, pantalla, grosor, hueco=8, borde=6):
    """Esquina de una ventanita de `an` x `al`, pegada a la barra y centrada en
    el punto `ancla`, sin salirse de la pantalla."""
    x, y, pan, pal = pantalla

    def dentro(v, desde, total, mio):
        return max(desde + borde, min(v, desde + total - mio - borde))

    px, py = ancla[0] - an / 2, ancla[1] - al / 2
    if lado == "abajo":
        py = y + pal - grosor - al - hueco
    elif lado == "arriba":
        py = y + grosor + hueco
    elif lado == "izquierda":
        px = x + grosor + hueco
    else:
        px = x + pan - grosor - an - hueco
    return round(dentro(px, x, pan, an)), round(dentro(py, y, pal, al))


def mas_cerca(punto, pantalla):
    """El lado de la pantalla más próximo a un punto."""
    x, y, an, al = pantalla
    d = {"abajo": (y + al - punto[1]) / al, "arriba": (punto[1] - y) / al,
         "izquierda": (punto[0] - x) / an, "derecha": (x + an - punto[0]) / an}
    return min(d, key=d.get)
