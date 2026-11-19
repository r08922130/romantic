#!/bin/bash
# =====================================================================
#  工程師的浪漫 - macOS / Linux launcher
#  macOS: double-click this file in Finder (opens Terminal + the menu).
#  Any options are passed on, e.g.  ./run.command --scene osaka
# =====================================================================
cd "$(dirname "$0")" || exit 1

printf '\033[8;30;90t'              # ask for a 90 x 30 window (enough for the menu)

PY=""
for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1 &&
       "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)' 2>/dev/null; then
        PY="$cand"
        break
    fi
done

if [ -z "$PY" ]; then
    echo "找不到 Python 3（需要 3.7 以上）。"
    echo "Mac：到 https://www.python.org/downloads/ 下載安裝，"
    echo "     或在終端機輸入 xcode-select --install 安裝開發者工具（內含 python3）。"
    read -r -p "按 Enter 關閉..." _
    exit 1
fi

"$PY" main.py --menu "$@"
status=$?
if [ $status -ne 0 ]; then
    read -r -p "發生錯誤（代碼 $status），按 Enter 關閉..." _
fi
exit $status