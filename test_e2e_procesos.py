#!/usr/bin/env python3
"""E2E: login → catálogo y preferencias de procesos automáticos."""
from __future__ import annotations

import sys
import unittest

from common import login, request, require_services, run_suite, url


class FlujoProcesosE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_services("seguridad", "procesos-automaticos")

    def test_catalogo_y_preferencias(self):
        """Catálogo público + preferencias autenticadas."""
        status, cat = request("GET", url("procesos-automaticos", "api/procesos/catalogo/"))
        self.assertEqual(status, 200, cat)
        self.assertTrue(cat.get("ok"), cat)
        self.assertTrue(cat.get("data"))

        token, _ = login()
        status, prefs = request(
            "GET",
            url("procesos-automaticos", "api/preferencias/me/"),
            token=token,
        )
        self.assertEqual(status, 200, prefs)
        self.assertTrue(prefs.get("ok"), prefs)
        procesos = (prefs.get("data") or {}).get("procesos") or []
        self.assertTrue(procesos)

        # Terapeuta no puede disparar jobs
        status, job = request(
            "POST",
            url("procesos-automaticos", "api/jobs/ejecutar/"),
            token=token,
            body={"proceso_codigo": "recordatorio_agenda"},
        )
        self.assertEqual(status, 403, job)


if __name__ == "__main__":
    sys.exit(run_suite(FlujoProcesosE2E, "RESUMEN E2E — procesos automáticos"))
