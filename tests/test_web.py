# -*- coding: utf-8 -*-
"""The web version (tools/build_ascii_html.py): recorded frames play back exactly."""
import base64
import json
import os
import random
import sys
import tempfile
import unittest
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build_ascii_html as B          # noqa: E402


def play(frames, n):
    """What the page does: start blank, apply every frame's runs."""
    cells = [(" ", 0)] * n
    screens = []
    for d in frames:
        for k in range(0, len(d), 3):
            start, chars, sts = d[k], d[k + 1], d[k + 2]
            for i, (c, s) in enumerate(zip(chars, sts)):
                cells[start + i] = (c, s)
        screens.append(list(cells))
    return screens


class WebTests(unittest.TestCase):
    def test_diff_round_trip(self):
        rng = random.Random(5)
        n = 300
        prev = [(" ", 0)] * n
        frames, want = [], []
        for _ in range(40):
            cur = list(prev)
            for _k in range(rng.randint(0, 30)):
                cur[rng.randrange(n)] = (rng.choice("ab*#\x01 "), rng.randrange(4))
            frames.append(B.diff(prev, cur))
            want.append(cur)
            prev = cur
        self.assertEqual(play(frames, n), want)

    def test_page_plays_a_scene(self):
        out = os.path.join(tempfile.mkdtemp(), "ascii.html")
        with open(B.build(out, ["christmas"]), encoding="utf-8") as f:
            html = f.read()
        self.assertNotIn("/*DATA*/", html)
        start = html.index("const DATA = ") + len("const DATA = ")
        page = json.loads(html[start:html.index(";</script>", start)])
        scene = page["scenes"][0]
        self.assertEqual(scene["name"], "christmas")
        rec = json.loads(zlib.decompress(base64.b64decode(scene["data"])).decode("utf-8"))
        self.assertEqual(len(rec["frames"]), int(scene["seconds"] * page["fps"]))
        screens = play(rec["frames"], page["cols"] * page["rows"])
        at_greeting = screens[int((scene["surprise"] + 15) * page["fps"])]
        self.assertIn("My Love!", "".join(c for c, _s in at_greeting))
        self.assertGreater(sum(1 for c, _s in at_greeting if c != " "), 500)   # a full picture


if __name__ == "__main__":
    unittest.main()
