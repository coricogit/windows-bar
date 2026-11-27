"""Cuánto se mueve la barra según lo que pase en el equipo.

Nada de esto apaga funciones: solo frena los dibujos cuando nadie los ve
(pantalla bloqueada, barra escondida) o cuando el portátil va con batería.
"""
from .temas import RITMO

ENCHUFE, BATERIA, AHORRO = "enchufe", "bateria", "ahorro"


def corriente(estado):
    """De red.bateria_estado() a ENCHUFE, BATERIA o AHORRO."""
    if not estado:
        return ENCHUFE
    enchufado, ahorro = estado
    return AHORRO if ahorro else ENCHUFE if enchufado else BATERIA


def mover(animar, animaciones, inactivo, oculto, luz):
    """Si los fondos se mueven."""
    return animar and animaciones != "ninguna" and not inactivo and not oculto and luz != AHORRO


def ritmo(animaciones, luz):
    """Milisegundos entre fotogramas de los fondos: con batería, la mitad de fotogramas."""
    base = RITMO.get(animaciones, 200)
    return base * 2 if luz != ENCHUFE else base


def paso(animaciones, inactivo, oculto, luz):
    """Décimas de segundo entre dibujos de Claudito."""
    if oculto:
        return 50
    if inactivo or luz != ENCHUFE:
        return 5
    return {"completas": 1, "suaves": 2}.get(animaciones, 4)


def fps_cava(animaciones, oculto, luz):
    """Fotogramas del visualizador (0: no hace falta el proceso)."""
    if oculto or luz == AHORRO:
        return 0
    fps = {"completas": 30, "suaves": 20}.get(animaciones, 0)
    return min(fps, 15) if luz == BATERIA else fps
