"""El tiempo, para el botón de widgets. Datos de Open-Meteo (CC BY 4.0).

Windows no enseña el suyo con su barra oculta. Solo se consulta si se ha elegido
una ciudad en el menú: sin ella no sale nada a internet.
"""
import json
import os
import urllib.parse

from . import actualizar

BUSCAR = "https://geocoding-api.open-meteo.com/v1/search?"
AHORA = "https://api.open-meteo.com/v1/forecast?"

# Códigos WMO: (hasta, icono de día, icono de noche, texto)
CODIGOS = ((0, "☀️", "🌙", "Despejado"), (2, "🌤️", "☁️", "Poco nuboso"), (3, "☁️", "☁️", "Nublado"),
           (48, "🌫️", "🌫️", "Niebla"), (57, "🌦️", "🌧️", "Llovizna"), (67, "🌧️", "🌧️", "Lluvia"),
           (77, "❄️", "❄️", "Nieve"), (82, "🌧️", "🌧️", "Chubascos"), (86, "🌨️", "🌨️", "Nieve"),
           (99, "⛈️", "⛈️", "Tormenta"))
NADA = {"hay": False, "icono": "⛅", "grados": "", "texto": ""}


def leer_ciudad(texto):
    """{"nombre", "lat", "lon"} de la respuesta del buscador, o None."""
    try:
        r = json.loads(texto)["results"][0]
        return {"nombre": str(r["name"]), "lat": float(r["latitude"]), "lon": float(r["longitude"])}
    except (ValueError, KeyError, IndexError, TypeError):
        return None


def leer_tiempo(texto):
    """Lo que enseña la barra, o None si la respuesta no vale."""
    try:
        c = json.loads(texto)["current"]
        codigo, grados, dia = int(c["weather_code"]), round(float(c["temperature_2m"])), bool(c["is_day"])
    except (ValueError, KeyError, TypeError):
        return None
    f = next((f for f in CODIGOS if codigo <= f[0]), CODIGOS[-1])
    return {"hay": True, "icono": f[1] if dia else f[2], "grados": f"{grados}°", "texto": f[3]}


def ciudad_valida(c):
    return (isinstance(c, dict) and isinstance(c.get("nombre"), str)
            and all(isinstance(c.get(k), (int, float)) and abs(c[k]) <= 180 for k in ("lat", "lon")))


def _pedir(url, carpeta, traer):
    ruta = os.path.join(carpeta, "tiempo.json")
    traer(url, ruta)
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def buscar_ciudad(nombre, carpeta, traer=actualizar.traer):
    q = urllib.parse.urlencode({"name": nombre, "count": 1, "language": "es"})
    return leer_ciudad(_pedir(BUSCAR + q, carpeta, traer))


def ahora(ciudad, carpeta, traer=actualizar.traer):
    q = urllib.parse.urlencode({"latitude": round(ciudad["lat"], 2), "longitude": round(ciudad["lon"], 2),
                                "current": "temperature_2m,weather_code,is_day"})
    return leer_tiempo(_pedir(AHORA + q, carpeta, traer))
