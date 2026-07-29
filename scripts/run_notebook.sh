#!/usr/bin/env bash
# Execute a notebook detached, with a progress log and an unambiguous end marker.
#
# Training runs here take tens of minutes. Running them synchronously means an
# interruption leaves "did it finish?" unanswerable, and the notebook's own output
# is buffered until each cell completes. This wrapper writes START, then whatever
# the run emits, then exactly one of DONE or FAILED with an exit code -- so the
# state is always readable from the log alone.
#
# Usage:
#   bash scripts/run_notebook.sh notebooks/06_forecast_horizons.ipynb
#   tail -f logs/06_forecast_horizons_run.log
#
# Long notebooks may additionally append per-step progress to their own log
# (e.g. logs/nb06_progress.log), which updates while a cell is still running.

set -u

NOTEBOOK="${1:?usage: run_notebook.sh <notebook.ipynb>}"
TIMEOUT="${2:-7200}"

NAME="$(basename "$NOTEBOOK" .ipynb)"
LOG="logs/${NAME}_run.log"
mkdir -p logs
: > "$LOG"

{
  echo "START   $(date '+%Y-%m-%d %H:%M:%S')"
  echo "NOTEBOOK $NOTEBOOK"
  echo "TIMEOUT  ${TIMEOUT}s"
  echo "---"
} >> "$LOG"

.venv/Scripts/python.exe -m jupyter nbconvert \
    --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout="$TIMEOUT" \
    "$NOTEBOOK" >> "$LOG" 2>&1
STATUS=$?

echo "---" >> "$LOG"
if [ "$STATUS" -eq 0 ]; then
  echo "DONE    $(date '+%Y-%m-%d %H:%M:%S')  exit=0" >> "$LOG"
else
  echo "FAILED  $(date '+%Y-%m-%d %H:%M:%S')  exit=$STATUS" >> "$LOG"
fi

exit "$STATUS"
