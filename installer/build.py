"""Crea el instalador.

    py installer\\build.py      ->  installer\\dist\\Windows-Bar-Setup-<versión>.exe

Necesita Python 3.9 o posterior con pip, e internet la primera vez. No instala
nada: Python, Qt e Inno Setup se descargan en installer\\build, se comprueban con
los hashes de abajo y se usan desde ahí.

Para publicarlo, y que las copias instaladas se actualicen solas a él, la
etiqueta tiene que ser v<versión> y el archivo conservar su nombre:

    gh release create v<versión> installer\\dist\\Windows-Bar-Setup-<versión>.exe
"""
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
BUILD = os.path.join(AQUI, "build")
STAGE = os.path.join(BUILD, "stage")
DIST = os.path.join(AQUI, "dist")

PYTHON = ("https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip",
          "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3")
INNO = ("https://api.nuget.org/v3-flatcontainer/tools.innosetup/6.7.3/tools.innosetup.6.7.3.nupkg",
        "f780898e402ff80612cc8d9fcb8c6e02932bd1cb4c900ffdaa31f9341cfb49f4")
QT = (("PySide6_Essentials==6.12.0", "c9a95102aa23c1f86516a30d5a9be37552d324eee7e567eb7508973f1218cb42"),
      ("shiboken6==6.12.0", "a1906cb8116869178c64b6bab52623bbc8b4ceed7b30bfc3c9aa0f6e67f6438e"))
MUSICA = (("winrt-runtime==4.2.1", "c4c82b8aace86435f833059d583679e5dfb55260328609ddb8a8ba26bd79036c"),
          ("winrt-Windows.Media.Control==4!10.0.28000.2957", "5d010ccf64e39040b0550c7b8f6cf8015e558542bd3887cc424f32096e61410e"),
          ("winrt-Windows.Foundation==4!10.0.28000.2957", "0669de7ce480806a0f9a46d005837799e37f1738911b54c4bc04788b37974e69"),
          ("winrt-Windows.Foundation.Collections==4!10.0.28000.2957",
           "0401c1b6ed512d1fdad8ba1571698e9000ebee6a69781db9a01994ffcc54a503"),
          ("winrt-Windows.Storage.Streams==4!10.0.28000.2957",
           "e113832320f2e7f8b09cedfb400cb7eaf0ac769ad1f2038ddbe88801497916c4"),
          ("typing_extensions==4.16.0", "481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8"))

# Lo que entra del repositorio (de git, para que no se cuele nada más).
FUENTES = ("LICENSE", "README.md", "barra.pyw", "barra", "qml", "temas")

# Lo que entra de PySide6.
QT_MODULOS = ("Core", "Gui", "Network", "OpenGL", "Qml", "Quick", "QuickControls2", "Widgets")
QT_DLL = ("Core", "Gui", "Network", "OpenGL", "Qml", "QmlMeta", "QmlModels", "QmlWorkerScript", "Quick",
          "QuickControls2", "QuickControls2Basic", "QuickControls2BasicStyleImpl", "QuickControls2Fusion",
          "QuickControls2FusionStyleImpl", "QuickControls2Impl", "QuickLayouts", "QuickTemplates2", "Widgets")
QT_PLUGINS = ("platforms/qwindows.dll", "styles/qmodernwindowsstyle.dll", "imageformats/qjpeg.dll",
              "imageformats/qgif.dll", "imageformats/qwebp.dll")       # para leer el fondo de escritorio
QT_QML = ("QtQml", "QtQuick/Window", "QtQuick/Layouts", "QtQuick/Templates", "QtQuick/Controls/impl",
          "QtQuick/Controls/Basic", "QtQuick/Controls/Fusion")
QT_QML_SUELTO = ("", "QtQuick", "QtQuick/Controls")   # solo sus archivos directos


def decir(texto):
    print("==>", texto, flush=True)


def traer(url, sha256):
    os.makedirs(BUILD, exist_ok=True)
    ruta = os.path.join(BUILD, url.rsplit("/", 1)[1])
    if not os.path.exists(ruta):
        decir("Descargando " + url)
        with urllib.request.urlopen(url, timeout=120) as r, open(ruta + ".part", "wb") as f:
            shutil.copyfileobj(r, f)
        os.replace(ruta + ".part", ruta)
    with open(ruta, "rb") as f:
        suma = hashlib.sha256(f.read()).hexdigest()
    if suma != sha256:
        sys.exit(f"{ruta}: hash incorrecto {suma}")
    return ruta


def vacia(ruta):
    shutil.rmtree(ruta, ignore_errors=True)
    os.makedirs(ruta)
    return ruta


def descomprimir(ruta, destino):
    with zipfile.ZipFile(ruta) as z:
        z.extractall(vacia(destino))
    return destino


def copiar(de, a):
    os.makedirs(os.path.dirname(a), exist_ok=True)
    shutil.copy2(de, a)


def paquetes(lista, destino):
    reqs = os.path.join(BUILD, "requisitos.txt")
    with open(reqs, "w", encoding="ascii") as f:
        f.writelines(f"{nombre} --hash=sha256:{sha}\n" for nombre, sha in lista)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check", "--no-compile",
                    "--no-deps", "--only-binary", ":all:", "--platform", "win_amd64", "--python-version", "3.12",
                    "--require-hashes", "--target", vacia(destino), "-r", reqs], check=True)
    return destino


def poner_fuentes():
    lista = subprocess.run(["git", "-C", RAIZ, "ls-files", "-z", "--", *FUENTES],
                           capture_output=True, check=True).stdout.decode().split("\0")
    for n in filter(None, lista):
        copiar(os.path.join(RAIZ, n), os.path.join(STAGE, n))
    for n in os.listdir(os.path.join(AQUI, "licenses")):
        copiar(os.path.join(AQUI, "licenses", n), os.path.join(STAGE, "licenses", n))
    copiar(os.path.join(AQUI, "version.txt"), os.path.join(STAGE, "version.txt"))


def poner_python():
    python = descomprimir(traer(*PYTHON), os.path.join(STAGE, "python"))
    with open(os.path.join(python, "python312._pth"), "w", encoding="ascii") as f:
        f.write("python312.zip\n.\nLib\\site-packages\n")
    return python


def poner_qt(python):
    decir("PySide6")
    todo = paquetes(QT, os.path.join(BUILD, "qt"))
    sitio = os.path.join(python, "Lib", "site-packages")
    for carpeta in ("shiboken6", "PySide6"):
        de = os.path.join(todo, carpeta)
        for n in os.listdir(de):
            ruta, min_ = os.path.join(de, n), n.lower()
            if not os.path.isfile(ruta) or n.endswith((".pyi", ".exe", ".lib")):
                continue
            if (carpeta == "shiboken6" or n.endswith(".py") or min_.startswith(("msvcp140", "vcruntime140"))
                    or n in ("pyside6.abi3.dll", "pyside6qml.abi3.dll")
                    or n in {f"Qt{m}.pyd" for m in QT_MODULOS} or n in {f"Qt6{m}.dll" for m in QT_DLL}):
                copiar(ruta, os.path.join(sitio, carpeta, n))
    de, a = os.path.join(todo, "PySide6"), os.path.join(sitio, "PySide6")
    for n in QT_PLUGINS:
        copiar(os.path.join(de, "plugins", n), os.path.join(a, "plugins", n))
    for n in QT_QML:
        shutil.copytree(os.path.join(de, "qml", n), os.path.join(a, "qml", n), dirs_exist_ok=True)
    for carpeta in QT_QML_SUELTO:
        for n in os.listdir(os.path.join(de, "qml", carpeta)):
            if os.path.isfile(os.path.join(de, "qml", carpeta, n)):
                copiar(os.path.join(de, "qml", carpeta, n), os.path.join(a, "qml", carpeta, n))
    for m in (*(f"Qt{m}.pyd" for m in QT_MODULOS), *(f"Qt6{m}.dll" for m in QT_DLL)):
        if not os.path.exists(os.path.join(a, m)):
            sys.exit("PySide6 no trae " + m)


def main():
    with open(os.path.join(AQUI, "version.txt"), encoding="ascii") as f:
        version = f.read().strip()
    decir("Windows Bar " + version)
    vacia(STAGE)
    poner_fuentes()
    python = poner_python()
    poner_qt(python)
    decir("Música")
    paquetes(MUSICA, os.path.join(STAGE, "lib"))
    decir("Icono")
    # Con el mismo Python que se entrega; -B, que no deje compilados.
    subprocess.run([os.path.join(python, "python.exe"), "-B", os.path.join(AQUI, "icono.py"),
                    os.path.join(STAGE, "windows-bar.ico")], check=True)
    for carpeta, _, _ in list(os.walk(STAGE)):
        if os.path.basename(carpeta) == "__pycache__":
            shutil.rmtree(carpeta)
    inno = descomprimir(traer(*INNO), os.path.join(BUILD, "inno"))
    decir("Inno Setup")
    os.makedirs(DIST, exist_ok=True)
    subprocess.run([os.path.join(inno, "tools", "ISCC.exe"), "/Qp", f"/DVersion={version}", f"/DStage={STAGE}",
                    f"/DOut={DIST}", os.path.join(AQUI, "windows-bar.iss")], check=True)
    exe = os.path.join(DIST, f"Windows-Bar-Setup-{version}.exe")
    with open(exe, "rb") as f:
        datos = f.read()
    decir(f"{exe}\n    {len(datos) / 1e6:.1f} MB, SHA-256 {hashlib.sha256(datos).hexdigest()}")


if __name__ == "__main__":
    main()
