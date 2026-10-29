#!/usr/bin/env python3
"""E2E: login (seguridad) → paciente (info-medica) → crear cita (agendamiento)."""
from __future__ import annotations

import sys
import time
import unittest
from datetime import datetime, timedelta

from common import BASE, EMAIL, PASSWORD, login, request, require_services, run_suite, url


class FlujoLoginCrearCitaE2E(unittest.TestCase):
    token = ""
    doc_usuario = ""
    paciente_doc = ""
    cita_id = None

    @classmethod
    def setUpClass(cls):
        require_services("seguridad", "info-medica", "agendamiento")

    def tearDown(self):
        if self.cita_id and self.token:
            request("DELETE", url("agendamiento", f"api/citas/{self.cita_id}/"), token=self.token)
            self.cita_id = None

    def test_01_login_credenciales_invalidas(self):
        """Login debe fallar con contraseña incorrecta."""
        status, payload = request(
            "POST",
            url("seguridad", "api/auth/login/"),
            body={"email": EMAIL, "password": "clave-incorrecta-xyz"},
        )
        self.assertEqual(status, 401, payload)
        self.assertFalse(payload.get("ok"))

    def test_02_flujo_login_paciente_y_cita(self):
        """Login JWT → registrar paciente → crear cita de valoración."""
        token, usuario = login()
        self.token = token
        self.doc_usuario = str(usuario.get("doc_usuario") or "")
        self.assertTrue(self.doc_usuario)

        status, me = request("GET", url("seguridad", "api/auth/me/"), token=token)
        self.assertEqual(status, 200, me)
        self.assertEqual((me.get("data") or {}).get("doc_usuario"), self.doc_usuario)

        status, tipos = request("GET", url("agendamiento", "api/tipos-terapia/"), token=token)
        self.assertEqual(status, 200, tipos)
        activos = [t for t in (tipos.get("data") or []) if t.get("activo")]
        self.assertTrue(activos, "No hay tipos de terapia activos")
        tipo_id = activos[0]["id"]

        self.paciente_doc = f"e2e{int(time.time()) % 1_000_000:06d}"
        status, pac = request(
            "POST",
            url("info-medica", "api/pacientes/"),
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
        self.assertEqual((pac.get("data") or {}).get("documento"), self.paciente_doc)

        inicio = (datetime.now() + timedelta(days=3)).replace(hour=10, minute=0, second=0, microsecond=0)
        status, cita = request(
            "POST",
            url("agendamiento", "api/citas/"),
            token=token,
            body={
                "documento_paciente": self.paciente_doc,
                "tipo_terapia": tipo_id,
                "proposito": "VALORACION",
                "inicio_cita": inicio.isoformat(),
            },
        )
        self.assertEqual(status, 201, cita)
        self.assertEqual(cita.get("message"), "Cita creada")
        cita_data = cita.get("data") or {}
        self.cita_id = cita_data.get("id")
        self.assertTrue(self.cita_id)
        self.assertEqual(cita_data.get("creado_por"), self.doc_usuario)
        self.assertEqual(cita_data.get("proposito"), "VALORACION")


if __name__ == "__main__":
    print(f"E2E login→cita base={BASE}")
    sys.exit(run_suite(FlujoLoginCrearCitaE2E, "RESUMEN E2E — login → crear cita"))
