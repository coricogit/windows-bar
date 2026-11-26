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


def en_borde(lado, zona, punto, grueso=2):
    """¿Está el ratón pegado al borde de la pantalla, a lo largo de la barra?
    `zona` es (x, y, ancho, alto) de la barra."""
    x, y, an, al = zona
    px, py = punto
    if lado in VERTICALES:
        if not y <= py < y + al:
            return False
        return px < x + grueso if lado == "izquierda" else px >= x + an - grueso
    if not x <= px < x + an:
        return False
    return py < y + grueso if lado == "arriba" else py >= y + al - grueso


def dentro(zona, punto, holgura=0):
    x, y, an, al = zona
    return x - holgura <= punto[0] < x + an + holgura and y - holgura <= punto[1] < y + al + holgura


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
