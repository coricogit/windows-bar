"""Lo que suena ahora (Spotify, navegador...), por la sesión multimedia de Windows.

Usa los paquetes winrt-*; si no están, la barra funciona sin este módulo.
"""
import asyncio
import os
import sys
import threading

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
try:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as Manager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status)
except ImportError:
    Manager = None

NADA = {"titulo": "", "artista": "", "sonando": False}


class Musica:
    def __init__(self, avisar):
        """`avisar(dict)` se llama desde otro hilo cuando algo cambia."""
        self.avisar = avisar
        self.pausada = False         # modo juego: no consulta
        self._ultimo = None
        self._loop = None
        if Manager:
            threading.Thread(target=self._hilo, daemon=True).start()

    def _hilo(self):
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self._seguir())

    async def _seguir(self):
        manager = None
        while True:
            if not self.pausada:
                try:
                    manager = manager or await Manager.request_async()
                    datos = await self._leer(manager)
                except Exception:        # la sesión se cerró a mitad de la consulta
                    manager, datos = None, dict(NADA)
                if datos != self._ultimo:
                    self._ultimo = datos
                    self.avisar(datos)
            await asyncio.sleep(1.5)

    async def _leer(self, manager):
        s = manager.get_current_session()
        if not s:
            return dict(NADA)
        p = await s.try_get_media_properties_async()
        return {"titulo": p.title or "", "artista": p.artist or "",
                "sonando": s.get_playback_info().playback_status == Status.PLAYING}

    def orden(self, nombre):
        """"pausa", "siguiente" o "anterior"."""
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._orden(nombre), self._loop)

    async def _orden(self, nombre):
        s = (await Manager.request_async()).get_current_session()
        if s:
            await {"pausa": s.try_toggle_play_pause_async, "siguiente": s.try_skip_next_async,
                   "anterior": s.try_skip_previous_async}[nombre]()
