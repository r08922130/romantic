# -*- coding: utf-8 -*-
"""The web version (tools/build_ascii_html.py): the recordings play back exactly."""
import base64
import json
import os
import random
import re
import sys
import tempfile
import unittest
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build_ascii_html as B          # noqa: E402
import engine.cats as catlib          # noqa: E402


def play(frames, n, blank):
    """What the page does: start blank, apply every frame's runs."""
    cells = [(blank, 0)] * n
    screens = []
    for d in frames:
        for k in range(0, len(d), 3):
            start, chars, sts = d[k], d[k + 1], d[k + 2]
            for i, (c, s) in enumerate(zip(chars, sts)):
                cells[start + i] = (c, s)
        screens.append(list(cells))
    return screens


def unpack(b64):
    return json.loads(zlib.decompress(base64.b64decode(b64)).decode("utf-8"))


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.web = tempfile.mkdtemp()
        B.build(cls.web, ["christmas"], choices=[[0, 1]])
        with open(os.path.join(cls.web, "ascii.html"), encoding="utf-8") as f:
            html = f.read()
        start = html.index("const DATA = ") + len("const DATA = ")
        cls.page = json.loads(html[start:html.index(";</script>", start)])
        with open(os.path.join(cls.web, "ascii", "christmas.js"), encoding="utf-8") as f:
            cls.data = json.loads(re.match(r"ASCII_SCENE\((.*)\);\s*$", f.read(), re.S).group(1))

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
        self.assertEqual(play(frames, n, " "), want)

    def test_page_lists_scenes_and_cats(self):
        self.assertEqual([s["name"] for s in self.page["scenes"]], ["christmas"])
        names = [c["name"] for c in catlib.read_config(os.path.join(ROOT, "cats.json"))[0]["cats"]]
        self.assertEqual([c["name"] for c in self.page["cats"]], names)
        self.assertEqual(sorted(self.data["overlays"]), ["0,1"])

    def test_background_plus_cats_is_what_the_engine_draws(self):
        """The page puts the chosen cats' overlay on the cat-free background:
        that must be exactly the screen the engine draws with those cats."""
        scene = self.page["scenes"][0]
        n = self.page["cols"] * self.page["rows"]
        styles = self.data["styles"]
        bg = play(unpack(self.data["bg"]), n, " ")
        ov = play(unpack(self.data["overlays"]["0,1"]), n, B.CLEAR)
        manager, _d = B.make_manager()
        with B.Recording() as rec:
            want = list(B.play(manager, "christmas", [0, 1], scene["seconds"], rec))
        self.assertEqual(len(want), len(bg))
        for k in range(0, len(want), 15):                   # one screen a second
            got = [(o if o[0] != B.CLEAR else b) for b, o in zip(bg[k], ov[k])]
            got = [(c, styles[s]) for c, s in got]
            exp = [(c, -1 if st is None else st) for c, st in want[k]]
            self.assertEqual(got, exp, "screen at %.0f s" % (k / 15.0))
        greeting = "".join(c for c, _s in want[int((scene["surprise"] + 15) * 15)])
        self.assertIn("My Love!", greeting)

    def test_cats_leave_the_background_alone(self):
        """Before the surprise only the cats differ: the overlay stays small."""
        n = self.page["cols"] * self.page["rows"]
        ov = play(unpack(self.data["overlays"]["0,1"]), n, B.CLEAR)
        early = ov[int(50 * 15)]                             # cats in, no greeting yet
        self.assertLess(sum(1 for c, _s in early if c != B.CLEAR), 250)

    def test_recording_restores_the_engine(self):
        saved = (catlib.random, catlib.load_cats)
        with B.Recording() as rec:
            rec.start()
        self.assertEqual((catlib.random, catlib.load_cats), saved)


if __name__ == "__main__":
    unittest.main()
