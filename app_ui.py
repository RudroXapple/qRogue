"""
Home screen (connected state) of the qFlipper-style app.
Geometry/colours from qFlipper's HomeOverlay.qml, DeviceActions.qml,
MainButton.qml, Button.qml, TextLabel.qml. Needs main.py and flipper_link.py.
Buttons that need real Flipper functions only show "coming soon".
"""
import os
import threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.properties import BooleanProperty
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.utils import get_color_from_hex as hexc

from flipper_link import FlipperLink
from main import (BASE_H, BASE_W, BLACK, DARKORANGE1, FONT, LIGHTORANGE2,
                  LOG_LINES, MEDIUMORANGE3, GridLines, OutlineButton, Panel,
                  Stage, StageLabel, asset, log, register_fonts, vgradient)

GREEN = hexc("#2ed832")

# (normal, down, disabled) for each part, from Button.qml / MainButton.qml
STYLES = {
    "default": dict(fg=("#fe8a2c", "#491d00", "#9e5823"),
                    bg=("#491d00", "#fe8a2c", "#3a1f10"),
                    stroke=("#fe8a2c", "#fe8a2c", "#9e5823")),
    "green": dict(fg=("#2ed832", "#0c160c", "#9e5823"),
                  bg=("#203812", "#2ed832", "#3a1f10"),
                  stroke=("#2ed832", "#2ed832", "#9e5823")),
    "red": dict(fg=("#ff5b27", "#451a0e", "#9e5823"),
                bg=("#451a0e", "#ff5b27", "#3a1f10"),
                stroke=("#ff5b27", "#ff5b27", "#9e5823")),
}

ORDER = ["hardware_model", "hardware_name", "hardware_ver", "hardware_region",
         "firmware_version", "firmware_build_date", "firmware_commit",
         "firmware_branch", "radio_alive"]


def register_haxr():
    FONT.setdefault("haxr", "Roboto")
    path = asset("fonts", "haxrcorp-4089.ttf")
    if os.path.exists(path):
        LabelBase.register(name="HaxrCorp", fn_regular=path)
        FONT["haxr"] = "HaxrCorp"


def hint(widget, x, y, w, h):
    """Set position by desktop pixels (top-left origin) without adding."""
    widget.size_hint = (w / BASE_W, h / BASE_H)
    widget.pos_hint = {"x": x / BASE_W, "y": 1 - (y + h) / BASE_H}
    return widget


class QButton(Button):
    checked = BooleanProperty(False)

    def __init__(self, stage, text, style="default", px=32, font="haxr",
                 radius=5, border_w=2, icon=None, **kw):
        super().__init__(text=text, background_normal="", background_down="",
                         background_color=(0, 0, 0, 0), **kw)
        self.stage, self.style = stage, STYLES[style]
        self.px, self._r, self._bw = px, radius, border_w
        self.font_name = FONT.get(font, "Roboto")
        with self.canvas.before:
            self._bgc = Color()
            self._bg = RoundedRectangle()
            self._lnc = Color()
            self._ln = Line(width=1)
        self._icon = None
        if icon:
            path, self._iw, self._ih = icon
            self._icon = Image(source=path, fit_mode="fill", size_hint=(None, None))
            self.add_widget(self._icon)
        self.bind(pos=self._draw, size=self._draw, state=self._draw,
                  disabled=self._draw, checked=self._draw)
        stage.bind(scale=self._draw)
        self._draw()

    def _draw(self, *args):
        s = self.stage.scale
        i = 2 if self.disabled else (1 if (self.state == "down" or self.checked) else 0)
        st = self.style
        self._bgc.rgba = hexc(st["bg"][i])
        self._bg.pos, self._bg.size = self.pos, self.size
        self._bg.radius = [self._r * s]
        self._lnc.rgba = hexc(st["stroke"][i])
        self._ln.width = max(self._bw * s, 0.5)
        self._ln.rounded_rectangle = (*self.pos, *self.size, self._r * s)
        self.color = hexc(st["fg"][i])
        self.font_size = self.px * s
        if self._icon is not None:
            self._icon.color = hexc(st["fg"][i])
            self._icon.size = (self._iw * s, self._ih * s)
            ix = (self.x + 8 * s) if self.text else (self.center_x - self._icon.width / 2)
            self._icon.pos = (ix, self.center_y - self._icon.height / 2)


class QLink(Button):
    def __init__(self, stage, text, color="#fe8a2c", px=24, **kw):
        super().__init__(text="[u]%s[/u]" % text, markup=True,
                         background_normal="", background_down="",
                         background_color=(0, 0, 0, 0), color=hexc(color), **kw)
        self.stage, self.px = stage, px
        self.font_name = FONT["haxr"]
        stage.bind(scale=self._f)
        self._f()

    def _f(self, *args):
        self.font_size = self.px * self.stage.scale


class HomeApp(App):
    def build(self):
        register_fonts()
        register_haxr()
        Window.clearcolor = BLACK
        st = self.st = Stage()
        self.connected = False
        self.tab_index = 0
        self.log_widgets = []

        st.place(Panel(st, fill=BLACK, border=MEDIUMORANGE3, border_w=2,
                       radius=10), 0, 0, BASE_W, BASE_H)

        BW = 3
        cw, ch = 800 + BW * 2, 390 + BW * 2
        cx, cy = (BASE_W - cw) / 2, 38
        self.cx, self.cy, self.cw, self.ch = cx, cy, cw, ch

        def C(x, y, w, h):
            return cx + x, cy + y, w, h
        self.C = C

        st.place(Panel(st, texture=vgradient("#090400", "#210F00"),
                       border=LIGHTORANGE2, border_w=BW, radius=9), cx, cy, cw, ch)
        st.place(GridLines(st, cw, ch, BW), cx, cy, cw, ch)
        st.place(StageLabel(st, 16, text="0.0.0", halign="right", valign="top",
                            color=(*LIGHTORANGE2[:3], 0.5), font_name=FONT["mono"]),
                 *C(cw - 16 - 120, 10, 120, 24))

        # waiting-state pictures (they move when a Flipper is connected)
        self.flipper = st.place(Image(source=asset("gfx", "flipper.png"), fit_mode="fill"),
                                *C(216, 82, 360, 156))
        self.screen = st.place(Image(source=asset("gfx", "default.png"), fit_mode="fill"),
                               *C(216 + 93, 82 + 26, 128, 64))
        self.plug = st.place(Image(source=asset("gfx", "typec.png"), fit_mode="fill"),
                             *C(cw - 216, 145, 159, 37))
        self.headline = st.place(StageLabel(st, 48, text="Connect your Flipper",
                                            halign="center", valign="top",
                                            color=LIGHTORANGE2, font_name=FONT["title"]),
                                 *C(0, 264, cw, 60))
        self.waiting_only = [self.plug, self.headline]

        # footer
        fy = cy + ch + 13
        logs = OutlineButton(st, text="LOGS")
        logs.bind(on_release=self.toggle_logs)
        st.place(logs, cx, fy, 110, 42)
        sx, sw = cx + 110 + 15, cw - 110 - 15
        st.place(Panel(st, fill=DARKORANGE1), sx, fy, sw, 42)
        st.place(Image(source=asset("gfx", "info-small.png"), fit_mode="fill",
                       color=LIGHTORANGE2), sx + 10, fy + 10, 22, 22)
        self.status = st.place(StageLabel(st, 18, text="Waiting for devices ...",
                                          halign="left", valign="middle",
                                          color=LIGHTORANGE2, font_name=FONT["ui"]),
                               sx + 10 + 22 + 10, fy, sw - 42, 42)

        self._build_home()
        self.dpad = []
        for name, px, py, bw, bh in (
                ("up", 274, 32, 30, 22), ("down", 274, 84, 30, 22),
                ("left", 248, 58, 22, 30), ("right", 300, 58, 22, 30),
                ("ok", 274, 58, 26, 26), ("back", 326, 83, 30, 30)):
            b = Button(text="", background_normal="", background_down="",
                       background_color=(0, 0, 0, 0))
            b.bind(on_release=lambda w, n=name: self._key(n))
            hint(b, 403 + px - bw / 2 + self.cx, 82 + py - bh / 2 + self.cy, bw, bh)
            self.dpad.append(b)
        self.link = FlipperLink(self.on_state, log)
        self.link.on_frame = self._frame
        Clock.schedule_interval(self.link.poll, 1.0)
        Clock.schedule_interval(self._refresh_log, 0.5)
        return st

    # ---------- Home overlay (HomeOverlay.qml) ----------
    def _build_home(self):
        st, C = self.st, self.C
        self.home = []

        def add(w, x, y, ww, hh, group=None):
            hint(w, *C(x, y, ww, hh))
            (self.home if group is None else group).append(w)
            return w

        # tab pane first, so the tabs draw above its top edge
        add(Panel(st, fill=(0, 0, 0, 0.35), border=LIGHTORANGE2, border_w=2,
                  radius=5), 28, 68, 318, 232)

        self.tab_btns = []
        for i, (name, w, h) in enumerate([("info", 25, 25), ("wrench", 27, 27),
                                          ("file", 23, 29)]):
            b = QButton(st, "", icon=(asset("gfx", name + ".png"), w, h))
            b.bind(on_release=lambda _b, i=i: self.select_tab(i))
            add(b, 28 + i * 52, 28, 52, 42)
            self.tab_btns.append(b)

        self.name_lbl = add(StageLabel(st, 48, text="", halign="right",
                                       valign="middle", color=LIGHTORANGE2,
                                       font_name=FONT["title"]), 286, 19, 300, 56)
        add(Image(source=asset("gfx", "usb.png"), fit_mode="fill", color=GREEN),
            594, 27, 18, 10)
        add(StageLabel(st, 18, text="Connected", halign="left", valign="middle",
                       color=GREEN, font_name=FONT["haxr"]), 618, 22, 160, 20)
        self.path_lbl = add(StageLabel(st, 14, text="", halign="left",
                                       valign="middle", color=GREEN,
                                       font_name=FONT["mono"]), 594, 42, 210, 18)

        self.update_btn = QButton(st, "No data", px=48, font="title",
                                  radius=7, border_w=3)
        self.update_btn.disabled = True
        add(self.update_btn, 450, 265, 280, 56)
        link = QLink(st, "Install from file")
        link.bind(on_release=lambda *_: self.say("Install from file: coming soon"))
        add(link, 596, 326, 170, 28)

        # tab 0: device info
        g0, g1, g2 = [], [], []
        self.tab_groups = [g0, g1, g2]
        self.info_lbl = add(StageLabel(st, 15, text="", halign="left", valign="top",
                                       color=LIGHTORANGE2, font_name=FONT["mono"]),
                            40, 80, 296, 212, g0)

        # tab 1: advanced controls (DeviceActions.qml)
        add(StageLabel(st, 20, text="Firmware update channel", halign="left",
                       valign="middle", color=LIGHTORANGE2, font_name=FONT["haxr"]),
            38, 78, 298, 26, g1)
        combo = QButton(st, "Release", px=24)
        combo.bind(on_release=lambda *_: self.say("Update channel: coming soon"))
        add(combo, 38, 108, 298, 42, g1)
        add(StageLabel(st, 20, text="Backup & Restore", halign="left",
                       valign="middle", color=LIGHTORANGE2, font_name=FONT["haxr"]),
            38, 160, 298, 26, g1)
        for text, icon, style, x, y in [("Backup", "backup", "default", 38, 192),
                                        ("Restore", "restore", "default", 192, 192),
                                        ("Erase", "trash", "red", 38, 244),
                                        ("Reinstall", "update", "default", 192, 244)]:
            b = QButton(st, text, style=style, px=24,
                        icon=(asset("gfx", icon + ".png"), 18, 20))
            b.bind(on_release=lambda _b, t=text: self.say("%s: coming soon" % t))
            if text == "Reinstall":
                b.disabled = True
            add(b, x, y, 144, 42, g1)

        # tab 2: file manager placeholder
        add(StageLabel(st, 24, text="File manager\ncoming soon", halign="center",
                       valign="middle", color=LIGHTORANGE2, font_name=FONT["haxr"]),
            28, 68, 318, 232, g2)

    def _vis(self, widgets, on):
        for w in widgets:
            if on and w.parent is None:
                self.st.add_widget(w)
            elif not on and w.parent is not None:
                self.st.remove_widget(w)

    def select_tab(self, i):
        self.tab_index = i
        self._refresh_tabs()

    def _refresh_tabs(self):
        for j, b in enumerate(self.tab_btns):
            b.checked = (j == self.tab_index)
        for g in self.tab_groups:
            self._vis(g, False)
        if self.connected:
            self._vis(self.tab_groups[self.tab_index], True)

    def _set_connected(self, on):
        self._vis(self.home, on)
        self._vis(self.waiting_only, not on)
        self._vis(self.dpad, on)
        if on:
            hint(self.flipper, *self.C(403, 82, 360, 156))
            hint(self.screen, *self.C(403 + 93, 82 + 26, 128, 64))
        else:
            hint(self.flipper, *self.C(216, 82, 360, 156))
            hint(self.screen, *self.C(216 + 93, 82 + 26, 128, 64))
            self.screen.source = ""
            self.screen.source = asset("gfx", "default.png")
            self.screen.color = (1, 1, 1, 1)
        self._refresh_tabs()

    def _fill(self, info):
        self.name_lbl.text = (info.get("hardware_name") or info.get("hardware.name")
                              or info.get("hardware_model") or "Flipper")
        self.path_lbl.text = (self.link.devname or "")[-26:]
        keys = [k for k in ORDER if k in info] or list(info)[:9]
        self.info_lbl.text = "\n".join(
            "%s: %s" % (k.replace("_", " "), info[k][:22]) for k in keys[:10])

    # ---------- state from the USB link ----------
    def on_state(self, state, info):
        if state == "waiting":
            if self.connected:
                self.connected = False
                self._set_connected(False)
            self.status.text = "Waiting for devices ..."
        elif state == "permission":
            self.status.text = "Allow USB access in the popup ..."
        elif state == "connected":
            self.connected = True
            self._fill(info)
            self._set_connected(True)
            self.status.text = "Ready."
        elif state == "error":
            self.status.text = "Error: " + info.get("msg", "")[:60]

    def _frame(self, data):
        if not self.connected:
            return
        self._latest = data
        if not getattr(self, "_draw_pending", False):
            self._draw_pending = True
            Clock.schedule_once(self._draw, 0)

    def _draw(self, dt):
        self._draw_pending = False
        data = getattr(self, "_latest", None)
        if not data or not self.connected:
            return
        tbl = getattr(self, "_tbl", None)
        if tbl is None:
            tbl = self._tbl = [
                bytes(0 if (v >> bit) & 1 else 255 for v in range(256))
                for bit in range(8)]
        rows = [data[(y // 8) * 128:(y // 8) * 128 + 128].translate(tbl[y % 8])
                for y in range(64)]
        tex = Texture.create(size=(128, 64), colorfmt="luminance")
        tex.mag_filter = "nearest"
        tex.blit_buffer(b"".join(reversed(rows)), colorfmt="luminance",
                        bufferfmt="ubyte")
        self.screen.texture = tex
        self.screen.color = (1, 0.51, 0, 1)

    def _key(self, name):
        rpc = self.link.rpc
        if not rpc:
            return
        log("key %s" % name)

        def run():
            try:
                rpc.key(name)
            except Exception as e:
                log("key err: %r" % (e,))
        threading.Thread(target=run, daemon=True).start()

    def say(self, msg):
        self.status.text = msg
        Clock.unschedule(self._restore)
        Clock.schedule_once(self._restore, 2.5)

    def _restore(self, dt):
        self.status.text = "Ready." if self.connected else "Waiting for devices ..."

    # ---------- log viewer ----------
    def toggle_logs(self, *args):
        if self.log_widgets:
            for w in self.log_widgets:
                self.st.remove_widget(w)
            self.log_widgets = []
            return
        panel = self.st.place(Panel(self.st, fill=(0, 0, 0, 0.94),
                                    border=LIGHTORANGE2, border_w=3, radius=9),
                              self.cx, self.cy, self.cw, self.ch)
        self.log_label = self.st.place(
            StageLabel(self.st, 14, text="", halign="left", valign="top",
                       color=LIGHTORANGE2, font_name=FONT["mono"]),
            self.cx + 14, self.cy + 12, self.cw - 28, self.ch - 24)
        self.log_widgets = [panel, self.log_label]
        self._refresh_log()

    def _refresh_log(self, *args):
        if self.log_widgets:
            self.log_label.text = "\n".join(l[:95] for l in LOG_LINES[-17:])
