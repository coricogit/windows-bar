"""Mantiene al día la copia instalada con los releases de GitHub.

Solo se actualiza la instalada (lleva version.txt y su propio Python). Quien la
usa desde el código sigue con `git pull`.

El .zip nuevo se descarga, se compara con el SHA-256 que publica GitHub y se
descomprime; su barra/instalado.py lo pone en su sitio y, si falla, recupera la
versión anterior. Sin ningún .exe sin firmar, que Smart App Control bloquearía.
barra.pyw decide cuándo.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ULTIMO = "https://api.github.com/repos/coricogit/windows-bar/releases/latest"
DESCARGAS = "https://github.com/coricogit/windows-bar/releases/download/"
PROTOCOLO = "=https"
MAX_BYTES = 300_000_000
MAX_INTENTOS = 2          # al día: la que falla se deja hasta mañana
SIN_CONSOLA = 0x08000000


class SinRed(OSError):
    """No se pudo descargar; otra vez será."""


def version_instalada(raiz=RAIZ):
    """"1.2.3", o "" si esta no es una copia instalada."""
    if not os.path.exists(os.path.join(raiz, "python", "pythonw.exe")):
        return ""
    try:
        with open(os.path.join(raiz, "version.txt"), encoding="ascii") as f:
            texto = f.read().strip()
    except (OSError, ValueError):
        return ""
    return texto if numeros(texto) else ""


def numeros(version):
    """"1.2.3" -> (1, 2, 3, 0), o None si no tiene esa forma."""
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]{1,6}(\.[0-9]{1,6}){0,3}", version):
        return None
    n = [int(x) for x in version.split(".")]
    return tuple(n + [0] * (4 - len(n)))


def archivo(version):
    return f"Windows-Bar-{version}.zip"


def mas_nueva(texto, actual):
    """(versión, url, sha256) del .zip, según la respuesta de GitHub, o
    None si no hay nada más nuevo de fiar."""
    try:
        r = json.loads(texto)
    except ValueError:
        return None
    if not isinstance(r, dict) or r.get("draft") or r.get("prerelease"):
        return None
    tag = r.get("tag_name")
    version = tag[1:] if isinstance(tag, str) and tag.startswith("v") else ""
    if not numeros(version) or numeros(version) <= numeros(actual):
        return None
    nombre = archivo(version)
    for a in r.get("assets") or ():
        if not isinstance(a, dict) or a.get("name") != nombre:
            continue
        suma = re.fullmatch(r"sha256:([0-9a-f]{64})", str(a.get("digest")))
        if suma and a.get("browser_download_url") == DESCARGAS + tag + "/" + nombre:
            return version, a["browser_download_url"], suma.group(1)
    return None


def traer(url, ruta):
    """Descarga con el curl de Windows, que usa los certificados de Windows."""
    curl = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "curl.exe")
    orden = [curl, "-q", "--silent", "--fail", "--location", "--max-redirs", "5", "--proto", PROTOCOLO,
             "--proto-redir", PROTOCOLO, "--connect-timeout", "30", "--speed-limit", "1000", "--speed-time", "60",
             "--max-filesize", str(MAX_BYTES), "--user-agent", "Windows-Bar", "--output", ruta]
    proxy = urllib.request.getproxies().get("https")
    if proxy:
        orden += ["--proxy", proxy]
    try:
        codigo = subprocess.run(orden + ["--url", url], creationflags=SIN_CONSOLA, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    except OSError as e:
        raise SinRed(f"curl: {e}") from e
    if codigo:
        raise SinRed(f"curl: error {codigo}")


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for trozo in iter(lambda: f.read(1 << 20), b""):
            h.update(trozo)
    return h.hexdigest()


def descargar(actual, carpeta, saltar=lambda version: False, traer=traer):
    """Trae el .zip de una versión más nueva: (versión, ruta, sha256), o
    None si no la hay. SinRed, o ValueError si no llega lo anunciado."""
    os.makedirs(carpeta, exist_ok=True)
    respuesta = os.path.join(carpeta, "ultimo.json")
    traer(ULTIMO, respuesta)
    with open(respuesta, encoding="utf-8") as f:
        hay = mas_nueva(f.read(), actual)
    if not hay or saltar(hay[0]):
        shutil.rmtree(carpeta, ignore_errors=True)      # lo de la última vez
        return None
    version, url, suma = hay
    ruta = os.path.join(carpeta, archivo(version))
    if not (os.path.exists(ruta) and sha256(ruta) == suma):
        parte = ruta + ".part"
        traer(url, parte)
        if sha256(parte) != suma:
            os.remove(parte)
            raise ValueError(f"el archivo de {version} no tiene el SHA-256 anunciado")
        os.replace(parte, ruta)
    return version, ruta, suma


def preparar(ruta, suma):
    """Descomprime la versión nueva y devuelve su carpeta."""
    if sha256(ruta) != suma:            # puede llevar horas ahí
        raise ValueError("el archivo descargado ha cambiado")
    nueva = os.path.join(os.path.dirname(ruta), "nueva")
    shutil.rmtree(nueva, ignore_errors=True)
    with zipfile.ZipFile(ruta) as z:
        for n in z.namelist():
            if os.path.isabs(n) or ".." in n.replace("\\", "/").split("/") or ":" in n:
                raise ValueError(f"nombre sospechoso: {n}")
        z.extractall(nueva)
    return nueva


def ejecutar(ruta, suma, raiz=RAIZ):
    """Lanza la versión nueva, que cierra esta barra, se instala y se abre."""
    nueva = preparar(ruta, suma)
    # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP: no depende de esta barra
    return subprocess.Popen([os.path.join(nueva, "python", "pythonw.exe"), os.path.join(nueva, "barra", "instalado.py"),
                             "--actualizar", raiz], cwd=nueva, close_fds=True, creationflags=0x208,
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def hoy():
    return time.strftime("%Y-%m-%d")


def intentos(guardado, version):
    """Cuántas veces se probó hoy esa versión, según el texto de los ajustes."""
    p = str(guardado or "").split(":")
    return int(p[1]) if len(p) == 3 and p[::2] == [version, hoy()] and p[1].isdigit() else 0


def contar(guardado, version):
    """Ese texto, con un intento más."""
    return f"{version}:{intentos(guardado, version) + 1}:{hoy()}"
