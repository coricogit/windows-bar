"""En qué momento del día estamos, sin ubicación: salida y puesta del sol
aproximadas para latitudes medias del hemisferio norte."""
import math

MOMENTOS = ("noche", "amanecer", "dia", "atardecer")


def sol(mes):
    """(salida, puesta) en horas: de 6-18.5 en verano a 7-17.9 en invierno, aprox."""
    k = math.cos((mes - 6.5) / 12 * 2 * math.pi)       # 1 en verano, -1 en invierno
    return 6.5 - 0.6 * k, 18.6 + 0.7 * k


def momento(hora, mes):
    sale, pone = sol(mes)
    if sale - 0.6 <= hora < sale + 0.9:
        return "amanecer"
    if sale + 0.9 <= hora < pone - 1:
        return "dia"
    if pone - 1 <= hora < pone + 0.6:
        return "atardecer"
    return "noche"
