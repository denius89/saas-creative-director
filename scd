#!/bin/sh
set -eu
SCD_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$SCD_ROOT/core/src${PYTHONPATH:+:$PYTHONPATH}"

case "${1:-}" in
  install|update|rollback|health-check)
    exec python3 -m saas_creative_director.maintenance "$@"
    ;;
  "")
    echo "Usage: ./scd {install|update|rollback|health-check|init|status|validate|advance|approve|figma-manifest}" >&2
    exit 2
    ;;
  *)
    exec python3 -m saas_creative_director.cli "$@"
    ;;
esac

