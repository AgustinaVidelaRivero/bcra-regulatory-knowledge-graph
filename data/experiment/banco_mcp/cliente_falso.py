#!/usr/bin/env python3
"""cliente_falso.py — Cliente MCP de prueba (stdio) para los servidores del banco.

Lanza un servidor como subproceso (igual que lo hace Claude Code: stdio,
JSON-RPC), negocia la inicialización, lista tools y ejecuta llamadas. Sirve a
los tests de paridad (mcp_kg), a los tests del vectorial, a la medición del
tope de tamaño de resultado y al selftest integrador. No usa ningún modelo:
costo USD 0.

Uso como módulo:
    with ClienteFalso(cmd=[python, servidor, "--config", cfg], env=...) as c:
        tools = c.listar_tools()
        texto = c.llamar("buscar_nodos", {"consulta": "x"})   # str íntegro
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import os
import threading
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class ClienteFalso:
    """Envoltura síncrona sobre ClientSession del SDK. Un único hilo corre UNA
    corrutina que entra en los context managers (stdio + sesión) y atiende
    pedidos por cola: anyio exige que los cancel scopes se abran y cierren en
    la misma tarea."""

    def __init__(self, cmd: list[str], env: dict | None = None, cwd: Path | None = None,
                 timeout_s: float = 600.0):
        self.params = StdioServerParameters(command=cmd[0], args=cmd[1:],
                                            env={**os.environ, **(env or {})},
                                            cwd=str(cwd) if cwd else None)
        self.timeout_s = timeout_s
        self._loop = asyncio.new_event_loop()
        self._hilo = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._hilo.start()
        self._cola = None
        self._listo = threading.Event()
        self._error_inicio = None
        self.init_result = None

    async def _driver(self):
        self._cola = asyncio.Queue()
        fut_cierre = None
        try:
            async with stdio_client(self.params) as (r, w):
                async with ClientSession(r, w) as session:
                    self.init_result = await session.initialize()
                    self._listo.set()
                    while True:
                        fn, fut = await self._cola.get()
                        if fn is None:
                            fut_cierre = fut
                            break
                        try:
                            fut.set_result(await fn(session))
                        except Exception as e:  # se propaga al hilo llamador
                            fut.set_exception(e)
            # Acá el SDK ya cerró stdin y esperó la salida del subproceso: el
            # servidor terminó de escribir su log (línea `fin`) antes de que
            # el llamador siga.
            if fut_cierre is not None:
                fut_cierre.set_result(None)
        except Exception as e:
            self._error_inicio = e
            self._listo.set()
            if fut_cierre is not None:
                fut_cierre.set_exception(e)

    def _pedir(self, fn):
        fut = concurrent.futures.Future()
        self._loop.call_soon_threadsafe(self._cola.put_nowait, (fn, fut))
        return fut.result(self.timeout_s)

    def __enter__(self):
        asyncio.run_coroutine_threadsafe(self._driver(), self._loop)
        self._listo.wait(self.timeout_s)
        if self._error_inicio is not None:
            raise self._error_inicio
        return self

    def __exit__(self, *exc):
        try:
            self._pedir(None)
        finally:
            # dejar que el loop recoja los transportes del subproceso antes de
            # detenerse (evita el "Event loop is closed" del GC de asyncio)
            asyncio.run_coroutine_threadsafe(asyncio.sleep(0.3), self._loop).result(5)
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._hilo.join(timeout=10)
            self._loop.close()

    def listar_tools(self) -> list[dict]:
        res = self._pedir(lambda s: s.list_tools())
        return [{"name": t.name, "description": t.description, "input_schema": t.inputSchema}
                for t in res.tools]

    def llamar_crudo(self, name: str, arguments: dict):
        return self._pedir(lambda s: s.call_tool(name, arguments))

    def llamar(self, name: str, arguments: dict) -> str:
        """Texto íntegro que recibiría el modelo (concatenación de bloques de texto)."""
        res = self.llamar_crudo(name, arguments)
        if res.isError:
            raise RuntimeError("tool error: " + "".join(
                getattr(c, "text", "") for c in res.content))
        return "".join(c.text for c in res.content if getattr(c, "type", None) == "text")
