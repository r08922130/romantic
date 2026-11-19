# -*- coding: utf-8 -*-
"""
terminal.py - the ONE animation loop all scenes share
=====================================================

  enable_vt()  Windows: turn on ANSI/VT, UTF-8 output, 1 ms timer
  Keys         non-blocking key reading (Windows + POSIX)
  run()        alternate screen, fixed-fps loop, single write() per frame,
               terminal-too-small notice, Ctrl+C / q / Esc to quit
  snapshot()   render a scene at time T as plain text (for tests)

  run_menu()   the start menu's key / screen loop (engine/menu.py: Menu)

Keys:  q / Esc / Ctrl+C = quit,  s = surprise now,  n = next scene
"""
import os
import random
import shutil
import sys
import time

from .render import MIN_H, MIN_W, RESET, Canvas, pick_scale, view_canvas


def enable_vt():
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            h = k.GetStdHandle(-11)
            m = ctypes.c_uint32()
            if k.GetConsoleMode(h, ctypes.byref(m)):
                k.SetConsoleMode(h, m.value | 0x0004 | 0x0001)
            k.SetConsoleOutputCP(65001)
            ctypes.windll.winmm.timeBeginPeriod(1)
        except Exception:
            os.system("")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def maximize_window():
    """Windows console (conhost) only: maximise the window, so the scene can
    be drawn at its biggest size (see render.pick_scale; the font is left
    alone). Returns a function that puts the window back (or None).

    Windows Terminal does not let programs resize its window: run.bat opens
    the classic console window for this. Mac: run.command zooms Terminal."""
    if os.name != "nt" or (os.environ.get("WT_SESSION") and
                           not os.environ.get("ROMANCE_CONHOST")):
        return None
    try:
        import ctypes
        from ctypes import wintypes
        k = ctypes.windll.kernel32
        user = ctypes.windll.user32
        k.GetConsoleWindow.restype = wintypes.HWND
        hwnd = k.GetConsoleWindow()
        if not hwnd:
            return None
        cls = ctypes.create_unicode_buffer(64)
        user.GetClassNameW(hwnd, cls, 64)
        if cls.value == "PseudoConsoleWindow":   # inside Windows Terminal etc.
            return None
        if user.IsZoomed(hwnd):
            return None
        user.ShowWindow(hwnd, 3)                 # SW_MAXIMIZE

        def restore():
            try:
                user.ShowWindow(hwnd, 9)         # SW_RESTORE
            except Exception:
                pass
        return restore
    except Exception:
        return None

class Keys:
    def __init__(self):
        self.win = os.name == "nt"
        self.old = None
        self.buf = b""          # POSIX: raw bytes read but not yet turned into keys
        if self.win:
            import msvcrt
            self.m = msvcrt
        else:
            try:
                import termios
                import tty
                self.fd = sys.stdin.fileno()
                self.old = termios.tcgetattr(self.fd)
                tty.setcbreak(self.fd)
                self.termios = termios
            except Exception:
                self.old = None

    ARROWS_WIN = {"H": "up", "P": "down", "K": "left", "M": "right"}
    ARROWS_ANSI = {"A": "up", "B": "down", "D": "left", "C": "right"}

    def poll(self):
        """One key: a lower-case character, or 'up' / 'down' / 'left' / 'right'."""
        try:
            if self.win:
                if self.m.kbhit():
                    c = self.m.getwch()
                    if c in ("\x00", "\xe0"):
                        return self.ARROWS_WIN.get(self.m.getwch())
                    return c.lower()
            elif self.old is not None:
                return self.poll_posix()
        except Exception:
            return None
        return None

    def poll_posix(self):
        # Read raw bytes from the terminal ourselves: going through sys.stdin
        # would let Python buffer a whole arrow-key sequence (ESC [ B), after
        # which select() sees nothing left and the ESC looks like the Esc key.
        import select
        if not self.buf and select.select([self.fd], [], [], 0)[0]:
            self.buf += os.read(self.fd, 1024)
        return parse_key(self)

    def more(self, wait=0.03):
        import select
        if select.select([self.fd], [], [], wait)[0]:
            self.buf += os.read(self.fd, 1024)
            return True
        return False

    def close(self):
        if self.old is not None:
            try:
                self.termios.tcsetattr(self.fd, self.termios.TCSADRAIN, self.old)
            except Exception:
                pass


def parse_key(src):
    """Take one key off src.buf (bytes from a POSIX terminal).
    src.more() may read a little more input (to finish an escape sequence).
    Returns 'up' / 'down' / 'left' / 'right', a lower-case character, or None."""
    b = src.buf
    if not b:
        return None
    if b[:1] == b"\x1b":
        if len(b) < 3 and src.more():
            b = src.buf
        if b[1:2] in (b"[", b"O") and len(b) >= 3:          # arrows: ESC [ A / ESC O A
            src.buf = b[3:]
            return Keys.ARROWS_ANSI.get(chr(b[2]))
        src.buf = b[1:]
        return "\x1b"                                       # a real Esc
    n = 1                                                   # one UTF-8 character
    if b[0] >= 0xF0:
        n = 4
    elif b[0] >= 0xE0:
        n = 3
    elif b[0] >= 0xC0:
        n = 2
    if len(b) < n and src.more():
        b = src.buf
    src.buf = b[n:]
    try:
        return b[:n].decode("utf-8").lower()
    except UnicodeDecodeError:
        return None


def too_small(out, need_w, need_h, cols, rows):
    lines = ["Terminal too small!  /  視窗太小了",
             "Need at least %d x %d, now %d x %d" % (need_w, need_h, cols, rows),
             "Please enlarge the window or press Ctrl + mouse-wheel to shrink the font.",
             "請拉大視窗，或按 Ctrl+滾輪縮小字體。"]
    buf = ["\x1b[2J"]
    for i, ln in enumerate(lines):
        buf.append("\x1b[%d;1H%s" % (i + 1, ln))
    out.write("".join(buf))
    out.flush()


def run(manager, name, fps, title=None):
    """The shared main loop. `manager` builds scenes (and switches with 'n')."""
    enable_vt()
    out = sys.stdout
    scene = manager.create(name)
    cv = None
    keys = Keys()
    if title:
        out.write("\x1b]0;%s\x07" % title)        # terminal window / tab title
    out.write("\x1b[?1049h\x1b[?25l\x1b[2J")
    out.flush()
    frame = 1.0 / max(5, fps)
    last = time.perf_counter()
    nxt = last
    size = None
    try:
        while True:
            now = time.perf_counter()
            dt = min(now - last, 0.1)
            last = now
            k = keys.poll()
            if k in ("q", "\x1b", "\x03"):
                break
            if k == "s":
                scene.trigger_surprise()
            elif k == "n" and len(manager.names()) > 1:
                scene = manager.create(manager.next_name(scene.name))
                size = None                      # force a full clear + new canvas
            elif k and len(k) == 1:
                scene.on_key(k)
            sz = shutil.get_terminal_size((scene.CW, scene.CH))
            if sz != size:
                size = sz
                out.write("\x1b[2J")
                # the canvas fills the window (the stage centred, standing on
                # the bottom edge), drawn 1 / 1.5 / 2 times bigger if it fits;
                # None = smaller than MIN_W x MIN_H
                k = pick_scale(sz.columns, sz.lines, scene.MAX_SCALE)
                cv = view_canvas(sz.columns, sz.lines, scene.CW, scene.CH, k=k)
            if cv is None:
                too_small(out, MIN_W, MIN_H, sz.columns, sz.lines)
                time.sleep(0.25)
                last = time.perf_counter()
                nxt = last
                continue
            scene.update(dt)
            scene.draw(cv)
            out.write(cv.frame(sz.columns, sz.lines))
            out.flush()
            nxt += frame
            delay = nxt - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            else:
                nxt = time.perf_counter()
    except KeyboardInterrupt:
        pass
    finally:
        keys.close()
        out.write(RESET + "\x1b[?25h\x1b[?1049l")
        out.write("%s\n" % scene.farewell())
        out.flush()


def run_menu(menu, fps=30):
    """Show the menu until the user starts (-> (scene, [cats])) or quits (-> None)."""
    enable_vt()
    out = sys.stdout
    keys = Keys()
    cv = Canvas()
    out.write("\x1b]0;%s\x07\x1b[?1049h\x1b[?25l\x1b[2J" % (menu.title or "menu"))
    out.flush()
    t0 = last = time.perf_counter()
    size = None
    result = ("quit",)
    try:
        while True:
            sz = shutil.get_terminal_size((cv.w, cv.h))
            visible = sz.columns >= cv.w and sz.lines >= cv.h
            k = keys.poll()
            while k is not None:
                if visible or k in ("q", "\x1b", "\x03"):  # no blind choices while hidden
                    r = menu.handle(k)
                    if r is not None:
                        result = r
                        return None if r[0] == "quit" else r[1:]
                k = keys.poll()
            if sz != size:
                size = sz
                out.write("\x1b[2J")
            if not visible:
                too_small(out, cv.w, cv.h, sz.columns, sz.lines)
                time.sleep(0.25)
                continue
            now = time.perf_counter()
            menu.draw(cv, now - t0, now - last)
            last = now
            out.write(cv.frame(sz.columns, sz.lines))
            out.flush()
            time.sleep(1.0 / fps)
    except KeyboardInterrupt:
        result = ("quit",)
        return None
    finally:
        keys.close()
        if result[0] == "quit":
            out.write("\x1b[0m\x1b[?25h\x1b[?1049l")
            out.flush()


def simulate(scene, seconds, fps=30):
    """Advance a scene by `seconds` with a fixed time step."""
    for _ in range(int(seconds * fps)):
        scene.update(1.0 / fps)


def snapshot(manager, name, seconds, seed=None, size=None, scale=None):
    """Render scene `name` after `seconds` as plain text lines.
    size = (cols, lines) renders it as in a window of that size (drawn
    bigger if it fits; scale=1 forces the normal size)."""
    if seed is not None:
        random.seed(seed)
    scene = manager.create(name)
    cv = Canvas(scene.CW, scene.CH)
    if size is not None:
        k = scale or pick_scale(size[0], size[1], scene.MAX_SCALE)
        cv = view_canvas(size[0], size[1], scene.CW, scene.CH, k=k)
        if cv is None:
            raise ValueError("window too small: at least %d x %d" % (MIN_W, MIN_H))
        scene.set_scale(k)
        scene.set_view(cv.view())
    simulate(scene, seconds)
    scene.draw(cv)
    return cv.plain_rows()
