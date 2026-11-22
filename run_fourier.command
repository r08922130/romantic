#!/bin/bash
# Double-click (macOS): the Fourier epicycles Christmas tree in its own window.
cd "$(dirname "$0")" || exit 1
PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
exec "$PY" fourier_gui/app.py "$@"
