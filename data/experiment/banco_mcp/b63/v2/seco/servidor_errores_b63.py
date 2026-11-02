#!/usr/bin/env python3
"""servidor_errores_b63.py — El servidor local de la medición de las formas del error de B6.3 (etapa b1; decisión de la autora del
26/10/2026, la opción (d)): un servidor HTTP en 127.0.0.1, en un puerto libre que elige el sistema, que contesta a todo pedido con el
error de su ruta, con el cuerpo de error de la API:
  /c429/...  429 rate_limit_error, con `retry-after: 1`;
  /c500/...  500 api_error;
  /c529/...  529 overloaded_error.
Cuenta los pedidos que recibe, por ruta y por método, que es lo que mide si el CLI reintenta solo. No guarda ni imprime el cuerpo ni
los encabezados de ningún pedido: compara en memoria la clave del pedido (`x-api-key`) con la que se le pasa y cuenta, por método,
cuántos la traen.
Uso como módulo (lo levanta formas_error_b63.py en un hilo): s = ServidorErrores(clave); s.url("429"); s.cuentas(); s.cerrar().
"""
from __future__ import annotations

import json
import threading
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ERRORES = {"429": (429, "rate_limit_error", "Rate limit de prueba (servidor local de B6.3)"),
           "500": (500, "api_error", "Error interno de prueba (servidor local de B6.3)"),
           "529": (529, "overloaded_error", "Sobrecarga de prueba (servidor local de B6.3)")}


class ServidorErrores:
    def __init__(self, clave: str):
        self._clave = clave
        self._cuentas: Counter = Counter()
        self._lock = threading.Lock()
        dueno = self

        class Manejador(BaseHTTPRequestHandler):
            def _contestar(self):
                largo = int(self.headers.get("content-length") or 0)
                if largo:
                    self.rfile.read(largo)                       # se lee y se descarta: no se guarda
                partes = self.path.strip("/").split("/", 1)
                caso = partes[0][1:] if partes and partes[0].startswith("c") else ""
                ruta = "/" + (partes[1] if len(partes) > 1 else "")
                con_clave = self.headers.get("x-api-key") == dueno._clave
                with dueno._lock:
                    dueno._cuentas[(caso, self.command, ruta.split("?")[0])] += 1
                    dueno._cuentas[(caso, f"{self.command}:" + ("clave_inválida_del_pedido" if con_clave else "otra_clave_o_ninguna"),
                                    "")] += 1
                codigo, tipo, msg = ERRORES.get(caso, (404, "not_found_error", "ruta desconocida"))
                cuerpo = json.dumps({"type": "error", "error": {"type": tipo, "message": msg}}).encode()
                self.send_response(codigo)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(cuerpo)))
                if codigo == 429:
                    self.send_header("retry-after", "1")
                self.end_headers()
                self.wfile.write(cuerpo)

            do_POST = do_GET = do_HEAD = _contestar                # noqa: N815

            def log_message(self, *a):                           # sin registro de pedidos
                return

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
        self.puerto = self.srv.server_address[1]
        self.hilo = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.hilo.start()

    def url(self, caso: str) -> str:
        return f"http://127.0.0.1:{self.puerto}/c{caso}"

    def cuentas(self) -> dict:
        with self._lock:
            return {f"{c}|{m}|{r}": n for (c, m, r), n in sorted(self._cuentas.items())}

    def cerrar(self) -> None:
        self.srv.shutdown()
        self.srv.server_close()
