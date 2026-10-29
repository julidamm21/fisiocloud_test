#!/usr/bin/env python3
"""E2E: login → plan casero → token → portal /casa/."""
from __future__ import annotations

import sys
import time
import unittest

from common import BASE, login, request, require_services, run_suite, url


class FlujoTratamientoCasaE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_services("seguridad", "tratamiento-casa")

    def test_plan_token_y_casa(self):
        """Login → ejercicio/plan → token → GET público casa."""
        token, _ = login()

        status, ejers = request("GET", url("tratamiento-casa", "api/ejercicios/"), token=token)
        self.assertEqual(status, 200, ejers)
        ejercicios = [e for e in (ejers.get("data") or []) if e.get("activo") is not False]
        if not ejercicios:
            self.skipTest("No hay ejercicios activos en biblioteca (solo ADMIN puede crearlos)")
        ejercicio_id = ejercicios[0]["id"]

        status, plan = request(
            "POST",
            url("tratamiento-casa", "api/planes/"),
            token=token,
            body={
                "paciente_documento": f"c{int(time.time()) % 1000000}",
                "paciente_nombre": "Casa E2E",
                "titulo": "Plan E2E",
                "pasos": [{"ejercicio_id": ejercicio_id, "orden": 1}],
            },
        )
        self.assertEqual(status, 201, plan)
        plan_id = (plan.get("data") or {}).get("id")
        self.assertTrue(plan_id)

        status, tok = request(
            "POST",
            url("tratamiento-casa", f"api/planes/{plan_id}/token/"),
            token=token,
            body={"dias_vigencia": 2},
        )
        self.assertEqual(status, 201, tok)
        token_str = (tok.get("data") or {}).get("token")
        self.assertTrue(token_str)

        # Portal público (HTML) — vía nginx o puerto directo
        status_casa, _ = request("GET", f"{BASE}/svc/tratamiento-casa/casa/{token_str}/")
        self.assertEqual(status_casa, 200)


if __name__ == "__main__":
    sys.exit(run_suite(FlujoTratamientoCasaE2E, "RESUMEN E2E — tratamiento casa"))
