import os

from kivy.app import App
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

BASE_W, BASE_H = 830, 500
HERE = os.path.dirname(os.path.abspath(__file__))

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


class QFlipperApp(App):
    def build(self):
        register_fonts()
        Window.clearcolor = BLACK
        st = Stage()

        st.place(Panel(st, fill=BLACK, border=MEDIUMORANGE3, border_w=2,
                       radius=10), 0, 0, BASE_W, BASE_H)

        BW = 3
        cw, ch = 800 + BW * 2, 390 + BW * 2
        cx, cy = (BASE_W - cw) / 2, 38

        def C(x, y, w, h):
            return cx + x, cy + y, w, h

        st.place(Panel(st, texture=vgradient("#090400", "#210F00"),
                       border=LIGHTORANGE2, border_w=BW, radius=9),
                 cx, cy, cw, ch)
        st.place(GridLines(st, cw, ch, BW), cx, cy, cw, ch)

        st.place(StageLabel(st, 16, text="0.0.0", halign="right", valign="top",
                            color=(*LIGHTORANGE2[:3], 0.5), font_name=FONT["mono"]),
                 *C(cw - 16 - 120, 10, 120, 24))

        st.place(Image(source=asset("gfx", "flipper.png"), fit_mode="fill"),
                 *C(216, 82, 360, 156))
        st.place(Image(source=asset("gfx", "default.png"), fit_mode="fill"),
                 *C(216 + 93, 82 + 26, 128, 64))

        st.place(Image(source=asset("gfx", "typec.png"), fit_mode="fill"),
                 *C(cw - 216, 145, 159, 37))
        st.place(StageLabel(st, 48, text="Connect your Flipper", halign="center",
                            valign="top", color=LIGHTORANGE2, font_name=FONT["title"]),
                 *C(0, 264, cw, 60))

        fy = cy + ch + 13
        st.place(OutlineButton(st, text="LOGS"), cx, fy, 110, 42)

        sx, sw = cx + 110 + 15, cw - 110 - 15
        st.place(Panel(st, fill=DARKORANGE1), sx, fy, sw, 42)
        st.place(Image(source=asset("gfx", "info-small.png"), fit_mode="fill"),
                 sx + 10, fy + 10, 22, 22)
        st.place(StageLabel(st, 18, text="Waiting for devices ...", halign="left",
                            valign="middle", color=LIGHTORANGE2, font_name=FONT["ui"]),
                 sx + 10 + 22 + 10, fy, sw - 42, 42)
        return st


if __name__ == "__main__":
    QFlipperApp().run()
