# Fisiocloud — pruebas

## 1) Unitarias / API (por backend)

Misma metodología en todos los servicios:

- `config/settings_test.py` → MariaDB temporal `test_<bd>`
- `core/test_runner.py` → resumen en español
- `core/tests.py` → `APITestCase` + JWT

Dentro del contenedor, un servicio:

```bash
cd /app/backend_agendamiento
DJANGO_SETTINGS_MODULE=config.settings_test python3 manage.py test core.tests -v 2
```

Todos los backends:

```bash
bash /app/test/run_all_unit.sh
```

## 2) E2E (servicios vivos vía nginx)

Requieren `fisiocloud_setup.sh` ya corrido.

| Script | Flujo |
|---|---|
| `test_e2e_login_cita.py` | Login → paciente → cita |
| `test_e2e_suscripcion.py` | Login → checkout → webhook |
| `test_e2e_parametrizacion.py` | Login → catálogo tipos-documento |
| `test_e2e_soporte.py` | Login → ticket |
| `test_e2e_tratamiento_casa.py` | Login → plan → token → /casa/ |
| `test_e2e_procesos.py` | Catálogo + preferencias + job 403 |
| `test_e2e_asistente_voz.py` | Login → sesión (OK o 403 según feature) |

Uno:

```bash
python3 /app/test/test_e2e_login_cita.py
```

Todos:

```bash
python3 /app/test/run_all_e2e.py
```

Variables: `E2E_BASE_URL` (default `http://127.0.0.1`), `E2E_EMAIL`, `E2E_PASSWORD`.
