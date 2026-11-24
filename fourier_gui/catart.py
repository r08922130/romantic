# -*- coding: utf-8 -*-
"""
catart.py - the two cats, traced from photos, each as ONE closed curve
======================================================================

    path, labels, parts = cat_stroke("box")        (or "lying")

The shapes below were traced from the photos by hand, in photo pixels (the
photos themselves are not part of the project). Every shape is a loop; a
line (a whisker, a stripe) is a loop that goes along it and comes back. The
loops are joined by the shortest links (a minimum spanning tree): the pen
goes over a link to the next loop, round it, and back over the same link. So
the whole cat is a single closed path, and ONE Fourier series draws it.

parts: label -> {"colour", "line", "fill", "width"}, in painting order (the
first one is at the back). The links have the label "link".
"""
import math

SAMPLES = 4096                     # sample points of a cat (a power of two)

ORANGE, WHITE, PINK = "#e09a4e", "#f6f1ea", "#e8a3a6"
L_ORANGE, L_WHITE, L_PINK = "#b8702c", "#a99f98", "#b8686e"
STRIPE = "#b56a28"


class Art:
    """The traced shapes of one photo."""

    def __init__(self):
        self.shapes = []           # (label, loop points), in painting order
        self.parts = {}

    def _add(self, label, pts, colour, line, fill, width):
        assert label not in self.parts, label
        self.parts[label] = {"colour": colour, "line": line, "fill": fill, "width": width}
        self.shapes.append((label, pts))

    def area(self, label, pts, colour, line, width=1.8, smooth=True):
        pts = [complex(*p) for p in pts]
        self._add(label, spline(pts, True) if smooth else pts, colour, line, True, width)

    def oval(self, label, x, y, rx, ry, colour, line, width=1.6, tilt=0.0):
        turn = complex(math.cos(math.radians(tilt)), math.sin(math.radians(tilt)))
        pts = [complex(x, y) + turn * complex(rx * math.cos(a), ry * math.sin(a))
               for a in (2 * math.pi * k / 40 for k in range(40))]
        self._add(label, pts, colour, line, True, width)

    def line(self, label, pts, line, width=1.6):
        s = spline([complex(*p) for p in pts], False)
        self._add(label, s + s[-2:0:-1], line, line, False, width)   # there and back

    def lines(self, label, many, line, width=1.6):
        for i, pts in enumerate(many):
            self.line("%s%d" % (label, i), pts, line, width)


def spline(pts, closed, steps=8):
    """A smooth (Catmull-Rom) curve through the points."""
    n = len(pts)

    def at(i):
        return pts[i % n] if closed else pts[min(n - 1, max(0, i))]

    out = []
    for i in range(n if closed else n - 1):
        a, b, c, d = at(i - 1), at(i), at(i + 1), at(i + 2)
        for s in range(steps):
            t = s / float(steps)
            out.append(0.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t
                              + (3 * b - a - 3 * c + d) * t ** 3))
    if not closed:
        out.append(pts[-1])
    return out


# ---------------------------------------------------------------------
#  The cat in the cardboard box
# ---------------------------------------------------------------------
def box_cat():
    a = Art()
    card, card_l = "#b8914f", "#8a6528"
    # the line under the face, shared by the head, the chest and the body
    chin = [(405, 505), (415, 530), (432, 555), (455, 574), (478, 588), (505, 597), (530, 593),
            (552, 582), (580, 570), (607, 556), (632, 540), (650, 520), (663, 498), (669, 478)]
    a.area("back_flap", [(681, 527), (892, 592), (907, 602), (917, 622), (923, 646), (923, 712),
                         (754, 651), (735, 600), (704, 564)], "#7d5c2a", card_l, smooth=False)
    a.area("inside_right", [(754, 651), (923, 713), (785, 782), (774, 764), (765, 718), (758, 682)],
           "#5f431c", card_l, smooth=False)
    a.area("inside_left", [(288, 673), (373, 643), (379, 705)], "#8d6b33", card_l, smooth=False)
    a.area("body", chin + [(679, 541), (704, 564), (735, 600), (751, 645), (758, 682), (765, 718),
                           (774, 764), (778, 786), (754, 800), (700, 825), (683, 834), (600, 869),
                           (540, 896), (482, 922), (497, 870), (508, 831), (510, 808), (504, 785),
                           (485, 768), (454, 752), (415, 728), (376, 709), (379, 695), (379, 664),
                           (373, 627), (374, 591), (379, 568), (390, 541)], ORANGE, L_ORANGE)
    a.area("chest", chin[1:-1] + [(669, 520), (676, 536), (675, 568), (658, 605), (631, 632),
                                  (595, 650), (554, 673), (541, 695), (567, 714), (590, 740),
                                  (594, 773), (602, 805), (608, 864), (540, 896), (482, 922),
                                  (497, 870), (508, 831), (510, 808), (504, 785), (486, 764),
                                  (472, 736), (454, 700), (435, 668), (408, 636), (379, 609),
                                  (374, 591), (385, 568), (402, 545)], WHITE, L_WHITE)
    a.lines("fur", [[(702, 570), (712, 610), (718, 660), (712, 705)],
                    [(722, 605), (736, 645), (741, 690), (735, 730)],
                    [(590, 700), (635, 688), (676, 700)], [(612, 738), (645, 728), (684, 742)],
                    [(614, 782), (640, 774), (664, 790)], [(630, 660), (662, 648), (694, 662)],
                    [(384, 640), (398, 650), (410, 666)], [(388, 690), (410, 688), (430, 704)]],
            STRIPE, 2.6)
    a.lines("ruff", [[(470, 640), (480, 675), (492, 700)], [(512, 630), (514, 665), (508, 695)],
                     [(556, 625), (548, 650), (536, 672)], [(530, 740), (538, 775), (536, 805)]],
            "#cfc6bf", 1.4)
    a.area("flap_left", [(127, 727), (158, 654), (177, 634), (192, 631), (215, 640), (454, 751),
                         (485, 768), (504, 785), (510, 808), (508, 831), (477, 921), (354, 850),
                         (254, 795)], "#c69f58", card_l, smooth=False)
    a.area("face_left", [(127, 728), (254, 796), (354, 851), (479, 923), (485, 1279), (150, 1036)],
           "#8f6c33", card_l, smooth=False)
    a.area("face_right", [(479, 923), (683, 834), (688, 911), (715, 855), (800, 809), (925, 715),
                          (901, 1017), (485, 1279)], card, card_l, smooth=False)
    a.area("flap_small", [(715, 855), (692, 823), (673, 797), (671, 785), (677, 771), (715, 751),
                          (726, 748), (738, 748), (754, 758), (800, 809)], "#d3ad66", card_l,
           smooth=False)
    a.area("ear_left", [(424, 372), (428, 346), (435, 319), (442, 283), (451, 251), (461, 233),
                        (469, 227), (480, 233), (492, 251), (503, 278), (512, 305), (519, 330),
                        (505, 358), (460, 378)], ORANGE, L_ORANGE)
    a.area("ear_right", [(608, 356), (633, 330), (655, 310), (678, 298), (701, 293), (712, 299),
                         (715, 317), (712, 346), (703, 378), (692, 403), (680, 434), (655, 420),
                         (625, 385)], ORANGE, L_ORANGE)
    a.area("head", chin + [(676, 458), (680, 436), (660, 410), (632, 376), (610, 355), (587, 346),
                           (551, 337), (519, 331), (497, 350), (465, 366), (424, 366), (417, 380),
                           (412, 402), (410, 422), (407, 442), (402, 462), (400, 482)],
           ORANGE, L_ORANGE)
    a.area("pink_left", [(436, 350), (444, 301), (453, 260), (467, 238), (480, 246), (496, 280),
                         (507, 312), (496, 340), (470, 346), (452, 362), (441, 372)], PINK, L_PINK)
    a.area("pink_right", [(626, 361), (646, 334), (674, 309), (699, 302), (709, 309), (710, 324),
                          (704, 355), (693, 387), (679, 414), (670, 430), (660, 419), (656, 401),
                          (640, 384)], PINK, L_PINK)
    a.lines("earfur", [[(452, 340), (470, 318), (494, 312)], [(452, 312), (468, 292), (488, 288)],
                       [(640, 372), (652, 352), (680, 346)], [(650, 388), (664, 372), (688, 368)]],
            "#f3dcd8", 1.4)
    a.area("face", [(541, 411), (534, 423), (527, 417), (521, 432), (516, 446), (509, 459),
                    (498, 468), (486, 470), (471, 469), (455, 466), (444, 476), (428, 486), (410, 484), (400, 480)]
           + chin[:9] + [(600, 562), (616, 556), (607, 530), (606, 504), (588, 498), (569, 490),
                         (557, 476), (552, 459), (552, 444), (553, 430), (551, 417),
                         (546, 424)], WHITE, L_WHITE)
    a.lines("brow", [[(533, 345), (530, 362), (521, 380), (519, 404)],
                     [(551, 345), (549, 362), (542, 380), (541, 398)], [(571, 350), (572, 368), (564, 390)],
                     [(590, 356), (588, 376), (578, 400)], [(412, 424), (428, 418), (444, 418)],
                     [(424, 436), (430, 458), (442, 472)], [(619, 466), (640, 476), (655, 500)],
                     [(614, 508), (634, 514), (652, 504)], [(620, 538), (636, 532), (650, 514)]],
            STRIPE, 2.6)
    for side, x, y, rx, ry, py in (("l", 472, 439, 22, 22, 436), ("r", 590, 470, 24, 22, 466)):
        a.oval("rim_" + side, x, y, rx + 3, ry + 3, "#4a3020", "#c98b4a")
        a.oval("iris_" + side, x, y, rx, ry, "#d99a2b", "#8a5a16")
        a.oval("pupil_" + side, x + 1, py, 5.5, 12, "#17110c", "#6b5030")
        a.oval("glint_" + side, x + 5, py - 8, 3.6, 4, "#ffffff", "#ffffff", 1.0)
    a.area("nose", [(486, 518), (501, 524), (517, 525), (535, 521), (537, 530), (522, 538),
                    (510, 550), (503, 554), (498, 542), (490, 530)], "#e58a94", "#a8505c")
    a.line("mouth", [(479, 565), (492, 562), (504, 557), (504, 560), (514, 569), (532, 574)],
           "#9c5560", 2.0)
    a.lines("whisker", [[(452, 526), (418, 517), (372, 522)], [(452, 534), (420, 534), (378, 552)],
                        [(456, 542), (430, 552), (402, 578)], [(560, 542), (604, 552), (648, 580)],
                        [(556, 548), (592, 566), (622, 596)], [(550, 556), (572, 578), (590, 606)]],
            "#ded8d2", 1.2)
    return a


# ---------------------------------------------------------------------
#  The cat lying on the floor
# ---------------------------------------------------------------------
def lying_cat():
    a = Art()
    chin = [(883, 309), (893, 325), (907, 340), (922, 355), (935, 365), (951, 371), (964, 367),
            (982, 357), (1001, 344), (1018, 332), (1028, 317)]
    a.area("tail", [(347, 315), (362, 313), (388, 314), (419, 316), (470, 321), (452, 331),
                    (412, 340), (381, 334), (353, 325)], ORANGE, L_ORANGE)
    a.lines("ring", [[(367, 314), (365, 329)], [(384, 314), (382, 333)], [(402, 315), (399, 337)],
                     [(421, 317), (419, 337)]], STRIPE, 3.0)
    a.area("body", [(224, 406), (230, 393), (247, 385), (287, 381), (356, 362), (419, 343),
                    (462, 327), (487, 309), (506, 299), (531, 287), (569, 277), (612, 273),
                    (662, 276), (700, 273), (750, 276), (800, 281), (831, 293), (856, 299),
                    (880, 294)] + chin + [(1026, 345), (1022, 376), (1014, 398), (1001, 413),
                    (987, 427), (940, 440), (884, 470), (884, 482), (878, 491), (862, 499),
                    (834, 502), (800, 490), (775, 474), (744, 456), (719, 443), (681, 439),
                    (637, 432), (600, 431), (569, 422), (544, 412), (469, 420), (381, 421),
                    (331, 440), (312, 452), (287, 459), (276, 449), (275, 431), (284, 420),
                    (250, 426), (230, 421)], WHITE, L_WHITE)
    a.area("patch", [(506, 299), (531, 287), (569, 277), (612, 273), (662, 276), (700, 273),
                     (750, 276), (800, 281), (831, 293), (857, 300), (858, 314), (850, 331),
                     (838, 336), (826, 324), (819, 343), (800, 359), (784, 381), (762, 393),
                     (758, 376), (752, 400), (742, 394), (733, 374), (718, 376), (702, 404),
                     (675, 396), (650, 384), (625, 366), (591, 356), (576, 342), (562, 325),
                     (532, 331), (510, 343), (502, 330)], ORANGE, L_ORANGE)
    a.lines("fur", [[(560, 295), (600, 290), (640, 296)], [(600, 318), (645, 312), (690, 320)],
                    [(660, 345), (700, 338), (738, 346)], [(700, 296), (745, 292), (785, 302)],
                    [(740, 322), (772, 316), (802, 326)], [(680, 372), (705, 366), (726, 360)]],
            STRIPE, 2.2)
    a.area("spot", [(362, 386), (378, 384), (394, 385), (388, 391), (374, 392)], "#ecc08c", L_ORANGE)
    a.lines("limb", [[(284, 420), (292, 409), (319, 398), (375, 385), (430, 378), (500, 369), (527, 360)],
                     [(790, 378), (765, 397), (747, 412), (741, 430), (744, 455)],
                     [(812, 420), (843, 437), (862, 447), (877, 460), (884, 474)],
                     [(240, 420), (243, 410), (238, 402)], [(292, 455), (294, 444), (288, 436)],
                     [(306, 452), (308, 442), (302, 434)], [(846, 498), (849, 488), (844, 480)],
                     [(862, 497), (866, 487), (862, 478)]], L_WHITE, 1.8)
    a.area("paw", [(883, 462), (897, 446), (912, 437), (939, 426), (962, 423), (987, 428),
                   (980, 437), (970, 450), (951, 463), (924, 473), (905, 479), (888, 477)],
           WHITE, L_WHITE)
    a.lines("toe", [[(893, 470), (898, 465), (896, 459)], [(907, 458), (911, 453), (909, 448)]],
            L_WHITE, 1.6)
    a.area("ear_left", [(884, 266), (874, 244), (866, 217), (862, 200), (865, 190), (878, 189),
                        (897, 200), (910, 213), (922, 232), (905, 250)], ORANGE, L_ORANGE)
    a.area("ear_right", [(973, 222), (978, 202), (987, 182), (1001, 169), (1016, 165), (1028, 175),
                         (1033, 194), (1034, 217), (1033, 245), (1010, 245), (990, 236)],
           ORANGE, L_ORANGE)
    a.area("head", chin + [(1032, 294), (1034, 267), (1034, 248), (1015, 240), (993, 230),
                           (974, 218), (958, 212), (935, 212), (917, 214), (917, 230), (900, 245),
                           (884, 260), (878, 275), (880, 294)], WHITE, L_WHITE)
    a.area("mask", [(945, 240), (939, 246), (934, 256), (926, 266), (916, 276), (905, 285),
                    (897, 291), (897, 304), (902, 318), (893, 322), (883, 309), (880, 294),
                    (878, 275), (884, 260), (900, 245), (917, 230), (917, 214), (935, 212),
                    (958, 212), (974, 218), (993, 230), (1015, 240), (1034, 248), (1034, 267),
                    (1030, 278), (1018, 281), (997, 276), (982, 276), (968, 278), (960, 267),
                    (953, 255), (949, 242)], ORANGE, L_ORANGE)
    a.area("pink_left", [(883, 256), (876, 240), (868, 213), (865, 197), (878, 194), (895, 203),
                         (909, 218), (915, 229), (901, 242), (891, 254)], PINK, L_PINK)
    a.area("pink_right", [(980, 220), (985, 197), (996, 179), (1010, 171), (1022, 175), (1029, 194),
                          (1030, 217), (1025, 237), (1010, 236), (992, 228)], PINK, L_PINK)
    a.lines("earfur", [[(886, 244), (893, 230), (905, 224)], [(990, 222), (1000, 208), (1014, 204)],
                       [(1000, 230), (1010, 218), (1022, 215)]], "#f3dcd8", 1.4)
    a.lines("brow", [[(928, 218), (931, 232), (925, 248)], [(944, 217), (944, 228), (941, 238)],
                     [(960, 218), (958, 232), (962, 248)], [(887, 280), (890, 294), (896, 308)],
                     [(1000, 250), (1012, 256), (1026, 258)]], STRIPE, 2.2)
    for side, x, y, rx, ry, tilt in (("l", 913, 298, 13, 11, 8), ("r", 982, 289, 14.5, 12, -12)):
        a.oval("rim_" + side, x, y, rx + 1.8, ry + 1.8, "#4a3020", "#c98b4a", tilt=tilt)
        a.oval("iris_" + side, x, y, rx, ry, "#c98a2c", "#8a5a16", tilt=tilt)
        a.oval("pupil_" + side, x, y - 1.5, 5, 6.5, "#17110c", "#6b5030")
        a.oval("glint_" + side, x + 3, y - 5, 1.9, 2.1, "#ffffff", "#ffffff", 1.0)
    a.area("nose", [(931, 340), (939, 337), (951, 338), (961, 334), (957, 346), (948, 355),
                    (942, 350)], "#e58a94", "#a8505c", 1.4)
    a.line("mouth", [(933, 357), (942, 361), (948, 355), (948, 357), (957, 361), (970, 357)],
           "#9c5560", 1.6)
    a.lines("whisker", [[(926, 346), (906, 345), (880, 354)], [(928, 352), (912, 358), (892, 374)],
                        [(976, 338), (1004, 328), (1042, 332)], [(976, 344), (1004, 342), (1038, 354)],
                        [(972, 350), (994, 354), (1022, 370)]], "#8f8780", 1.0)
    return a


CATS = {"box": ("紙箱貓咪", box_cat), "lying": ("躺躺貓咪", lying_cat)}


# ---------------------------------------------------------------------
#  All the loops joined into one closed path
# ---------------------------------------------------------------------
def spanning_tree(loops):
    """Prim: -> children[i] = [(index on loop i, j, index on loop j)], from loop 0."""
    best, parent = {}, {}
    children = {i: [] for i in range(len(loops))}

    def relax(i):
        for j in best_left:
            d, ki, kj = min((abs(p - q), ki, kj) for ki, p in enumerate(loops[i])
                            for kj, q in enumerate(loops[j]))
            if j not in best or d < best[j]:
                best[j], parent[j] = d, (i, ki, kj)

    best_left = set(range(1, len(loops)))
    relax(0)
    while best_left:
        j = min(best_left, key=lambda k: (best[k], k))
        best_left.discard(j)
        i, ki, kj = parent[j]
        children[i].append((ki, j, kj))
        relax(j)
    return children


def cat_stroke(name):
    """-> (points, labels, parts): the cat as one closed path, about 2 units
    high or wide, y downwards, centred on 0."""
    art = CATS[name][1]()
    loops = [pts for _l, pts in art.shapes]
    every = [z for pts in loops for z in pts]
    x0, x1 = min(z.real for z in every), max(z.real for z in every)
    y0, y1 = min(z.imag for z in every), max(z.imag for z in every)
    mid, scale = complex((x0 + x1) / 2, (y0 + y1) / 2), 2.0 / max(x1 - x0, y1 - y0)
    children = spanning_tree(loops)
    points, labels = [], []

    def go(z, label):
        points.append((z - mid) * scale)
        labels.append(label)

    def walk(i, start):
        label, pts = art.shapes[i]
        n = len(pts)
        for s in range(n + 1):
            k = (start + s) % n
            go(pts[k], label)
            if s == n:
                break
            for ki, j, kj in children[i]:
                if ki == k:
                    go(loops[j][kj], "link")
                    walk(j, kj)
                    go(pts[k], "link")

    walk(0, 0)
    parts = dict(art.parts)
    parts["link"] = {"colour": "#56648f", "line": "#56648f", "fill": False, "width": 0.8}
    return points, labels, parts


def resample_detail(points, labels, n=SAMPLES):
    """n samples along the path, closer together on small shapes (the eyes,
    the nose) than on long ones (the box): the pen slows down for detail.
    Each sample has the label of the piece of path it lies on."""
    pts = list(points) + [points[0]]
    labs = [labels[(i + 1) % len(labels)] for i in range(len(points))]
    seg = [abs(pts[i + 1] - pts[i]) for i in range(len(points))]
    length = {}
    for s, l in zip(seg, labs):
        length[l] = length.get(l, 0.0) + s
    weight = {l: min(3.0, max(0.5, math.sqrt(0.6 / v))) if v else 1.0 for l, v in length.items()}
    weight["link"] = 1.0
    cost = [s * weight[l] for s, l in zip(seg, labs)]
    total = sum(cost)
    out, lab, i, acc = [], [], 0, 0.0
    for k in range(n):
        target = total * k / float(n)
        while i < len(seg) - 1 and acc + cost[i] < target:
            acc += cost[i]
            i += 1
        u = min(1.0, (target - acc) / cost[i]) if cost[i] else 0.0
        out.append(pts[i] + (pts[i + 1] - pts[i]) * u)
        lab.append(labs[i])
    return out, lab
