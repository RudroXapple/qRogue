"""
qFlipper-style UI in Kivy (waiting-for-device screen) with USB link.

All numbers come from qFlipper's own QML (GPLv3):
  main.qml, MainWindow.qml, GridBackground.qml, NoDeviceOverlay.qml,
  DeviceWidget.qml, StatusBar.qml, Theme.qml
The UI is drawn on a fixed 830x500 stage scaled to the phone screen
(use landscape). Stage.place() takes desktop pixel coordinates (from top-left).
"""
import os
import threading
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.properties import NumericProperty
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex as hexc
from kivy.utils import platform

BASE_W, BASE_H = 830, 500                      # MainWindow.baseWidth/baseHeight
HERE = os.path.dirname(os.path.abspath(__file__))

# Theme.qml
LIGHTORANGE2 = hexc("#fe8a2c")
MEDIUMORANGE3 = hexc("#662c00")
DARKORANGE1 = hexc("#491d00")
BLACK = (0, 0, 0, 1)


def asset(*parts):
    return os.path.join(HERE, "assets", *parts)


FONT = {"mono": "Roboto", "ui": "Roboto", "title": "Roboto"}


def register_fonts():
    for key, name, fn in [("title", "Born2bSporty", "Born2bSportyV2.ttf"),
                          ("mono", "ProggySquare", "ProggySquare.ttf"),
                          ("ui", "ShareTech", "ShareTech-Regular.ttf")]:
        path = asset("fonts", fn)
        if os.path.exists(path):
            LabelBase.register(name=name, fn_regular=path)
            FONT[key] = name


def vgradient(top_hex, bottom_hex):
    """1x2 texture; QML GradientStop 0 is the top."""
    top = [int(c * 255) for c in hexc(top_hex)]
    bottom = [int(c * 255) for c in hexc(bottom_hex)]
    tex = Texture.create(size=(1, 2), colorfmt="rgba")
    tex.blit_buffer(bytes(bottom + top), colorfmt="rgba", bufferfmt="ubyte")
    tex.mag_filter = "linear"
    tex.wrap = "clamp_to_edge"
    return tex


class Stage(FloatLayout):
    scale = NumericProperty(1)

    def __init__(self, **kw):
        super().__init__(size_hint=(None, None), **kw)
        Window.bind(size=self._fit)
        self._fit()

    def _fit(self, *args):
        w, h = Window.size
        self.scale = min(w / BASE_W, h / BASE_H)
        self.size = (BASE_W * self.scale, BASE_H * self.scale)
        self.pos = ((w - self.width) / 2, (h - self.height) / 2)

    def place(self, widget, x, y, w, h):
        widget.size_hint = (w / BASE_W, h / BASE_H)
        widget.pos_hint = {"x": x / BASE_W, "y": 1 - (y + h) / BASE_H}
        self.add_widget(widget)
        return widget


class Panel(Widget):
    """QML Rectangle: fill (colour or gradient texture), radius, border."""

    def __init__(self, stage, fill=BLACK, texture=None, border=None,
                 border_w=0, radius=0, **kw):
        super().__init__(**kw)
        self.stage, self._r, self._bw = stage, radius, border_w
        with self.canvas:
            Color(*((1, 1, 1, 1) if texture else fill))
            self._bg = RoundedRectangle(texture=texture)
            Color(*(border or (0, 0, 0, 0)))
            self._ln = Line(width=1)
        self.bind(pos=self._redraw, size=self._redraw)
        stage.bind(scale=self._redraw)

    def _redraw(self, *args):
        s = self.stage.scale
        self._bg.pos, self._bg.size = self.pos, self.size
        self._bg.radius = [self._r * s]
        if self._bw:
            self._ln.width = self._bw * s
            self._ln.rounded_rectangle = (*self.pos, *self.size, self._r * s)


class GridLines(Widget):
    """Canvas grid of GridBackground.qml: 30 cells across, #aa5115, 15% opacity."""

    def __init__(self, stage, content_w, content_h, border_w, **kw):
        super().__init__(**kw)
        self.stage, self.cw, self.ch, self.bw = stage, content_w, content_h, border_w
        self.bind(pos=self._draw, size=self._draw)
        stage.bind(scale=self._draw)

    def _draw(self, *args):
        s = self.stage.scale
        inner_w = self.cw - 2 * self.bw
        inner_h = self.ch - 2 * self.bw
        cell = inner_w / 30
        left = self.x + self.bw * s
        top = self.y + self.height - self.bw * s
        self.canvas.clear()
        with self.canvas:
            Color(*hexc("#aa5115")[:3], 0.15)
            ypos = cell
            while ypos < inner_h:
                y = top - int(ypos) * s
                Line(points=[left, y, left + inner_w * s, y], width=2 * s)
                ypos += cell
            xpos = cell
            while xpos < inner_w:
                x = left + int(xpos) * s
                Line(points=[x, top, x, top - inner_h * s], width=2 * s)
                xpos += cell


class StageLabel(Label):
    def __init__(self, stage, px, **kw):
        super().__init__(**kw)
        self.stage, self.px = stage, px
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))
        stage.bind(scale=self._font)
        self._font()

    def _font(self, *args):
        self.font_size = self.px * self.stage.scale


class OutlineButton(Button):
    """Placeholder LOGS button until DefaultAmber/Button.qml is read."""

    def __init__(self, stage, **kw):
        super().__init__(background_normal="", background_down="",
                         background_color=(0, 0, 0, 0), color=LIGHTORANGE2,
                         font_name=FONT["ui"], **kw)
        self.stage = stage
        with self.canvas.before:
            Color(*MEDIUMORANGE3)
            self._ln = Line(width=1)
        self.bind(pos=self._r, size=self._r)
        stage.bind(scale=self._r)

    def _r(self, *args):
        s = self.stage.scale
        self._ln.width = 2 * s
        self._ln.rounded_rectangle = (*self.pos, *self.size, 6 * s)
        self.font_size = 16 * s


LOG_LINES = []
FLIPPER_VID = 0x0483


def log(msg):
    LOG_LINES.append(time.strftime("%H:%M:%S ") + str(msg))
    del LOG_LINES[:-200]
    print(msg)


class FlipperLink:
    """USB link to a Flipper Zero (Android USB host via usb4a + usbserial4a)."""

    def __init__(self, on_state):
        self.on_state = on_state
        self.port = None
        self.devname = None
        self.busy = False
        self.failed = None
        self.asked = set()
        self.seen = None
        self.usb = self.serial4a = None
        if platform == "android":
            try:
                from usb4a import usb
                from usbserial4a import serial4a
                self.usb, self.serial4a = usb, serial4a
                log("USB libraries loaded")
            except Exception as e:
                log("USB libraries missing: %r" % (e,))
        else:
            log("Not on Android: USB disabled")

    def poll(self, dt):
        try:
            self._poll()
        except Exception as e:
            log("poll error: %r" % (e,))

    def _poll(self):
        if not self.usb or self.busy:
            return
        devices = list(self.usb.get_usb_device_list())
        names = [d.getDeviceName() for d in devices]
        if tuple(names) != self.seen:
            self.seen = tuple(names)
            log("USB devices: %d" % len(devices))
            for d in devices:
                log("  %s %04x:%04x" % (d.getDeviceName(), d.getVendorId(),
                                       d.getProductId()))
        if self.port is not None:
            if self.devname not in names:
                self._lost()
            return
        flipper = next((d for d in devices if d.getVendorId() == FLIPPER_VID), None)
        if flipper is None:
            self.asked.clear()
            self.failed = None
            self.on_state("waiting", {})
            return
        name = flipper.getDeviceName()
        if name == self.failed:
            return
        if not self.usb.has_usb_permission(flipper):
            self.on_state("permission", {})
            if name not in self.asked:
                self.asked.add(name)
                log("requesting USB permission")
                self.usb.request_usb_permission(flipper)
            return
        self.busy = True
        threading.Thread(target=self._open, args=(name,), daemon=True).start()

    def _lost(self):
        log("Flipper disconnected")
        try:
            self.port.close()
        except Exception:
            pass
        self.port = self.devname = None
        self.on_state("waiting", {})

    @staticmethod
    def _read_until_prompt(port, timeout):
        buf = b""
        end = time.time() + timeout
        while time.time() < end:
            n = port.in_waiting
            if n:
                buf += port.read(n)
                if buf.rstrip(b" ").endswith(b">:"):
                    break
            else:
                time.sleep(0.05)
        return buf

    def _open(self, name):
        port = None
        try:
            port = self.serial4a.get_serial_port(name, 115200, 8, "N", 1)
            if not port or not port.is_open:
                raise RuntimeError("serial port did not open")
            try:
                port.dtr = True
            except Exception as e:
                log("dtr: %r" % (e,))
            log("port open, asking device_info")
            time.sleep(0.3)
            port.write(b"\r\n")
            self._read_until_prompt(port, 2.0)
            port.write(b"device_info\r\n")
            out = self._read_until_prompt(port, 4.0).decode(errors="replace")
            info = {}
            for line in out.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    info[k.strip()] = v.strip()
            log("device_info: %d fields" % len(info))
            for k in list(info)[:6]:
                log("  %s = %s" % (k, info[k]))
            if not info:
                log("raw: %r" % (out[:200],))
            self.port, self.devname = port, name
            Clock.schedule_once(lambda dt: self.on_state("connected", info))
        except Exception as e:
            log("open failed: %r" % (e,))
            self.failed = name
            try:
                if port:
                    port.close()
            except Exception:
                pass
            msg = repr(e)
            Clock.schedule_once(lambda dt: self.on_state("error", {"msg": msg}))
        finally:
            self.busy = False


class QFlipperApp(App):
    def build(self):
        register_fonts()
        Window.clearcolor = BLACK
        st = Stage()

        # MainWindow.qml: bg, radius 10, border mediumorange3 2px
        st.place(Panel(st, fill=BLACK, border=MEDIUMORANGE3, border_w=2,
                       radius=10), 0, 0, BASE_W, BASE_H)

        # mainContent = GridBackground: 800+2*3 x 390+2*3, y = 38, centered
        BW = 3
        cw, ch = 800 + BW * 2, 390 + BW * 2
        cx, cy = (BASE_W - cw) / 2, 38

        def C(x, y, w, h):          # content coords -> stage coords
            return cx + x, cy + y, w, h

        st.place(Panel(st, texture=vgradient("#090400", "#210F00"),
                       border=LIGHTORANGE2, border_w=BW, radius=9),
                 cx, cy, cw, ch)
        st.place(GridLines(st, cw, ch, BW), cx, cy, cw, ch)

        # versionLabel: top-right, margin 10 / right 16, 16px, opacity 0.5
        self.st, self.cx, self.cy, self.cw, self.ch = st, cx, cy, cw, ch
        self.log_widgets = []
        st.place(StageLabel(st, 16, text="0.0.0", halign="right", valign="top",
                            color=(*LIGHTORANGE2[:3], 0.5), font_name=FONT["mono"]),
                 *C(cw - 16 - 120, 10, 120, 24))

        # DeviceWidget (waiting state): flipper.svg 360x156 at x=216, y=82
        st.place(Image(source=asset("gfx", "flipper.png"), fit_mode="fill"),
                 *C(216, 82, 360, 156))
        # defaultScreen: at (93, 26) inside flipper, 128x64
        st.place(Image(source=asset("gfx", "default.png"), fit_mode="fill"),
                 *C(216 + 93, 82 + 26, 128, 64))

        # NoDeviceOverlay: usb plug at x = width-216, y = 145 (159x37)
        self.plug = st.place(Image(source=asset("gfx", "typec.png"), fit_mode="fill"),
                             *C(cw - 216, 145, 159, 37))
        # connectMsg: centered, y = 264, Born2bSportyV2 48px
        self.headline = st.place(StageLabel(st, 48, text="Connect your Flipper",
                                            halign="center", valign="top",
                                            color=LIGHTORANGE2, font_name=FONT["title"]),
                                 *C(0, 264, cw, 60))

        # footer: top = content bottom + 13, height 42, spacing 15
        fy = cy + ch + 13
        logs = OutlineButton(st, text="LOGS")
        logs.bind(on_release=self.toggle_logs)
        st.place(logs, cx, fy, 110, 42)

        # StatusBar: darkorange1, left margin 10, icon 22px, spacing 10
        sx, sw = cx + 110 + 15, cw - 110 - 15
        st.place(Panel(st, fill=DARKORANGE1), sx, fy, sw, 42)
        st.place(Image(source=asset("gfx", "info-small.png"), fit_mode="fill"),
                 sx + 10, fy + 10, 22, 22)
        self.status = st.place(StageLabel(st, 18, text="Waiting for devices ...",
                                          halign="left", valign="middle",
                                          color=LIGHTORANGE2, font_name=FONT["ui"]),
                               sx + 10 + 22 + 10, fy, sw - 42, 42)
        self.link = FlipperLink(self.on_state)
        Clock.schedule_interval(self.link.poll, 1.0)
        Clock.schedule_interval(self._refresh_log, 0.5)
        return st

    def on_state(self, state, info):
        if state == "waiting":
            self.status.text = "Waiting for devices ..."
            self.headline.text = "Connect your Flipper"
            self.plug.opacity = 1
        elif state == "permission":
            self.status.text = "Allow USB access in the popup ..."
        elif state == "connected":
            name = (info.get("hardware_name") or info.get("hardware_model")
                    or "Flipper")
            fw = info.get("firmware_version") or info.get("firmware.version") or ""
            self.headline.text = name
            self.plug.opacity = 0
            self.status.text = ("Connected  " + fw).strip()
        elif state == "error":
            self.status.text = "Error: " + info.get("msg", "")[:60]

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


if __name__ == "__main__":
    from app_ui import HomeApp
    HomeApp().run()
