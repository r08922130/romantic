# -*- coding: utf-8 -*-
"""
sprites.py - small helpers for drawing multi-line ASCII art in scenes
=====================================================================

  sym(left, centre, half)  build a mirror-symmetric row from its left half
                           ('/'<->'\\', '('<->')', '['<->']' ... swapped)
  Art                      a block of rows + colours, drawn at (x, y)
  Prop                     an Art standing on the floor; cats walk in front
                           of / behind it and a playful cat may hide behind it
                           (has cx, w, h like BaseScene.hideouts() expects)

Colours: give `charmap` {char: style} for "this character is always this
colour", and/or `mask` rows (same shape as the art) whose letters are keys
of `palette`. A space in the art is transparent; '$' is an opaque blank.
"""
from .render import S

_SWAP = str.maketrans("/\\()<>[]{}", "\\/)(><][}{")


def sym(left, centre="", half=None):
    """'/__' + '_' -> '/_____\\'   (left half mirrored onto the right)."""
    if half is not None:
        left = left.rjust(half)
    return left + centre + left[::-1].translate(_SWAP)


class Art:
    def __init__(self, rows, charmap=None, default=None, mask=None, palette=None):
        self.rows = rows
        self.charmap = charmap or {}
        self.default = S(255) if default is None else default
        self.mask = mask
        self.palette = palette or {}
        self.w = max(len(r) for r in rows)
        self.h = len(rows)

    def style(self, x, y, ch):
        if self.mask is not None and y < len(self.mask) and x < len(self.mask[y]):
            k = self.mask[y][x]
            if k != " " and k in self.palette:
                return self.palette[k]
        return self.charmap.get(ch, self.default)

    def draw(self, cv, x, y, recolor=None):
        """recolor(dx, dy, ch, style) -> style lets a scene animate colours."""
        for dy, row in enumerate(self.rows):
            for dx, ch in enumerate(row):
                if ch == " ":
                    continue
                st = self.style(dx, dy, ch)
                if recolor is not None:
                    st = recolor(dx, dy, ch, st)
                if ch == "$":
                    cv.put(x + dx, y + dy, " ", st, True)
                else:
                    cv.put(x + dx, y + dy, ch, st)


class Prop:
    """An Art standing with its bottom row on `base` (a floor row)."""

    def __init__(self, art, x, base, recolor=None):
        self.art = art
        self.x = x
        self.base = base
        self.w, self.h = art.w, art.h
        self.cx = x + art.w / 2.0
        self.recolor = recolor

    def draw(self, cv, t=0.0):
        rc = None
        if self.recolor is not None:
            rc = lambda dx, dy, ch, st: self.recolor(t, dx, dy, ch, st)  # noqa: E731
        self.art.draw(cv, self.x, self.base - self.h + 1, rc)
