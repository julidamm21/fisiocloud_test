#!/usr/bin/env python3
"""E2E: login → crear ticket de soporte."""
from __future__ import annotations

import sys
import unittest

from common import login, request, require_services, run_suite, url


class FlujoSoporteE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_services("seguridad", "soporte")

    def test_crear_ticket(self):
        """Login → abrir caso de soporte con mensaje."""
        token, usuario = login()
        self.assertNotEqual((usuario.get("rol") or "").upper(), "ADMIN")

        status, resp = request(
            "POST",
            url("soporte", "api/tickets/"),
            token=token,
            body={
                "asunto": "E2E soporte",
                "mensaje": "Ticket generado por prueba punta a punta",
            },
        )
        self.assertEqual(status, 201, resp)
        self.assertTrue(resp.get("ok"), resp)
        data = resp.get("data") or {}
        self.assertTrue(data.get("id") or data.get("numero"))


if __name__ == "__main__":
    sys.exit(run_suite(FlujoSoporteE2E, "RESUMEN E2E — soporte"))
