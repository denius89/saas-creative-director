#!/bin/sh
set -eu
SCD_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$SCD_ROOT/core/src${PYTHONPATH:+:$PYTHONPATH}"

# Published 0.6 releases used a hard-coded update inventory. They receive the
# new launcher and core, then this idempotent step materializes newly managed
# knowledge trees carried inside core. It never overwrites an existing tree.
python3 -m saas_creative_director.maintenance bootstrap-managed

case "${1:-}" in
  install|update|rollback|health-check)
    exec python3 -m saas_creative_director.maintenance "$@"
    ;;
  "")
    echo "Usage: ./scd {install|update|rollback|health-check|init|status|validate|advance|approve|request-changes|figma-manifest|prepare-runtime|record-usage|usage-summary}" >&2
    exit 2
    ;;
  *)
    exec python3 -m saas_creative_director.cli "$@"
    ;;
esac
