# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""App-local typography, rounded surfaces and spring feedback."""
from __future__ import unicode_literals
import math
import time
from functools import partial
from ..pyreact import *
from ..pyreact.hooks import use_animation_frame
from ..pyreact.style import Style as NativeStyle
from ..pyreact.primitives import LabelPrimitive as BaseLabelPrimitive, ImagePrimitive, SliderPrimitive, InputPrimitive, PaperDollPrimitive as BasePaperDollPrimitive, ScrollViewPrimitive
from .type_assets import ASSETS

TEX = 'textures/modern_projection/'


class Theme(object):
    scale = 1.
    motion = True
    bg = Color(0xF1F4F8FF)
    white = Color(0xFFFFFFFF)
    ink = Color(0x26374BFF)
    muted = Color(0x7D8CA0FF)
    line = Color(0xE5EBF2FF)
    pale = Color(0xF5F8FCFF)
    blue = Color(0x477AF4FF)
    tint = Color(0xEDF2FFFF)
    mint = Color(0x178C7EFF)
    green = Color(0xE9F7F1FF)
    red = Color(0xD35C72FF)


def S(**values):
    dimensions = ('width', 'height', 'minWidth', 'minHeight', 'maxWidth', 'maxHeight',
                  'top', 'right', 'bottom', 'left', 'gap', 'rowGap', 'columnGap', 'flexBasis')
    for name, value in list(values.items()):
        if name in dimensions or name.startswith(('padding', 'margin')):
            if isinstance(value, (int, float)):
                values[name] = value * Theme.scale
    return NativeStyle(**values)


class LabelPrimitive(BaseLabelPrimitive):
    def apply_props(self, host, fiber, control, prev_props, next_props):
        BaseLabelPrimitive.apply_props(self, host, fiber, control, prev_props, next_props)
        if control is not None and next_props.get('rasterText'):
            control.asLabel().SetText('', False)


class PaperDollPrimitive(BasePaperDollPrimitive):
    def apply_props(self, host, fiber, control, prev_props, next_props):
        if prev_props and prev_props.get('renderKey') != next_props.get('renderKey'):
            prev_props = None
        BasePaperDollPrimitive.apply_props(self, host, fiber, control, prev_props, next_props)


NativeText = LabelPrimitive()
NativeText.template_path = '/root/mp_label_tmpl'
TypeImage = ImagePrimitive()
TypeImage.template_path = '/root/mp_type_tmpl'
Image = TypeImage
Input = InputPrimitive()
Input.template_path = '/root/mp_input_tmpl'
Slider = SliderPrimitive()
Slider.template_path = '/root/mp_slider_tmpl'
Doll = PaperDollPrimitive()
Doll.template_path = '/root/mp_doll_tmpl'
Scroll = ScrollViewPrimitive()
Scroll.template_path = '/root/mp_scroll_tmpl'


def text(value, size=12, color=None, center=False, **style):
    if not isinstance(value, type('')):
        value = value.decode('utf8') if isinstance(value, bytes) else str(value)
    color = color or Theme.ink
    font = size * Theme.scale
    props = dict(content=value, fontSize=font, shadow=False, color=color,
                 textAlign=TextAlignment.center if center else TextAlignment.left)
    if value and all(char in ASSETS for char in value):
        pieces = [value] if value in ASSETS else list(value)
        advance = sum(ASSETS[p][3] for p in pieces) * font
        limit = style.get('width')
        limit = limit * Theme.scale if isinstance(limit, (int, float)) else None
        if limit and advance > limit:
            pieces = list(value)
        x, y, children = 0., 0., []
        for i, piece in enumerate(pieces):
            name, width, height, step = ASSETS[piece]
            if limit and x and x + step * font > limit:
                x, y = 0., y + font * 1.5
            children.append(TypeImage(key='glyph_%d' % i, src=TEX + 'type/' + name,
                color=color, style=NativeStyle(position=Position.absolute, left=x, top=y,
                                               width=width * font, height=height * font)))
            x += step * font
        advance = min(advance, limit) if limit else advance
        total_height = y + font * 1.35
        props['children'] = Panel(style=NativeStyle(position=Position.absolute,
            left='50%' if center else 0, top=0, width=advance, height=total_height,
            transform=[Translate(-advance / 2., 0)] if center else None), children=children)
        props['rasterText'] = True
        props['style'] = NativeStyle(width=advance, height=total_height).merge(S(**style))
    else:
        props['style'] = S(**style)
    return NativeText(**props)


def row(children, **style):
    values = dict(flexDirection=FlexDirection.row, alignItems=AlignItems.center, gap=6)
    values.update(style)
    return Panel(style=S(**values), children=children)


def rounded_skin(color, radius=7):
    # Explicit high-resolution corners avoid GUI-scale dependent native nine-slicing.
    rows = []
    for r, v in enumerate((0, 24, 40)):
        vh = 16 if r == 1 else 24
        cells = []
        for c, u in enumerate((0, 24, 40)):
            uw = 16 if c == 1 else 24
            cells.append(Image(src=TEX + 'rounded', color=color, uv=(u, v), uvSize=(uw, vh),
                style=S(width=radius if c != 1 else None, flex=1 if c == 1 else 0, height='100%')))
        rows.append(Panel(style=S(flexDirection=FlexDirection.row, width='100%',
                                 height=radius if r != 1 else None, flex=1 if r == 1 else 0), children=cells))
    return Panel(style=S(position=Position.absolute, left=0, top=0, width='100%', height='100%', zIndex=-3), children=rows)


def surface(children=None, color=None, **style):
    content = list(children) if isinstance(children, (list, tuple)) else ([children] if children is not None else [])
    radius = min(7, style.get('height', 32) / 2.) if isinstance(style.get('height', 32), (int, float)) else 7
    inset = dict((k, style.pop(k)) for k in list(style) if k.startswith('padding') or k in ('gap', 'alignItems', 'justifyContent'))
    inset['width'] = '100%'
    if style.get('height') is not None:
        inset['height'] = '100%'
    return Panel(style=S(**style), children=[rounded_skin(color or Theme.white, radius), Panel(style=S(**inset), children=content)])


def icon(name, color=None, size=18):
    return Image(src=TEX + 'icons/' + name, color=color or Theme.muted, style=S(width=size, height=size))


def line():
    return Image(color=Theme.line, style=S(height=1, width='100%', marginVertical=10))


def transparent(unused):
    return Image(color=Colors.transparent)


@Component
def PageMotion(page=None, children=None, width=760, height=440):
    progress, set_progress = use_state(1.)
    started = use_ref(0.)

    def changed():
        if Theme.motion:
            started.current = time.time()
            set_progress(0.)
    use_effect(changed, [page])

    def tick(now):
        set_progress(min(1., (now - started.current) / .28))
    use_animation_frame(tick, progress < 1.)
    eased = 1 - (1 - progress) ** 3 if Theme.motion else 1.
    return Panel(style=S(width=width, height=height, opacity=.4 + .6 * eased,
                        transform=[Translate(12 * (1 - eased) * Theme.scale, 0)]), children=children)


@Component
def JellyButton(onClick=None, buttonBuilder=None, style=None, children=None):
    progress, set_progress = use_state(1.)
    started = use_ref(0.)

    def clicked():
        if Theme.motion:
            started.current = time.time()
            set_progress(0.)
        if onClick:
            onClick()

    def tick(now):
        set_progress(min(1., (now - started.current) / .36))
    use_animation_frame(tick, progress < 1.)
    wobble = math.exp(-6 * progress) * math.sin(3 * math.pi * progress) if progress < 1. else 0.
    return Button(onClick=clicked, buttonBuilder=buttonBuilder,
                  style=(style or NativeStyle()).merge(NativeStyle(transform=[Scale(1 + .06 * wobble, 1 - .08 * wobble)])),
                  children=children)


@Component
def Action(label='', onClick=None, width=None, height=32, accent=False, selected=False,
           enabled=True, glyph=None, danger=False, compact=False):
    progress, set_progress = use_state(1.)
    started = use_ref(0.)

    def click():
        if not enabled or not callable(onClick):
            return
        if Theme.motion:
            started.current = time.time()
            set_progress(0.)
        onClick()

    def tick(now):
        set_progress(min(1., (now - started.current) / .44))
    use_animation_frame(tick, progress < 1.)
    wobble = math.exp(-6 * progress) * math.sin(3.5 * math.pi * progress) if progress < 1. else 0
    base = Theme.blue if accent else (Theme.tint if selected else Theme.pale)
    ink = Theme.white if accent else (Theme.red if danger else (Theme.blue if selected else Theme.ink))

    def background(state):
        return Image(color=Colors.transparent)
    contents = []
    if glyph:
        contents.append(icon(glyph, ink, 15 if compact else 17))
    if label:
        contents.append(text(label, 11 if compact else 12, ink))
    children = [rounded_skin(base), row(contents, justifyContent=JustifyContent.center, paddingHorizontal=9)]
    if 0 <= progress < 1. and Theme.motion:
        for i in range(6):
            angle = i * math.pi / 3.
            children.append(Image(key='burst%d' % i, src=TEX + 'dot', color=Theme.blue,
                style=S(position=Position.absolute, left='50%', top='50%', width=3, height=3,
                        opacity=(1. - progress) ** 2, zIndex=20,
                        transform=[Translate(math.cos(angle) * 27 * progress * Theme.scale,
                                             math.sin(angle) * 20 * progress * Theme.scale)])))
    return Button(buttonBuilder=background, onClick=click if enabled else None,
                  style=S(width=width, height=height, flexShrink=0,
                          opacity=1 if enabled else .38,
                          transform=[Scale(1 + .07 * wobble, 1 - .10 * wobble)]), children=children)


@Component
def Range(label='', value=0., minimum=0., maximum=1., onChange=None, unit='', integer=False):
    pulse, set_pulse = use_state(False)
    normalized = (value - minimum) / float(maximum - minimum)

    def change(v):
        val = minimum + v * (maximum - minimum)
        if integer:
            val = int(round(val))
        set_pulse(True)
        if onChange:
            onChange(val)

    def release():
        set_pulse(False)
    return Panel(style=S(height=49, width='100%'), children=[
        row([text(label, 11, Theme.muted, flex=1), text(('%d' % value if integer else '%.2f' % value) + unit, 11)]),
        Panel(style=S(height=26, width='100%', marginTop=3), children=[
            surface(color=Theme.line, position=Position.absolute, top=11, height=4, width='100%'),
            surface(color=Theme.blue, position=Position.absolute, top=11, height=4,
                    width='%.3f%%' % (100 * max(0., min(1., normalized)))),
            Animated(style=S(position=Position.absolute, left='%.3f%%' % (100 * max(0., min(1., normalized))),
                             top=5, width=15, height=15),
                     transition=NativeStyle(transform=[Scale(1.2 if pulse and Theme.motion else 1.)]),
                     transitionEasing=Easing.back_out, duration=.16, onTransitionComplete=release,
                     children=Image(src=TEX + 'knob', style=S(width=15, height=15, marginLeft=-7.5))),
            Slider(value=normalized, steps=1, onChange=change, style=S(width='100%', height=26, zIndex=4)),
        ])])


@Component
def Segments(items=None, value=None, onChange=None, width=216):
    items = items or []
    index = next((i for i, pair in enumerate(items) if pair[0] == value), 0)
    cell = (width - 6) / max(1, len(items))
    return surface(color=Theme.pale, width=width, height=32, padding=3, children=[
        Animated(style=S(position=Position.absolute, left=3, top=3, width=cell, height=26),
                 transition=NativeStyle(transform=[Translate(index * cell * Theme.scale, 0)]),
                 duration=.25 if Theme.motion else 0., transitionEasing=Easing.back_out,
                 children=surface(color=Theme.white, width='100%', height='100%')),
        row([JellyButton(key=pair[0], buttonBuilder=transparent, onClick=partial(onChange, pair[0]),
                    style=S(width=cell, height=26),
                    children=text(pair[1], 11, Theme.blue if pair[0] == value else Theme.muted)) for pair in items], gap=0)])
