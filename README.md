# Fisiocloud — pruebas E2E

Pruebas punta a punta contra los microservicios vivos (vía nginx `/svc/`).

| Archivo | Flujo |
|---|---|
| `test_e2e_login_cita.py` | Login (seguridad) → paciente (info-medica) → cita (agendamiento) |

## Requisitos

- Contenedor / servidor con nginx + backends levantados (`fisiocloud_setup.sh`)
- Usuario demo: `juan@test.com` / `Terapeuta@123456`

## Cómo correr

Dentro del contenedor:

```bash
python3 /app/test/test_e2e_login_cita.py
```

Desde el host (ajusta el puerto si aplica):

```bash
E2E_BASE_URL=http://127.0.0.1:8089 python3 app/test/test_e2e_login_cita.py
```

Variables opcionales: `E2E_BASE_URL`, `E2E_EMAIL`, `E2E_PASSWORD`.
