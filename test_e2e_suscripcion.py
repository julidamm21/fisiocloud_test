#!/usr/bin/env python3
"""E2E: login → listar planes → checkout → webhook → features."""
from __future__ import annotations

import sys
import unittest

from common import login, request, require_services, run_suite, url


class FlujoSuscripcionE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_services("seguridad", "suscripcion")

    def test_flujo_checkout_y_webhook(self):
        """Login → plan activo → checkout → pago simulado → features."""
        token, usuario = login()
        doc = usuario.get("doc_usuario")
        self.assertTrue(doc)

        status, plans = request("GET", url("suscripcion", "api/plans/"))
        self.assertEqual(status, 200, plans)
        activos = [p for p in (plans.get("data") or []) if p.get("activo")]
        self.assertTrue(activos, "No hay planes activos")
        plan_codigo = activos[0]["codigo"]

        status, checkout = request(
            "POST",
            url("suscripcion", "api/checkout/"),
            token=token,
            body={"plan_codigo": plan_codigo, "segmento": "GENERAL"},
        )
        self.assertEqual(status, 201, checkout)
        data = checkout.get("data") or {}
        pago = data.get("pago") or {}
        payment_id = pago.get("pasarela_payment_id") or pago.get("payment_id")
        self.assertTrue(payment_id, checkout)
        self.assertTrue(data.get("checkout_url"))

        status, wh = request(
            "POST",
            url("suscripcion", "api/payments/webhook/"),
            body={"payment_id": payment_id, "resultado": "success"},
        )
        self.assertEqual(status, 200, wh)
        self.assertTrue(wh.get("ok"), wh)
        sus = (wh.get("data") or {}).get("suscripcion") or {}
        self.assertEqual(sus.get("estado"), "ACTIVA")

        status, feats = request(
            "GET",
            url("suscripcion", "api/subscriptions/me/features/"),
            token=token,
        )
        self.assertEqual(status, 200, feats)
        self.assertTrue(feats.get("ok"), feats)


if __name__ == "__main__":
    sys.exit(run_suite(FlujoSuscripcionE2E, "RESUMEN E2E — suscripción"))
