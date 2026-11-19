# -*- coding: utf-8 -*-
"""
make_win_zip.py - package the project for Windows
=================================================

    python tools/make_win_zip.py          ->  dist/工程師的浪漫-windows.zip

After unzipping, double-click run.bat (needs Python 3.7+).
run.bat is kept ASCII + CRLF: cmd.exe misreads anything else.
"""
import os
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "工程師的浪漫"
OUT = os.path.join(ROOT, "dist", NAME + "-windows.zip")

FILES = ["main.py", "cats.json", "settings.json", "README.md", "run.bat"]
DIRS = ["engine", "scenes", "skins"]


def entries():
    for f in FILES:
        yield f
    for d in DIRS:
        for base, subdirs, files in os.walk(os.path.join(ROOT, d)):
            subdirs[:] = [s for s in subdirs if s != "__pycache__"]
            for f in sorted(files):
                if not f.endswith(".pyc"):
                    yield os.path.relpath(os.path.join(base, f), ROOT).replace(os.sep, "/")


def add(z, rel):
    src = os.path.join(ROOT, rel)
    with open(src, "rb") as fh:
        data = fh.read()
    if rel.endswith((".bat", ".cmd")):
        data.decode("ascii")                                  # fail loudly if not ASCII
        data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")   # CRLF
    info = zipfile.ZipInfo(NAME + "/" + rel, time.localtime(os.path.getmtime(src))[:6])
    info.flag_bits |= 0x800                                   # UTF-8 file names
    info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, data)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    names = list(entries())
    with zipfile.ZipFile(OUT, "w") as z:
        for rel in names:
            add(z, rel)
    print("wrote %s  (%d files, %.0f KB)" % (OUT, len(names), os.path.getsize(OUT) / 1024.0))


if __name__ == "__main__":
    main()
