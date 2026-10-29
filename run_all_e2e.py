#!/usr/bin/env python3
"""Ejecuta todas las suites E2E del directorio test/."""
from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

from common import BASE, EMAIL, ResumenResult, imprimir_resumen

# Asegurar imports locales
sys.path.insert(0, str(Path(__file__).resolve().parent))

MODULES = [
    "test_e2e_login_cita",
    "test_e2e_suscripcion",
    "test_e2e_parametrizacion",
    "test_e2e_soporte",
    "test_e2e_tratamiento_casa",
    "test_e2e_procesos",
    "test_e2e_asistente_voz",
]


def main() -> int:
    print(f"E2E ALL base={BASE} email={EMAIL}")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in MODULES:
        mod = importlib.import_module(name)
        suite.addTests(loader.loadTestsFromModule(mod))
    runner = unittest.TextTestRunner(verbosity=2, resultclass=ResumenResult)
    result = runner.run(suite)
    return imprimir_resumen(result, "RESUMEN E2E — todos los módulos")  # type: ignore[arg-type]


if __name__ == "__main__":
    sys.exit(main())
