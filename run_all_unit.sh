#!/usr/bin/env bash
# Corre pruebas unitarias/API de todos los backends (MariaDB test_*).
# Uso (dentro del contenedor):
#   bash /app/test/run_all_unit.sh
set -u
ROOT="${APP_ROOT:-/app}"
FAIL=0

SERVICES=(
  backend_seguridad
  backend_suscripcion
  backend_info_medica
  backend_agendamiento
  backend_parametrizacion
  backend_tratamiento_casa
  backend_soporte
  backend_procesos_automaticos
  backend_asistente_voz
)

echo "=============================================="
echo " UNIT/API — todos los backends"
echo "=============================================="

for svc in "${SERVICES[@]}"; do
  echo ""
  echo ">>> $svc"
  if (cd "$ROOT/$svc" && DJANGO_SETTINGS_MODULE=config.settings_test python3 manage.py test core.tests -v 2); then
    echo ">>> $svc OK"
  else
    echo ">>> $svc FALLÓ"
    FAIL=1
  fi
done

echo ""
echo "=============================================="
if [ "$FAIL" -eq 0 ]; then
  echo " Resultado global UNIT/API: EXITOSO"
else
  echo " Resultado global UNIT/API: FALLIDO"
fi
echo "=============================================="
exit "$FAIL"
