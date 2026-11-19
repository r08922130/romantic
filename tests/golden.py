# -*- coding: utf-8 -*-
r"""
Deterministic frame capture for the Christmas regression test.

    python tests/golden.py           # (re)write tests/golden/christmas.json

Only re-run this after a deliberate visual change, and look at the diff!
The frames were first verified against the pre-refactor program: identical
except the playful cat's Santa hat, which gained the droopy tip ("/#\.@").
"""
import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine.manager import SceneManager  # noqa: E402
from engine.render import Canvas         # noqa: E402

CATS = os.path.join(HERE, "cats_golden.json")
OUT = os.path.join(HERE, "golden", "christmas.json")
TIMES = [1, 5, 9, 12, 14, 19, 23, 30, 45, 60, 75, 85, 100, 130, 160, 180]
SEED = 4242


def capture(skip_intro=False, scene="christmas"):
    m = SceneManager("scenes", {}, {}, {"cats": CATS, "skip_intro": skip_intro})
    random.seed(SEED)
    sc = m.create(scene)
    cv = Canvas(sc.CW, sc.CH)
    frames, step = {}, 0
    for T in TIMES:
        while step < int(T * 30):
            sc.update(1 / 30.0)
            step += 1
        sc.draw(cv)
        chars = ["".join(cv.ch[y * cv.w:(y + 1) * cv.w]) for y in range(cv.h)]
        styles = hashlib.sha256(repr(cv.st).encode()).hexdigest()
        frames[str(T)] = {"chars": chars, "styles_sha256": styles}
    return frames


if __name__ == "__main__":
    data = {"normal": capture(False), "skip_intro": capture(True)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)
    print("wrote", OUT)
