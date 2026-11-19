# -*- coding: utf-8 -*-
"""
make_mac_zip.py - package the project for a Mac
===============================================

    python tools/make_mac_zip.py          ->  dist/工程師的浪漫-mac.zip

Windows cannot mark a file as executable, but a zip can carry Unix file
permissions. Inside this zip run.command is marked executable (755), so
after unzipping on the Mac it can be double-clicked in Finder right away.
"""
import os
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "工程師的浪漫"          # 工程師的浪漫
OUT = os.path.join(ROOT, "dist", NAME + "-mac.zip")

FILES = ["main.py", "cats.json", "settings.json", "README.md",
         "run.command"]
DIRS = ["engine", "scenes", "skins"]
EXECUTABLE = {"run.command"}


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
    if rel.endswith((".command", ".sh")):
        data = data.replace(b"\r\n", b"\n")              # shell scripts need LF
    info = zipfile.ZipInfo(NAME + "/" + rel, time.localtime(os.path.getmtime(src))[:6])
    info.create_system = 3                               # Unix, so permissions count
    mode = 0o755 if os.path.basename(rel) in EXECUTABLE else 0o644
    info.external_attr = (0o100000 | mode) << 16         # regular file + mode
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
