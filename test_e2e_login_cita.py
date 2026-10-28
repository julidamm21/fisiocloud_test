#!/usr/bin/env python3
"""
E2E: login (seguridad) → paciente (info-medica) → crear cita (agendamiento).

Requiere los microservicios y nginx levantados.

Ejecutar dentro del contenedor:
  python3 /app/test/test_e2e_login_cita.py

Desde el host (puerto mapeado, ej. 8089):
  E2E_BASE_URL=http://127.0.0.1:8089 python3 app/test/test_e2e_login_cita.py

Variables opcionales:
  E2E_BASE_URL   (default http://127.0.0.1)
  E2E_EMAIL      (default juan@test.com)
  E2E_PASSWORD   (default Terapeuta@123456)
"""
from __future__ import annotations

import json
import os
import sys
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from typing import Any
from unittest.runner import TextTestResult, TextTestRunner


BASE = os.environ.get("E2E_BASE_URL", "http://127.0.0.1").rstrip("/")
EMAIL = os.environ.get("E2E_EMAIL", "juan@test.com")
PASSWORD = os.environ.get("E2E_PASSWORD", "Terapeuta@123456")

URL_LOGIN = f"{BASE}/svc/seguridad/api/auth/login/"
URL_ME = f"{BASE}/svc/seguridad/api/auth/me/"
URL_PACIENTES = f"{BASE}/svc/info-medica/api/pacientes/"
URL_TIPOS = f"{BASE}/svc/agendamiento/api/tipos-terapia/"
URL_CITAS = f"{BASE}/svc/agendamiento/api/citas/"


def _request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    body: dict | None = None,
    timeout: float = 15.0,
) -> tuple[int, dict[str, Any]]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8") or "{}"
            payload = json.loads(raw) if raw.strip() else {}
            if not isinstance(payload, dict):
                payload = {"data": payload}
            return resp.status, payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") or "{}"
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            payload = {"error": raw[:300]}
        if not isinstance(payload, dict):
            payload = {"data": payload}
        return exc.code, payload
    except Exception as exc:
        return 0, {"ok": False, "error": f"No se pudo conectar a {url}: {exc}"}


class ResumenResult(TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.historial: list[tuple[str, str, str, str]] = []

    def _desc(self, test) -> tuple[str, str]:
        nombre = getattr(test, "_testMethodName", str(test))
        method = getattr(test, nombre, None)
        doc = (getattr(method, "__doc__", None) or "").strip()
        desc = doc.splitlines()[0].strip() if doc else nombre
        return nombre, desc

    def addSuccess(self, test):
        super().addSuccess(test)
        n, d = self._desc(test)
        self.historial.append(("OK", n, d, ""))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        n, d = self._desc(test)
        msg = self._exc_info_to_string(err, test).strip().splitlines()[-1]
        self.historial.append(("FAIL", n, d, msg))

    def addError(self, test, err):
        super().addError(test, err)
        n, d = self._desc(test)
        msg = self._exc_info_to_string(err, test).strip().splitlines()[-1]
        self.historial.append(("ERROR", n, d, msg))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        n, d = self._desc(test)
        self.historial.append(("SKIP", n, d, reason or ""))


def _imprimir_resumen(result: ResumenResult) -> int:
    historial = getattr(result, "historial", [])
    ok_n = sum(1 for e, *_ in historial if e == "OK")
    fail_n = sum(1 for e, *_ in historial if e == "FAIL")
    err_n = sum(1 for e, *_ in historial if e == "ERROR")
    skip_n = sum(1 for e, *_ in historial if e == "SKIP")
    total = len(historial)
    marcas = {
        "OK": "[OK]   ",
        "FAIL": "[FAIL] ",
        "ERROR": "[ERROR]",
        "SKIP": "[SKIP] ",
    }
    print("")
    print("=" * 60)
    print(" RESUMEN E2E — login → crear cita")
    print("=" * 60)
    print(f"  Base: {BASE}")
    for estado, nombre, desc, detalle in historial:
        print(f"  {marcas.get(estado, '[?]    ')} {nombre}")
        print(f"           {desc}")
        if detalle:
            print(f"           → {detalle}")
    print("-" * 60)
    print(f"  Total:    {total}")
    print(f"  OK:       {ok_n}")
    print(f"  Falló:    {fail_n}")
    print(f"  Errores:  {err_n}")
    print(f"  Omitidos: {skip_n}")
    print("=" * 60)
    if fail_n or err_n:
        print("  Resultado final: FALLIDO")
        code = 1
    else:
        print("  Resultado final: EXITOSO")
        code = 0
    print("=" * 60)
    print("")
    return code


class FlujoLoginCrearCitaE2E(unittest.TestCase):
    """Punta a punta entre seguridad, info-medica y agendamiento."""

    token: str = ""
    doc_usuario: str = ""
    paciente_doc: str = ""
    cita_id: int | None = None

    @classmethod
    def setUpClass(cls):
        status, payload = _request("GET", f"{BASE}/svc/seguridad/api/health/")
        if status != 200 or not payload.get("ok"):
            raise unittest.SkipTest(
                f"Servicios no disponibles en {BASE} (seguridad health={status}). "
                "Levante nginx + microservicios antes de correr el E2E."
            )

    def tearDown(self):
        if self.cita_id and self.token:
            _request("DELETE", f"{URL_CITAS}{self.cita_id}/", token=self.token)
            self.cita_id = None

    def test_01_login_credenciales_invalidas(self):
        """Login debe fallar con contraseña incorrecta."""
        status, payload = _request(
            "POST",
            URL_LOGIN,
            body={"email": EMAIL, "password": "clave-incorrecta-xyz"},
        )
        self.assertEqual(status, 401, payload)
        self.assertFalse(payload.get("ok"))
        self.assertIn("contraseña", (payload.get("error") or "").lower())

    def test_02_flujo_login_paciente_y_cita(self):
        """Login JWT → registrar paciente → crear cita de valoración."""
        # 1) Login
        status, payload = _request(
            "POST",
            URL_LOGIN,
            body={"email": EMAIL, "password": PASSWORD},
        )
        self.assertEqual(status, 200, payload)
        self.assertTrue(payload.get("ok"), payload)
        data = payload.get("data") or {}
        token = data.get("access_token") or ""
        self.assertTrue(token, "No llegó access_token")
        usuario = data.get("usuario") or {}
        self.doc_usuario = str(usuario.get("doc_usuario") or "")
        self.assertTrue(self.doc_usuario)
        self.token = token

        # 2) /me confirma el mismo JWT
        status, me = _request("GET", URL_ME, token=token)
        self.assertEqual(status, 200, me)
        self.assertTrue(me.get("ok"), me)
        self.assertEqual((me.get("data") or {}).get("doc_usuario"), self.doc_usuario)

        # 3) Tipo de terapia activo
        status, tipos = _request("GET", URL_TIPOS, token=token)
        self.assertEqual(status, 200, tipos)
        self.assertTrue(tipos.get("ok"), tipos)
        activos = [t for t in (tipos.get("data") or []) if t.get("activo")]
        self.assertTrue(activos, "No hay tipos de terapia activos")
        tipo_id = activos[0]["id"]

        # 4) Paciente (documento único por corrida)
        self.paciente_doc = f"e2e{int(time.time()) % 1_000_000:06d}"
        status, pac = _request(
            "POST",
            URL_PACIENTES,
            token=token,
            body={
                "documento": self.paciente_doc,
                "tipo_documento": "CC",
                "nombres": "Paciente E2E",
                "primer_apellido": "Prueba",
                "sexo": "M",
                "fecha_nacimiento": "1990-05-05",
            },
        )
        self.assertEqual(status, 201, pac)
        self.assertTrue(pac.get("ok"), pac)
        self.assertEqual((pac.get("data") or {}).get("documento"), self.paciente_doc)

        # 5) Crear cita
        inicio = (datetime.now() + timedelta(days=3)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        status, cita = _request(
            "POST",
            URL_CITAS,
            token=token,
            body={
                "documento_paciente": self.paciente_doc,
                "tipo_terapia": tipo_id,
                "proposito": "VALORACION",
                "inicio_cita": inicio.isoformat(),
            },
        )
        self.assertEqual(status, 201, cita)
        self.assertTrue(cita.get("ok"), cita)
        self.assertEqual(cita.get("message"), "Cita creada")
        cita_data = cita.get("data") or {}
        self.cita_id = cita_data.get("id")
        self.assertTrue(self.cita_id)
        self.assertEqual(cita_data.get("documento_paciente"), self.paciente_doc)
        self.assertEqual(cita_data.get("creado_por"), self.doc_usuario)
        self.assertEqual(cita_data.get("proposito"), "VALORACION")
        self.assertEqual(cita_data.get("primera_vez"), "S")
        self.assertEqual(cita_data.get("estado"), "P")


def main() -> int:
    print(f"E2E base={BASE} email={EMAIL}")
    loader = unittest.TestLoader()
    # Orden por nombre: test_01_…, test_02_…
    suite = loader.loadTestsFromTestCase(FlujoLoginCrearCitaE2E)
    runner = TextTestRunner(verbosity=2, resultclass=ResumenResult)
    result = runner.run(suite)
    return _imprimir_resumen(result)  # type: ignore[arg-type]


if __name__ == "__main__":
    sys.exit(main())
