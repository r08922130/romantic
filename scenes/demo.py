# -*- coding: utf-8 -*-
"""
demo.py - DemoScene: the smallest possible scene (architecture check)
=====================================================================

    python main.py --scene demo

Shows what a new scene needs: a `name`, some decorations, optionally an
accessory for the cats and its own greeting. Everything else (cats, the
surprise, the greeting banner, hearts, the main loop) comes from BaseScene.
Copy this file to start a new scene.
"""
import math

from engine.cats import Accessory
from engine.effects import Starfield
from engine.render import CW, S
from engine.scene import BaseScene

# the cats wear a small pink bow instead of a Santa hat here
BOW = Accessory("bow", [(0, 0, "{B}>{Y}o{B}<")], palette={"B": S(205, 1), "Y": S(226, 1)})


class DemoScene(BaseScene):
    name = "demo"
    title = "Minimal demo scene (architecture check)"
    label = "示範場景"
    order = 99

    CAT_ACCESSORY = BOW
    BANNER = {"ramp": (117, 123, 159, 195, 159, 123), "wish_colour": 152}
    SETTINGS = {
        "greeting": "Hello from a brand new scene!",
        "wish": "Add a file to scenes/ and it shows up here.",
        "surprise_at": 12.0,
        "every": 30.0,
        "hold": 12.0,
    }

    def build(self, rng):
        self.sky = Starfield(rng, n=30)

    def draw_background(self, cv):
        self.sky.draw(cv, self.t)
        # a softly pulsing moon
        glow = 229 if math.sin(self.t * 0.8) > 0 else 223
        for dy, row in enumerate((" _ ", "( )", " - ")):
            cv.text(CW - 10, 2 + dy, row, S(glow, 1))
        for x in cv.xs():                    # full width: use cv.xs(), not range(CW)
            cv.put(x, 23, "_", S(240))
