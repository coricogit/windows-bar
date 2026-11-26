"""Conectar Claude Code con el Claudito que trae la barra.

Sin el Claudito completo instalado, nadie avisa a la barra de lo que hace Claude
Code ni de los límites del plan. Esto añade a su settings.json los mismos avisos y
la misma línea de estado que pondría Claudito, con una copia de seguridad, y solo
si se pide en el menú. Usa el install.py del propio Claudito.
"""
import contextlib
import importlib.util
import io
import os

from . import claudito


def carpeta():
    """La de Claude Code, exista o no."""
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def hay_claude_code():
    return os.path.isdir(carpeta())


def _instalador(raiz=claudito.INCLUIDO):
    spec = importlib.util.spec_from_file_location("claudito_install", os.path.join(raiz, "windows", "install.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _nuestro(orden, raiz):
    def norma(x):
        return x.replace("\\", "/").lower()
    return norma(raiz) in norma(orden or "")


def _callado():
    """El instalador de Claudito cuenta lo que hace por consola; la barra no tiene consola."""
    return contextlib.redirect_stdout(io.StringIO())


def estado(raiz=claudito.INCLUIDO):
    """{"avisos": "no" | "nuestra" | "otra", "linea": "no" | "claudito" | "ajena"}.
    "otra": los de un Claudito instalado aparte, que no se tocan."""
    try:
        m = _instalador(raiz)
        d = m.load_settings(m.settings_path())
    except (OSError, SystemExit):
        return {"avisos": "otra", "linea": "ajena"}        # mejor no tocar nada
    ordenes = [h.get("command") for grupos in (d.get("hooks") or {}).values() for g in grupos or []
               for h in g.get("hooks", [])] if isinstance(d.get("hooks"), dict) else []
    suyas = [o for o in ordenes if m.is_ours(o, m.OURS_HOOK)]
    linea = (d.get("statusLine") or {}).get("command", "")
    return {"avisos": "no" if not suyas else "nuestra" if all(_nuestro(o, raiz) for o in suyas) else "otra",
            "linea": "no" if not linea else "claudito" if m.is_ours(linea, m.OURS_STATUS) else "ajena"}


def conectar(raiz=claudito.INCLUIDO):
    """Devuelve "" si fue bien, o por qué no."""
    if estado(raiz)["avisos"] == "otra":
        return "Claude Code ya está conectado con otro Claudito, o su settings.json no se puede leer."
    try:
        m = _instalador(raiz)
        with _callado():
            m.install_settings(m.settings_path())
        return ""
    except (OSError, SystemExit, TypeError, AttributeError) as e:
        return str(e)


def desconectar(raiz=claudito.INCLUIDO):
    if estado(raiz)["avisos"] != "nuestra":
        return
    try:
        m = _instalador(raiz)
        with _callado():
            m.uninstall_settings(m.settings_path())
    except (OSError, SystemExit, TypeError, AttributeError):
        pass
