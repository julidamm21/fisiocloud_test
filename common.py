"""Helpers compartidos para pruebas E2E HTTP vía nginx /svc/."""
from __future__ import annotations

import json
import os
import unittest
import urllib.error
import urllib.request
from typing import Any
from unittest.runner import TextTestResult, TextTestRunner


BASE = os.environ.get("E2E_BASE_URL", "http://127.0.0.1").rstrip("/")
EMAIL = os.environ.get("E2E_EMAIL", "juan@test.com")
PASSWORD = os.environ.get("E2E_PASSWORD", "Terapeuta@123456")


def url(svc: str, path: str) -> str:
    path = path.lstrip("/")
    return f"{BASE}/svc/{svc}/{path}"


def request(
    method: str,
    full_url: str,
    *,
    token: str | None = None,
    body: dict | None = None,
    timeout: float = 20.0,
) -> tuple[int, dict[str, Any]]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(full_url, data=data, headers=headers, method=method)
    def _parse(raw: str) -> dict[str, Any]:
        text = (raw or "").strip()
        if not text:
            return {}
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return {"_raw": text[:500], "ok": True}
        if isinstance(payload, dict):
            return payload
        return {"data": payload}

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, _parse(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        payload = _parse(raw)
        if "error" not in payload and "_raw" in payload:
            payload["error"] = payload["_raw"][:300]
            payload["ok"] = False
        return exc.code, payload
    except Exception as exc:
        return 0, {"ok": False, "error": f"No se pudo conectar a {full_url}: {exc}"}


def login(email: str = EMAIL, password: str = PASSWORD) -> tuple[str, dict]:
    status, payload = request(
        "POST",
        url("seguridad", "api/auth/login/"),
        body={"email": email, "password": password},
    )
    if status != 200 or not payload.get("ok"):
        raise AssertionError(f"Login falló ({status}): {payload}")
    data = payload.get("data") or {}
    token = data.get("access_token") or ""
    if not token:
        raise AssertionError(f"Login sin access_token: {payload}")
    return token, data.get("usuario") or {}


def require_services(*svcs: str) -> None:
    for svc in svcs:
        status, payload = request("GET", url(svc, "api/health/"))
        if status != 200 or not payload.get("ok"):
            raise unittest.SkipTest(
                f"Servicio {svc} no disponible en {BASE} (health={status}). "
                "Levante nginx + microservicios antes del E2E."
            )


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


def imprimir_resumen(result: ResumenResult, titulo: str = "RESUMEN E2E") -> int:
    historial = getattr(result, "historial", [])
    ok_n = sum(1 for e, *_ in historial if e == "OK")
    fail_n = sum(1 for e, *_ in historial if e == "FAIL")
    err_n = sum(1 for e, *_ in historial if e == "ERROR")
    skip_n = sum(1 for e, *_ in historial if e == "SKIP")
    total = len(historial)
    marcas = {"OK": "[OK]   ", "FAIL": "[FAIL] ", "ERROR": "[ERROR]", "SKIP": "[SKIP] "}
    print("")
    print("=" * 60)
    print(f" {titulo}")
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


def run_suite(test_case_cls, titulo: str) -> int:
    print(f"E2E base={BASE} email={EMAIL}")
    suite = unittest.TestLoader().loadTestsFromTestCase(test_case_cls)
    runner = TextTestRunner(verbosity=2, resultclass=ResumenResult)
    result = runner.run(suite)
    return imprimir_resumen(result, titulo)  # type: ignore[arg-type]
