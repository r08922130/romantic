# -*- coding: utf-8 -*-
"""
build_html.py - write the web version:  ../web/fourier.html
=======================================================

    python fourier_gui/build_html.py

One self-contained HTML file (no server, no internet needed): double-click it
to open it in a browser, or send it to someone. It is the 一筆畫 mode: the whole
picture as one closed curve drawn by one chain of circles. The bar picks the
picture: the Christmas tree or one of the cats (catart.py).

The one-stroke path is made here in Python (onestroke.py) and written into
the page as sample points; the page itself (web_template.html) does the
Fourier transform, the rotating circles and the drawing in JavaScript. Run
this again after changing the shapes, the template or the greeting in
settings.json.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fourier as F                                          # noqa: E402
from app import load_greeting                                # noqa: E402
from catart import CATS, cat_stroke, resample_detail         # noqa: E402
from onestroke import OneStroke, one_stroke, resample_labelled   # noqa: E402

TEMPLATE = os.path.join(HERE, "web_template.html")
OUT = os.path.join(os.path.dirname(HERE), "web", "fourier.html")


def flat(points):
    out = []
    for z in points:
        out += [round(z.real, 5), round(z.imag, 5)]
    return out


def picture(samples, labs, parts):
    names = sorted(set(labs))
    index = {n: i for i, n in enumerate(names)}
    return {"pts": flat(samples), "names": names, "lab": [index[l] for l in labs], "parts": parts}


def page_data():
    path, labels, info = one_stroke()
    tree = picture(*resample_labelled(path, labels, OneStroke.SAMPLES), info)
    cats = []
    for name, (title, _shapes) in CATS.items():
        path, labels, parts = cat_stroke(name)
        cats.append(dict(picture(*resample_detail(path, labels), parts), name=name, title=title))
    greeting, wish = load_greeting()
    return {"greeting": greeting, "wish": wish,
            "groundY": F.GROUND_Y, "starCY": F.STAR_CY,
            "one": tree, "cats": cats}


def build(out=OUT):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    data = json.dumps(page_data(), ensure_ascii=False, separators=(",", ":"))
    data = data.replace("</", "<\\/")                        # never end the <script> early
    html = html.replace("/*DATA*/", data, 1)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    return out


if __name__ == "__main__":
    path = build()
    print("wrote %s (%d KB)" % (path, os.path.getsize(path) // 1024))
