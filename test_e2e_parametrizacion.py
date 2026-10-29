#!/usr/bin/env python3
"""E2E: login → catálogos de parametrización."""
from __future__ import annotations

import sys
import time
import unittest

from common import login, request, require_services, run_suite, url


class FlujoParametrizacionE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_services("seguridad", "parametrizacion")

    def test_crud_tipo_documento(self):
        """Login → crear tipo documento → listar → soft-delete."""
        token, _ = login()
        codigo = f"T{int(time.time()) % 100000:05d}"[:10]

        status, created = request(
            "POST",
            url("parametrizacion", "api/tipos-documento/"),
            token=token,
            body={"codigo": codigo, "nombre": f"E2E {codigo}"},
        )
        self.assertEqual(status, 201, created)
        self.assertTrue(created.get("ok"), created)

        status, lista = request(
            "GET",
            url("parametrizacion", "api/tipos-documento/"),
            token=token,
        )
        self.assertEqual(status, 200, lista)
        codigos = [x.get("codigo") for x in (lista.get("data") or [])]
        self.assertIn(codigo, codigos)

        status, deleted = request(
            "DELETE",
            url("parametrizacion", f"api/tipos-documento/{codigo}/"),
            token=token,
        )
        self.assertEqual(status, 200, deleted)
        self.assertTrue(deleted.get("ok"), deleted)


if __name__ == "__main__":
    sys.exit(run_suite(FlujoParametrizacionE2E, "RESUMEN E2E — parametrización"))
