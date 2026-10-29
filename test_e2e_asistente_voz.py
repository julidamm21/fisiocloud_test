#!/usr/bin/env python3
"""E2E: login → gating asistente de voz (feature / sesión)."""
from __future__ import annotations

import sys
import unittest

from common import login, request, require_services, run_suite, url


class FlujoAsistenteVozE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_services("seguridad", "asistente-voz", "suscripcion")

    def test_sesion_requiere_feature_o_crea(self):
        """Login → crear sesión: OK si hay feature, 403 si no."""
        token, _ = login()
        status, feats = request(
            "GET",
            url("suscripcion", "api/subscriptions/me/features/"),
            token=token,
        )
        self.assertEqual(status, 200, feats)
        data = feats.get("data") or {}
        items = data.get("features") if isinstance(data, dict) else data
        if isinstance(items, list):
            codigos = {str(x.get("codigo") if isinstance(x, dict) else x) for x in items}
        else:
            codigos = set()

        status, resp = request(
            "POST",
            url("asistente-voz", "api/sesiones/"),
            token=token,
            body={
                "paciente_documento": "e2evoz001",
                "paciente_nombre": "Voz E2E",
                "proposito": "VALORACION",
                "tipo_valoracion": "FISIO",
            },
        )
        if "asistente_voz" in codigos:
            self.assertIn(status, (200, 201), resp)
            self.assertTrue(resp.get("ok"), resp)
        else:
            self.assertEqual(status, 403, resp)
            self.assertFalse(resp.get("ok"))


if __name__ == "__main__":
    sys.exit(run_suite(FlujoAsistenteVozE2E, "RESUMEN E2E — asistente de voz"))
