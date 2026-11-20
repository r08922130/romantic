# -*- coding: utf-8 -*-
"""
cats.py - the cat characters, shared by every scene
=====================================================

  * Skin      - what a cat looks like. Loaded from a ``skins/*.cat`` text file
                (see skins/README-skins.md for the format).
  * Cat       - movement, jumping, drawing (shared by every personality)
  * CalmCat   - "calm":    slow, sits, naps, gazes at the scene, follows friends
  * PlayfulCat- "playful": runs, hops, hides behind props, pounces, visits
  * Person    - a person (the two of you): strolls, looks at the scene, does
                a peace sign, keeps close to the other person
  * load_cats - reads cats.json ("cats" and "people") and builds them

Nothing in here knows about a particular holiday. The world (scene) a cat
lives in provides (engine/scene.py BaseScene has all of them):
  CW, CX, FLOOR_MIN, FLOOR_MAX, BACK_Y, GAZE, t, phase, cats, fx, heart,
  HEART_RAMP, Z_RAMP, SPARK_RAMP, hideouts()
"""
import json
import math
import os
import random
import re

GRAVITY = 34.0


def clamp(v, a, b):
    return a if v < a else (b if v > b else v)


def style(n, bold=False):
    return n | (256 if bold else 0)


def ansi(st):
    return "\x1b[0;%s38;5;%dm" % ("1;" if st & 256 else "", st & 255)


DEFAULT_STYLE = style(255)


class SkinError(Exception):
    pass


class ConfigError(Exception):
    pass


# ---------------------------------------------------------------------
#  Sprite markup:   {X} switches colour (X = palette key),
#                   ' ' is transparent,  '$' is an opaque blank
# ---------------------------------------------------------------------
_TOK = re.compile(r"\{([A-Za-z])\}")
_PARSED = {}


def parse(row):
    cells = _PARSED.get(row)
    if cells is None:
        cells = []
        key, x, pos = "O", 0, 0
        for m in list(_TOK.finditer(row)) + [None]:
            end = m.start() if m else len(row)
            for ch in row[pos:end]:
                if ch == "$":
                    cells.append((x, " ", key))
                elif ch != " ":
                    cells.append((x, ch, key))
                x += 1
            if m:
                key = m.group(1)
                pos = m.end()
        _PARSED[row] = cells
    return cells


MIRROR = str.maketrans("/\\()<>[]{}", "\\/)(><][}{")


# =====================================================================
#  Accessories: scene-specific things a cat wears (Santa hat, bow tie...)
# =====================================================================
ANCHORS = ("hat", "neck")     # where a skin lets accessories attach


class Accessory:
    """A tiny sprite drawn on top of a cat's head.

    rows    [(dx, dy, markup), ...] relative to the skin's anchor for `slot`
            (markup is the same as in skins: {X} colour keys, $ = opaque)
    palette {key: style}; keys it lacks fall back to the skin's palette.
    A skin without that anchor simply wears nothing.
    """

    def __init__(self, name, rows, palette=None, slot="hat"):
        self.name = name
        self.rows = rows
        self.palette = palette or {}
        self.slot = slot


# =====================================================================
#  Skins
# =====================================================================
POSES = ("stand", "sit", "sleep", "run", "crouch", "peek")
FALLBACK = {"run": "stand", "crouch": "sit", "sleep": "sit"}
DEFAULT_EYES = {"normal": "o", "wide": "O", "happy": "^", "closed": "-", "wink": "^-"}
LAYER_KINDS = ("static", "walk", "tail", "head")


class Skin:
    def __init__(self, name):
        self.name = name
        self.width = self.height = 0
        self.palette = {}
        self.eyes = dict(DEFAULT_EYES)
        self.head = []
        self.poses = {}
        self.anchors = {}         # "hat" -> (x, y) in head coordinates
        self._cache = {}

    def inherit(self, base):
        self.width, self.height = base.width, base.height
        self.anchors = dict(base.anchors)
        self.palette = dict(base.palette)
        self.eyes = dict(base.eyes)
        self.head = list(base.head)
        self.poses = dict(base.poses)

    def head_width(self):
        return max([x + 1 for r in self.head for (x, _c, _k) in parse(r)] or [1])

    def layers_for(self, pose):
        while pose not in self.poses and pose in FALLBACK:
            pose = FALLBACK[pose]
        if pose in self.poses:
            return self.poses[pose]
        if pose == "peek":   # automatic: just the head, centred
            return [{"x": (self.width - self.head_width()) // 2, "y": 1,
                     "kind": "head", "frames": [[]]}]
        return self.poses["stand"]

    def frame_count(self, pose):
        return max([len(L["frames"]) for L in self.layers_for(pose)
                    if L["kind"] in ("walk", "tail")] or [1])

    def eye_pair(self, name):
        v = self.eyes.get(name) or self.eyes.get("normal") or "o"
        return v[0], v[-1]

    def cells(self, pose, walk, tail, eyes, face, acc=None):
        key = (pose, walk, tail, eyes, face, acc.name if acc else None)
        cells = self._cache.get(key)
        if cells is not None:
            return cells
        le, re_ = eyes
        head = [r.replace("%L", le).replace("%R", re_) for r in self.head]
        cells = []
        for L in self.layers_for(pose):
            if L["kind"] == "head":
                rows = head
            else:
                fr = L["frames"]
                i = walk if L["kind"] == "walk" else (tail if L["kind"] == "tail" else 0)
                rows = fr[i % len(fr)]
            for dy, row in enumerate(rows):
                for dx, ch, k in parse(row):
                    cells.append((L["x"] + dx, L["y"] + dy, ch,
                                  self.palette.get(k, DEFAULT_STYLE)))
            if L["kind"] == "head" and acc is not None and acc.slot in self.anchors:
                ax, ay = self.anchors[acc.slot]
                for adx, ady, row in acc.rows:
                    for dx, ch, k in parse(row):
                        st = acc.palette.get(k) or self.palette.get(k, DEFAULT_STYLE)
                        cells.append((L["x"] + ax + adx + dx, L["y"] + ay + ady, ch, st))
        if face < 0:
            cells = [(self.width - 1 - x, y, ch.translate(MIRROR), st)
                     for (x, y, ch, st) in cells]
        self._cache[key] = cells
        return cells


def parse_skin(text, default_name, where, load_base):
    meta = {}
    head = None
    poses = {}
    pose = layer = rows = None

    def err(n, msg):
        raise SkinError("%s, line %d: %s" % (where, n, msg))

    for n, raw in enumerate(text.splitlines(), 1):
        if raw.startswith("|"):
            if rows is None:
                err(n, "art row '|...' must be inside @head or a @layer")
            rows.append(raw[1:])
            continue
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line == "---":
            if layer is None or layer["kind"] == "head":
                err(n, "'---' (next frame) is only allowed inside a @layer")
            layer["frames"].append([])
            rows = layer["frames"][-1]
            continue
        if line.startswith("@"):
            parts = line[1:].split()
            cmd = parts[0].lower() if parts else ""
            if cmd == "head":
                head = []
                rows, layer, pose = head, None, None
            elif cmd == "pose":
                if len(parts) < 2:
                    err(n, "usage: @pose NAME")
                pose = []
                poses[parts[1].lower()] = pose
                rows = layer = None
            elif cmd == "layer":
                if pose is None:
                    err(n, "@layer must come after a @pose line")
                try:
                    x, y = int(parts[1]), int(parts[2])
                except (IndexError, ValueError):
                    err(n, "usage: @layer X Y [static|walk|tail|head]")
                kind = parts[3].lower() if len(parts) > 3 else "static"
                if kind not in LAYER_KINDS:
                    err(n, "unknown layer kind '%s'" % kind)
                layer = {"x": x, "y": y, "kind": kind, "frames": [[]]}
                pose.append(layer)
                rows = None if kind == "head" else layer["frames"][0]
            else:
                err(n, "unknown command '@%s'" % cmd)
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = (v.strip(), n)
            rows = None
            continue
        err(n, "cannot understand this line (art rows must start with '|')")

    skin = Skin(meta.get("name", (default_name, 0))[0])
    if "base" in meta:
        skin.inherit(load_base(meta["base"][0]))
    if "size" in meta:
        v, n = meta["size"]
        try:
            w, h = [int(p) for p in v.replace("x", " ").split()]
        except ValueError:
            err(n, "size must look like '22 6' (width height)")
        skin.width, skin.height = w, h
    if "palette" in meta:
        v, n = meta["palette"]
        for tok in v.split():
            try:
                k, c = tok.split("=")
                bold = c.endswith("b")
                num = int(c.rstrip("b"))
                assert len(k) == 1 and 0 <= num <= 255
            except Exception:
                err(n, "bad palette entry '%s' (use e.g. O=208 or W=255b)" % tok)
            skin.palette[k] = style(num, bold)
    for a in ANCHORS:
        if a in meta:
            v, n = meta[a]
            try:
                ax, ay = [int(p) for p in v.split()]
            except ValueError:
                err(n, "%s must look like '3 1' (x y inside the head)" % a)
            skin.anchors[a] = (ax, ay)
    if "eyes" in meta:
        v, n = meta["eyes"]
        for tok in v.split():
            k, _, c = tok.partition("=")
            if not c or len(c) > 2:
                err(n, "bad eyes entry '%s' (use e.g. happy=^ or wink=^-)" % tok)
            skin.eyes[k] = c
    if head is not None:
        skin.head = head
    skin.poses.update(poses)

    if skin.width <= 0 or skin.height <= 0:
        raise SkinError("%s: missing 'size: WIDTH HEIGHT'" % where)
    if not skin.head:
        raise SkinError("%s: missing @head" % where)
    for need in ("stand", "sit"):
        if need not in skin.poses:
            raise SkinError("%s: missing '@pose %s'" % (where, need))
    return skin

def load_skin(name_or_path, skins_dir, _chain=()):
    path = name_or_path
    if not os.path.isfile(path):
        path = os.path.join(skins_dir, name_or_path + ".cat")
    if not os.path.isfile(path):
        raise SkinError("skin '%s' not found (looked for %s)" % (name_or_path, path))
    key = os.path.abspath(path)
    if key in _chain:
        raise SkinError("skin '%s' inherits from itself" % name_or_path)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    name = os.path.splitext(os.path.basename(path))[0]
    return parse_skin(text, name, path,
                      lambda base: load_skin(base, skins_dir, _chain + (key,)))


def preview_skin(skin, color=True, accessory=None):
    """Every pose, every frame, facing right and left, as text lines."""
    out = ["=== skin '%s'  (%d x %d) ===" % (skin.name, skin.width, skin.height)]
    eyes = skin.eye_pair("normal")
    for pose in POSES + tuple(p for p in skin.poses if p not in POSES):
        real = pose
        while real not in skin.poses and real in FALLBACK:
            real = FALLBACK[real]
        note = "" if real == pose else "   (not drawn -> uses '%s')" % real
        if pose == "peek" and "peek" not in skin.poses:
            note = "   (not drawn -> head only)"
        out.append("-- %s%s" % (pose, note))
        grids = []
        warn = set()
        for i in range(skin.frame_count(pose)):
            for face in (1, -1):
                g = [[(" ", None)] * skin.width for _ in range(skin.height)]
                for (x, y, ch, st) in skin.cells(pose, i, i, eyes, face, accessory):
                    if 0 <= x < skin.width and 0 <= y < skin.height:
                        g[y][x] = (ch, st)
                    else:
                        warn.add("frame %d: cell (%d,%d) is outside the %dx%d box"
                                 % (i, x, y, skin.width, skin.height))
                grids.append(g)
        for y in range(skin.height):
            line = []
            for g in grids:
                s = []
                for ch, st in g[y]:
                    s.append(ansi(st) + ch + "\x1b[0m" if (color and st is not None) else ch)
                line.append("|" + "".join(s) + "|")
            out.append("  ".join(line))
        for w in sorted(warn):
            out.append("   WARNING: " + w)
    return out


# =====================================================================
#  Cat: movement + drawing shared by every personality
# =====================================================================
REST_STATES = ("sit", "look", "loaf", "watch", "walk")
BUSY_STATES = ("nuzzle", "nuzzled", "gather", "final", "enter", "peek", "peekgo",
               "peekout", "crouch", "pounce")
ACTIVE_STATES = ("zoom", "run", "stalk", "visit")


class Cat:
    ACCEL = 5.0

    def __init__(self, world, skin, name="", enter_at=20.0, enter_from="left",
                 speed=1.0, jump=1.0):
        self.w = world
        self.skin = skin
        self.name = name or skin.name
        self.W, self.H = skin.width, skin.height
        self.enter_at = enter_at
        self.enter_from = enter_from
        self.spd = speed
        self.jmp = jump
        self.x, self.y, self.face = -50.0, 25.5, 1
        self.z = self.vz = 0.0
        self.lift = 0.0
        self.vx = self.vy = 0.0
        self.accel = self.ACCEL
        self.state = "sit"
        self.st = 0.0
        self.dur = 1.0
        self.phase = 0.0
        self.tt = random.uniform(0, 3)
        self.blink = random.uniform(1.5, 4.0)
        self.visible = False
        self.path = []
        self.last = ""
        self.hold_off = 0.0
        self.partner = None
        self.seat_face = 1
        self.accessory = None     # set by the scene (e.g. a Santa hat)

    # ---------- helpers ----------
    def go(self, state, dur=0.0):
        self.state = state
        self.st = 0.0
        self.dur = dur
        self.accel = self.ACCEL

    def bounds(self):
        lo, hi = getattr(self.w, "ROAM", (0, self.w.CW))     # visible columns
        return lo + self.W / 2.0 + 1, hi - self.W / 2.0 - 1

    def lane(self):
        return random.uniform(self.w.FLOOR_MIN, self.w.FLOOR_MAX)

    def others(self):
        return [c for c in self.w.cats if c is not self and c.visible]

    def clear_of_others(self, tx, gap):
        return all(abs(tx - c.x) >= gap for c in self.others())

    def nearest(self):
        os_ = self.others()
        return min(os_, key=lambda c: abs(c.x - self.x)) if os_ else None

    def stop(self):
        self.vx = self.vy = 0.0
        self.path = []

    def steer(self, dt, tx, ty, speed):
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy * 2.0)
        if d < 0.35:
            return True
        sp = speed * min(1.0, 0.25 + d / 5.0)
        k = min(1.0, dt * self.accel)
        self.vx += (sp * dx / d - self.vx) * k
        self.vy += (sp * dy / d - self.vy) * k
        self.x += self.vx * dt
        self.y += self.vy * dt
        if abs(self.vx) > 0.6:
            self.face = 1 if self.vx > 0 else -1
        self.phase += math.hypot(self.vx, self.vy * 2.0) * dt
        return False

    def walk_path(self, dt):
        if not self.path:
            return True
        tx, ty, sp = self.path[0]
        if self.steer(dt, tx, ty, sp):
            self.path.pop(0)
            if not self.path:
                self.vx = self.vy = 0.0
                return True
        return False

    def jump(self, v):
        self.vz = v * self.jmp
        self.z = 0.01

    def on_land(self):
        pass

    def speed(self):
        return math.hypot(self.vx, self.vy * 2.0)

    def pick(self, options):
        options = [o for o in options if o[1] > 0 and o[0] != self.last]
        total = sum(w for _n, w in options)
        r = random.uniform(0, total)
        for name, w in options:
            r -= w
            if r <= 0:
                return name
        return options[-1][0]

    def head_pos(self):
        return self.x, self.y - self.z - self.lift - self.H + 1

    def hearts(self, rate=2.2):
        if int(self.st * rate) != int((self.st - self.dt) * rate):
            hx, hy = self.head_pos()
            self.w.fx.emit(hx + random.uniform(-2, 2), hy - 1, random.uniform(-0.5, 0.5),
                           -2.1, 2.2, self.w.heart, self.w.HEART_RAMP, 0.8)

    # ---------- lifecycle ----------
    def enter(self):
        CX = self.w.CX
        lo, hi = getattr(self.w, "ROAM", (0, self.w.CW))     # walk in from off-screen
        self.visible = True
        self.y = self.lane()
        if self.enter_from == "right":
            self.x, self.face = hi + self.W / 2.0 + 3, -1
            tx = CX + 22 + random.uniform(-3, 5)
        else:
            self.x, self.face = lo - self.W / 2.0 - 3, 1
            tx = CX - 21 - random.uniform(-3, 5)
        self.path = [(tx, self.y, self.enter_speed())]
        self.go("enter")

    def place(self, x, y):
        self.visible = True
        self.x, self.y = x, y
        self.face = 1 if x < self.w.CX else -1

    def to_final(self, x, y, face):
        self.stop()
        self.lift = 0.0
        self.seat_face = face
        self.path = [(x, y, self.enter_speed())]
        self.go("gather")

    def u_gather(self, dt):
        if self.walk_path(dt):
            self.face = self.seat_face
            self.go("final")

    def u_final(self, dt):
        pass

    def react_nuzzle(self, other):
        self.stop()
        self.face = 1 if other.x > self.x else -1
        self.go("nuzzled", 3.0)

    def u_nuzzled(self, dt):
        self.hearts()
        if self.st > self.dur:
            self.next()

    def follow(self, leader, dur):
        pass

    def update(self, dt):
        self.dt = dt
        self.st += dt
        self.tt += dt
        self.hold_off -= dt
        self.blink -= dt
        if self.blink < -0.14:
            self.blink = random.uniform(2.5, 5.0)
        if self.vz != 0.0 or self.z > 0.0:
            self.vz -= GRAVITY * dt
            self.z += self.vz * dt
            if self.z <= 0.0:
                self.z = 0.0
                self.vz = 0.0
                self.on_land()
        getattr(self, "u_" + self.state)(dt)
        if self.state != "enter":
            lo, hi = self.bounds()
            self.x = clamp(self.x, lo, hi)
        self.y = clamp(self.y, self.w.BACK_Y - 0.5, self.w.FLOOR_MAX + 0.4)

    def draw(self, cv):
        if not self.visible:
            return
        pose, walk, tail, eyes = self.look()
        if self.blink < 0 and eyes in ("normal", "wide", "wink"):
            eyes = "closed"
        cells = self.skin.cells(pose, walk, tail, self.skin.eye_pair(eyes), self.face,
                                self.accessory)
        left = int(round(self.x - self.W / 2.0))
        top = int(round(self.y - self.z - self.lift)) - self.H + 1
        for (x, y, ch, st) in cells:
            cv.put(left + x, top + y, ch, st, ch == " ")


# =====================================================================
#  "calm": slow, gentle, round tabby energy
# =====================================================================
class CalmCat(Cat):
    ACCEL = 3.2

    def enter_speed(self):
        return 5.5 * self.spd

    def look(self):
        tail = int(self.tt * 1.3)
        eyes = "normal"
        if self.state in ("nuzzle", "nuzzled", "final"):
            eyes = "happy"
        if self.state in ("look", "watch"):
            eyes = "wide"
        if self.state == "loaf":
            return ("sleep", 0, 0, "closed")
        if self.speed() > 0.8:
            return ("stand", int(self.phase / 1.2), int(self.tt * 2.2), eyes)
        return ("sit", 0, tail, eyes)

    def next(self, after_move=False):
        opts = [("sit", 3.0), ("look", 2.6), ("loaf", 0.0 if after_move else 2.0),
                ("walk", 0.0 if after_move else 3.5), ("trot", 0.0 if after_move else 1.2)]
        name = self.pick(opts)
        self.last = name
        lo, hi = self.bounds()
        if name == "sit":
            self.go("sit", random.uniform(3.0, 6.0))
        elif name == "look":
            self.face = 1 if self.x < self.w.CX else -1
            self.go("look", random.uniform(3.0, 5.0))
        elif name == "loaf":
            self.go("loaf", random.uniform(7.0, 11.0))
        else:
            tx = self.x
            for _ in range(10):
                if name == "walk":
                    tx = random.uniform(lo, hi)
                else:
                    tx = clamp(self.x + random.choice((-1, 1)) * random.uniform(10, 18), lo, hi)
                if abs(tx - self.x) > 7 and self.clear_of_others(tx, 15):
                    break
            sp = (4.0 if name == "walk" else 9.0) * self.spd
            self.path = [(tx, self.lane(), sp)]
            self.go("walk")

    def follow(self, leader, dur):
        if self.state in REST_STATES:
            self.stop()
            self.partner = leader
            self.go("follow", dur)

    def u_enter(self, dt):
        if self.walk_path(dt):
            self.face = 1 if self.x < self.w.CX else -1
            self.go("look", 3.0)

    def u_sit(self, dt):
        if self.st > self.dur:
            self.next()

    u_look = u_sit

    def u_loaf(self, dt):
        if int(self.st) != int(self.st - dt):
            hx, hy = self.head_pos()
            self.w.fx.emit(hx + 1, hy + 2, 0.6, -1.4, 2.4, random.choice("zZ"),
                           self.w.Z_RAMP, 0.6)
        if self.st > self.dur:
            self.next()

    def u_walk(self, dt):
        if self.walk_path(dt):
            self.next(after_move=True)

    def u_watch(self, dt):
        o = self.partner
        if o is not None:
            self.face = 1 if o.x > self.x else -1
        if self.st > self.dur:
            self.next()

    def u_follow(self, dt):
        o = self.partner
        if o is not None and o.visible:
            side = 1 if o.x > self.x else -1
            tx = clamp(o.x - side * 15, *self.bounds())
            self.steer(dt, tx, self.y, 8.5 * self.spd)
        if self.st > self.dur:
            self.stop()
            self.next(after_move=True)

    def update(self, dt):
        Cat.update(self, dt)
        if self.hold_off <= 0 and self.state in ("sit", "look", "loaf"):
            for o in self.others():
                if o.state in ACTIVE_STATES and abs(o.x - self.x) < 24:
                    self.hold_off = 6.0
                    self.partner = o
                    self.go("watch", 2.4)
                    break
        # gazing at the scene's centrepiece makes it sparkle (if it has one)
        if self.state == "look" and random.random() < dt * 0.9 and self.w.GAZE:
            gx, ghw, gy, gh = self.w.GAZE
            self.w.fx.emit(gx + random.uniform(-ghw, ghw), gy + random.uniform(0, gh),
                           0, 0, 0.7, random.choice("*+"), self.w.SPARK_RAMP)


# =====================================================================
#  "playful": quick, curious, mischievous
# =====================================================================
class PlayfulCat(Cat):
    ACCEL = 9.0

    def enter_speed(self):
        return 17.0 * self.spd

    def look(self):
        eyes = "normal"
        if self.state in ("visit", "stalk", "crouch", "pounce"):
            eyes = "wide"
        if self.state in ("nuzzle", "nuzzled", "final"):
            eyes = "happy"
        if self.state in ("peek", "sit", "final") and int(self.tt * 0.7) % 3 == 0:
            eyes = "wink"
        tail = int(self.tt * 4.0)
        sp = self.speed()
        if self.state == "crouch":
            return ("crouch", 0, tail, eyes)
        if self.state == "peek":
            return ("peek", 0, 0, eyes)
        if self.z > 0.05:
            return ("run", 0, tail, eyes)
        if sp > 7.0:
            return ("run", int(self.phase / 2.2), tail, eyes)
        if sp > 0.8:
            return ("stand", int(self.phase / 1.3), tail, eyes)
        if self.state in ("sit", "final", "nuzzled"):
            return ("sit", 0, tail, eyes)
        return ("stand", 0, tail, eyes)

    def props_up(self):
        """Things to stalk / hide behind: the scene's props (cx, w, h)."""
        return self.w.hideouts()

    def visit_candidates(self):
        return [c for c in self.others() if c.state not in BUSY_STATES]

    def next(self):
        name = self.pick([("run", 3.0), ("hop", 1.5), ("stalk", 2.0), ("peek", 2.0),
                          ("visit", 2.4 if self.visit_candidates() else 0.0),
                          ("zoom", 1.2), ("sit", 1.2)])
        self.last = name
        getattr(self, "begin_" + name)()

    def begin_sit(self):
        self.go("sit", random.uniform(1.4, 3.0))

    def begin_run(self, tx=None):
        lo, hi = self.bounds()
        if tx is None:
            tx = self.x
            for _ in range(10):
                tx = random.uniform(lo, hi)
                if abs(tx - self.x) > 10 and self.clear_of_others(tx, 14):
                    break
        self.path = [(clamp(tx, lo, hi), self.lane(), random.uniform(11.0, 15.0) * self.spd)]
        self.go("run")

    def begin_hop(self, n=None):
        self.hops = n if n else random.randint(1, 3)
        self.cool = 0.0
        self.go("hop")

    def begin_stalk(self):
        gs = self.props_up()
        if not gs:
            return self.begin_run()
        g = random.choice(gs)
        side = 1 if self.x > g.cx else -1
        lo, hi = self.bounds()
        self.target = g
        self.path = [(clamp(g.cx + side * (g.w / 2.0 + 11), lo, hi), 25.8, 6.5 * self.spd)]
        self.go("stalk")

    def begin_peek(self):
        gs = [g for g in self.props_up() if g.h >= 4]
        if not gs:
            return self.begin_run()
        g = random.choice(gs)
        side = -1 if self.x < g.cx else 1
        lo, hi = self.bounds()
        sx = clamp(g.cx + side * (g.w / 2.0 + 10), lo, hi)
        self.peek_at = (g, sx)
        by = self.w.BACK_Y
        self.path = [(sx, by, 10.0 * self.spd), (g.cx, by, 6.5 * self.spd)]
        self.go("peekgo")

    def begin_visit(self):
        cands = self.visit_candidates()
        if not cands:
            return self.begin_run()
        self.partner = random.choice(cands)
        self.go("visit")

    def begin_zoom(self):
        lo, hi = self.bounds()
        o = self.partner if (self.partner and self.partner.visible) else self.nearest()
        go_left = o.x > self.w.CX if o is not None else random.random() < 0.5
        tx = lo + random.uniform(0, 6) if go_left else hi - random.uniform(0, 6)
        self.path = [(tx, self.lane(), 19.0 * self.spd)]
        self.go("zoom")
        self.accel = 11.0
        if o is not None:
            o.follow(self, 3.2)

    def follow(self, leader, dur):
        # a playful friend doesn't trot behind - it races after the leader
        if self.state in ("sit", "hop", "run") and leader.path:
            side = 1 if leader.path[-1][0] > self.x else -1
            self.begin_run(leader.path[-1][0] - side * 14)

    # ----- state updaters -----
    def u_enter(self, dt):
        if self.walk_path(dt):
            self.begin_hop(2)

    def u_sit(self, dt):
        if self.st > self.dur:
            self.next()

    def u_run(self, dt):
        if self.walk_path(dt):
            if random.random() < 0.45:
                self.begin_hop(random.randint(1, 2))
            else:
                self.next()

    def u_zoom(self, dt):
        if self.walk_path(dt):
            self.begin_hop(random.randint(1, 2))

    def u_hop(self, dt):
        self.cool -= dt
        if self.z <= 0.0 and self.cool <= 0.0:
            if self.hops > 0:
                self.hops -= 1
                self.jump(13.0)
                self.cool = 0.25
            else:
                self.next()

    def u_stalk(self, dt):
        if self.walk_path(dt):
            self.face = 1 if self.target.cx > self.x else -1
            self.go("crouch", random.uniform(1.0, 1.7))

    def u_crouch(self, dt):
        if self.st > self.dur:
            self.jvx = self.face * 9.0
            self.jump(11.0)
            self.go("pounce")

    def u_pounce(self, dt):
        self.x += self.jvx * dt

    def on_land(self):
        if self.state == "pounce":
            self.vx = 0.0
            self.go("sit", random.uniform(1.2, 2.2))

    def u_peekgo(self, dt):
        if self.walk_path(dt):
            self.go("peek", random.uniform(4.5, 6.5))

    def u_peek(self, dt):
        target = 2.0 if (self.st % 2.4) > 0.9 else 0.0
        self.lift += (target - self.lift) * min(1.0, dt * 7.0)
        o = self.nearest()
        if o is not None:
            self.face = 1 if o.x > self.x else -1
        if self.st > self.dur:
            g, sx = self.peek_at
            self.lift = 0.0
            by = self.w.BACK_Y
            self.path = [(sx, by, 8.0 * self.spd), (sx, 25.8, 11.0 * self.spd)]
            self.go("peekout")

    def u_peekout(self, dt):
        if self.walk_path(dt):
            if self.visit_candidates() and random.random() < 0.6:
                self.begin_visit()
            else:
                self.begin_zoom()

    def u_visit(self, dt):
        o = self.partner
        if o is None or not o.visible or o.state in BUSY_STATES:
            return self.begin_run()
        side = -1 if self.x < o.x else 1
        tx = clamp(o.x + side * (self.W + o.W) / 2.6, *self.bounds())
        self.accel = 7.0
        if self.steer(dt, tx, o.y, 10.0 * self.spd):
            self.stop()
            self.face = -side
            self.go("nuzzle", 3.2)
            self.hops = 2
            self.cool = 0.1
            o.react_nuzzle(self)

    def u_nuzzle(self, dt):
        self.cool -= dt
        if self.z <= 0.0 and self.cool <= 0.0 and self.hops > 0:
            self.hops -= 1
            self.jump(9.0)
            self.cool = 0.5
        self.hearts()
        if self.st > self.dur:
            self.begin_zoom()


# =====================================================================
#  a person: you two, walking around the scene with the cats
# =====================================================================
class Person(Cat):
    """Poses (skins/girlfriend.cat, boyfriend.cat): "stand" (walking),
    "sit" (standing still - people don't sit down here) and "peace"
    (a peace sign). The surprise puts the people in the middle, facing
    each other (BaseScene.seats)."""
    ACCEL = 4.0
    is_person = True

    def enter_speed(self):
        return 6.0 * self.spd

    def enter(self):
        Cat.enter(self)
        tx = self.w.CX + (16 if self.enter_from == "right" else -16) + random.uniform(-3, 3)
        self.path = [(tx, self.y, self.enter_speed())]

    def look(self):
        eyes = "normal"
        if self.state in ("pair", "final", "nuzzled", "gather"):
            eyes = "happy"
        if self.state == "peace":
            return ("peace", 0, 0, "wink")
        if self.speed() > 0.8:
            return ("stand", int(self.phase / 1.3), 0, eyes)
        return ("sit", 0, 0, eyes)

    def partner_person(self):
        ps = [c for c in self.others() if getattr(c, "is_person", False)]
        return ps[0] if ps else None

    def next(self, after_move=False):
        mate = self.partner_person()
        free = mate is not None and mate.state in ("idle", "look", "stroll")
        opts = [("idle", 2.5), ("look", 2.4), ("peace", 1.5),
                ("stroll", 0.0 if after_move else 3.0), ("pair", 2.5 if free else 0.0)]
        name = self.pick(opts)
        self.last = name
        lo, hi = self.bounds()
        if name == "idle":
            self.go("idle", random.uniform(2.5, 5.0))
        elif name == "look":
            self.face = 1 if self.x < self.w.CX else -1
            self.go("look", random.uniform(3.0, 5.0))
        elif name == "peace":
            self.stop()
            self.go("peace", random.uniform(2.2, 3.2))
        elif name == "pair":
            side = -1 if self.x < mate.x else 1
            tx = clamp(mate.x + side * (self.W + 1), lo, hi)
            self.partner = mate
            self.path = [(tx, mate.y, 5.0 * self.spd)]
            self.go("goto")
        else:
            tx = self.x
            for _ in range(10):
                tx = random.uniform(lo, hi)
                if abs(tx - self.x) > 8 and self.clear_of_others(tx, 6):
                    break
            self.path = [(tx, self.lane(), 4.5 * self.spd)]
            self.go("stroll")

    def u_enter(self, dt):
        if self.walk_path(dt):
            self.face = 1 if self.x < self.w.CX else -1
            self.go("look", 2.5)

    def u_idle(self, dt):
        if self.st > self.dur:
            self.next()

    u_look = u_idle

    def u_peace(self, dt):
        if int(self.st * 2.0) != int((self.st - dt) * 2.0):
            hx, hy = self.head_pos()
            self.w.fx.emit(hx + self.face * 5 + random.uniform(-1, 1), hy + 1, 0, -1.0, 0.8,
                           random.choice("*+"), self.w.SPARK_RAMP)
        if self.st > self.dur:
            self.next()

    def u_stroll(self, dt):
        if self.walk_path(dt):
            self.next(after_move=True)

    def u_goto(self, dt):
        mate = self.partner
        if mate is None or not mate.visible or mate.state in ("gather", "final"):
            return self.next(after_move=True)
        if self.walk_path(dt):
            self.face = 1 if mate.x > self.x else -1
            self.go("pair", 4.0)
            if mate.state in ("idle", "look", "stroll"):
                mate.stop()
                mate.face = -self.face
                mate.partner = self
                mate.go("pair", 4.0)

    def u_pair(self, dt):
        self.hearts(1.2)
        if self.st > self.dur:
            self.next()

    def u_final(self, dt):
        if self.w.phase == "hold":
            self.hearts(0.8)


PERSONALITIES = {"calm": CalmCat, "playful": PlayfulCat}

MAX_CATS = 3            # how many cats may be on stage together
MAX_PEOPLE = 2          # ... and people


# =====================================================================
#  cats.json
# =====================================================================
def read_config(path):
    if not os.path.isfile(path):
        raise ConfigError("cat config not found: %s" % path)
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except ValueError as e:
        raise ConfigError("%s is not valid JSON: %s" % (path, e))
    if not isinstance(cfg.get("cats"), list) or not cfg["cats"]:
        raise ConfigError("%s: needs a non-empty \"cats\": [ ... ] list" % path)
    skins_dir = os.path.join(os.path.dirname(os.path.abspath(path)),
                             cfg.get("skins_dir", "skins"))
    return cfg, skins_dir


def select_cats(path, names):
    """Names (as in cats.json) -> their positions in the "cats" list."""
    cfg, _d = read_config(path)
    all_names = [c.get("name", c.get("skin", "")) for c in cfg["cats"]]
    out = []
    for n in names:
        n = n.strip()
        if n not in all_names:
            raise ConfigError("no cat called '%s' in %s (cats: %s)"
                              % (n, path, ", ".join(all_names)))
        out.append(all_names.index(n))
    check_count(len(out))
    return out


def check_count(n):
    if n > MAX_CATS:
        raise ConfigError("at most %d cats can be on stage together (%d chosen) "
                          "/ 最多只能選 %d 隻貓" % (MAX_CATS, n, MAX_CATS))


def load_cats(path, world, accessory=None, only=None, only_people=None):
    """Build the cats, then the people. `only` / `only_people` = positions in
    the "cats" / "people" lists to use (ignores "enabled"); None = every
    enabled one."""
    cfg, skins_dir = read_config(path)
    cats = []
    if only is not None:
        entries = [cfg["cats"][i] for i in only if 0 <= i < len(cfg["cats"])]
    else:
        entries = [c for c in cfg["cats"] if c.get("enabled", True)]
    check_count(len(entries))
    for i, c in enumerate(entries):
        if "skin" not in c:
            raise ConfigError("cat #%d in %s has no \"skin\"" % (i + 1, path))
        pers = c.get("personality", "calm")
        if pers not in PERSONALITIES:
            raise ConfigError("cat '%s': unknown personality '%s' (choose: %s)"
                              % (c.get("name", i + 1), pers, ", ".join(PERSONALITIES)))
        try:
            skin = load_skin(c["skin"], skins_dir)
        except SkinError as e:
            raise ConfigError(str(e))
        default_from = "right" if pers == "playful" else "left"
        cats.append(PERSONALITIES[pers](
            world, skin, name=c.get("name", ""),
            enter_at=float(c.get("enter_at", 18.0 + 4.0 * i)),
            enter_from=c.get("enter_from", default_from),
            speed=float(c.get("speed", 1.0)),
            jump=float(c.get("jump", 1.0))))
        cats[-1].accessory = accessory
    cats += load_people(cfg, path, skins_dir, world, accessory, only_people)
    if not cats:
        raise ConfigError("%s: no cat selected / every cat is disabled" % path)
    return cats


def people_entries(cfg, path):
    people = cfg.get("people", [])
    if not isinstance(people, list):
        raise ConfigError("%s: \"people\" must be a list [ ... ]" % path)
    return people


def load_people(cfg, path, skins_dir, world, accessory=None, only=None):
    """The "people" list of cats.json -> Person characters."""
    people = people_entries(cfg, path)
    if only is not None:
        entries = [people[i] for i in only if 0 <= i < len(people)]
    else:
        entries = [p for p in people if p.get("enabled", True)]
    if len(entries) > MAX_PEOPLE:
        raise ConfigError("at most %d people can be on stage together / 最多 %d 個人"
                          % (MAX_PEOPLE, MAX_PEOPLE))
    out = []
    for i, p in enumerate(entries):
        if "skin" not in p:
            raise ConfigError("person #%d in %s has no \"skin\"" % (i + 1, path))
        try:
            skin = load_skin(p["skin"], skins_dir)
        except SkinError as e:
            raise ConfigError(str(e))
        out.append(Person(world, skin, name=p.get("name", ""),
                          enter_at=float(p.get("enter_at", 14.0 + 2.0 * i)),
                          enter_from=p.get("enter_from", "left" if i == 0 else "right"),
                          speed=float(p.get("speed", 1.0))))
        out[-1].accessory = accessory
    return out

def config_skins(path):
    cfg, skins_dir = read_config(path)
    # preview shows every cat (and person) in the config, also "enabled": false ones
    return [load_skin(c["skin"], skins_dir)
            for c in cfg["cats"] + people_entries(cfg, path) if "skin" in c]
