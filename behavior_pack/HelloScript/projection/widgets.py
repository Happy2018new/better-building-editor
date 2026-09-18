# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""App-local typography, rounded surfaces and spring feedback."""
from __future__ import unicode_literals
import math
import time
import mod.client.extraClientApi as clientApi
from functools import partial
from ..pyreact import *
from ..pyreact.hooks import use_animation_frame
from ..pyreact.style import Style as NativeStyle
from ..pyreact.primitives import LabelPrimitive as BaseLabelPrimitive, ImagePrimitive, SliderPrimitive, InputPrimitive, PaperDollPrimitive as BasePaperDollPrimitive, ScrollViewPrimitive, ButtonPrimitive as BaseButtonPrimitive, PanelPrimitive
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
        if control is not None and next_props.get('rasterText') and (
                prev_props is None or prev_props.get('content') != next_props.get('content')):
            control.asLabel().SetText('', False)


class PaperDollPrimitive(BasePaperDollPrimitive):
    def apply_props(self, host, fiber, control, prev_props, next_props):
        if next_props.get('managed'):
            return  # Scene owns native submissions; props remain inspectable.
        if prev_props and prev_props.get('renderKey') != next_props.get('renderKey'):
            prev_props = None
        BasePaperDollPrimitive.apply_props(self, host, fiber, control, prev_props, next_props)


NativeText = LabelPrimitive()
NativeText.template_path = '/root/mp_label_tmpl'
TypeImage = ImagePrimitive()
TypeImage.template_path = '/root/mp_type_tmpl'
Image = TypeImage
NativeInput = InputPrimitive()
NativeInput.template_path = '/root/mp_input_tmpl'
Slider = SliderPrimitive()
Slider.template_path = '/root/mp_slider_tmpl'
Doll = PaperDollPrimitive()
Doll.template_path = '/root/mp_doll_tmpl'
NativeScroll = ScrollViewPrimitive()
NativeScroll.template_path = '/root/mp_scroll_tmpl'


class RoundedPrimitive(PanelPrimitive):
    """Nine native patches, one layout node; fixed corners never become ellipses."""
    template_path = '/root/mp_round_tmpl'

    def props_affect_layout(self, prev_props, next_props, style):
        return False

    def apply_props(self, host, fiber, control, prev_props, next_props):
        state = fiber.primitive_state
        if 'patches' not in state:
            state['patches'] = [host.GetBaseUIControl(fiber.native_path + '/p%d' % i) for i in range(9)]
        color = next_props.get('color') or Theme.white
        rgb = color.to_rgb_tuple()
        if state.get('rgb') != rgb:
            for patch in state['patches']:
                patch.asImage().SetSpriteColor(rgb)
            state['rgb'] = rgb
        if state.get('_layout_applied'):
            self.paint(fiber, state['_layout_applied'][:2], state.get('_inherited_opacity', 1.))

    def paint(self, fiber, size, alpha):
        state = fiber.primitive_state
        width, height = size
        scale = state.get('_visual_scale', (1., 1.))
        radius = fiber.props.get('radius', 7 * Theme.scale)
        rx, ry = min(radius * scale[0], width / 2.), min(radius * scale[1], height / 2.)
        color = fiber.props.get('color') or Theme.white
        signature = (width, height, rx, ry, alpha * color.a)
        if state.get('rounded_paint') == signature:
            return
        old = state.get('rounded_paint')
        for i, patch in enumerate(state['patches']):
            row_index, col = i // 3, i % 3
            if old is None or old[:4] != signature[:4]:
                patch.SetPosition(((0., rx, width - rx)[col], (0., ry, height - ry)[row_index]))
                patch.SetSize(((rx, max(0., width - 2 * rx), rx)[col],
                               (ry, max(0., height - 2 * ry), ry)[row_index]))
            if old is None or old[4] != signature[4]:
                patch.SetAlpha(signature[4])
        state['rounded_paint'] = signature

    def apply_layout(self, host, node):
        # _layout_applied includes visual scaling; frame_w/h are logical during layout.
        size = node.fiber.primitive_state.get('_layout_applied', (node.frame_w, node.frame_h))[:2]
        self.paint(node.fiber, size, node.inherited_opacity)


Rounded = RoundedPrimitive()


@Component
def Field(value=None, onChange=None, style=None):
    # The native edit box already reserves text/caret padding; adding another
    # inset would clip digits in compact auxiliary-value fields.
    return Panel(style=style, children=[
        rounded_skin(Theme.tint, 5),
        NativeInput(value=value, onChange=onChange, style=S(width='100%', height='100%', zIndex=2))])


Input = Field


class ButtonPrimitive(BaseButtonPrimitive):
    """Native hit testing; feedback recolors the existing fixed-corner surface."""
    def apply_props(self, host, fiber, control, prev_props, next_props):
        BaseButtonPrimitive.apply_props(self, host, fiber, control, prev_props, next_props)
        if prev_props is not None:
            return
        button = control.asButton()
        button.AddHoverEventParams()

        def feedback(value, unused):
            callback = fiber.props.get('onFeedback')
            if callback:
                callback(value)

        def released(args):
            feedback(ButtonState.hover, args)
            host._pyreact_dispatch_touch_up(args)

        button.SetButtonHoverInCallback(partial(feedback, ButtonState.hover))
        button.SetButtonHoverOutCallback(partial(feedback, ButtonState.default))
        button.SetButtonTouchDownCallback(partial(feedback, ButtonState.pressed))
        button.SetButtonTouchCancelCallback(partial(feedback, ButtonState.default))
        button.SetButtonTouchUpCallback(released)


FeedbackButton = ButtonPrimitive()


class PointerPrimitive(BaseButtonPrimitive):
    """App-local pointer surface; callbacks receive native UI coordinates."""
    def apply_props(self, host, fiber, control, prev_props, next_props):
        BaseButtonPrimitive.apply_props(self, host, fiber, control, prev_props, next_props)
        tracker = fiber.primitive_state.get('pointer_tracker')
        if tracker is None:
            tracker = PointerTracker(host, fiber)
            fiber.primitive_state['pointer_tracker'] = tracker
        tracker.props = next_props
        button = control.asButton()
        if prev_props is None:
            button.AddHoverEventParams()
            for name, method in (('down', 'SetButtonTouchDownCallback'), ('move', 'SetButtonTouchMoveCallback'),
                                 ('up', 'SetButtonTouchUpCallback'), ('cancel', 'SetButtonTouchCancelCallback'),
                                 ('enter', 'SetButtonHoverInCallback'), ('leave', 'SetButtonHoverOutCallback')):
                getattr(button, method)(getattr(tracker, name))

    def unmount(self, host, fiber):
        tracker = fiber.primitive_state.get('pointer_tracker')
        if tracker:
            tracker.stop()
        BaseButtonPrimitive.unmount(self, host, fiber)


class PointerTracker(object):
    """PC has no touch-move events. Poll only while a native button is held."""
    def __init__(self, host, fiber):
        self.host, self.props = host, {}
        self.motion = clientApi.GetEngineCompFactory().CreateActorMotion(clientApi.GetLocalPlayerId())
        self.slot = {'fiber': fiber, 'active': False, 'callback': self.tick}
        self.origin = self.previous = None
        self.args = None

    def send(self, name, args):
        callback = self.props.get(name)
        if callable(callback):
            callback(args)

    def down(self, args):
        self.origin = self.previous = self.motion.GetMousePosition()
        self.args = dict(args)
        self.send('onDown', args)
        if self.origin is not None:
            self.slot['active'] = True
            self.host.pyreact_register_animation_frame(self.slot)

    def tick(self, unused):
        current = self.motion.GetMousePosition()
        if current is not None and current != self.previous:
            self.previous = current
            args = dict(self.args)
            args['TouchPosX'] += current[0] - self.origin[0]
            args['TouchPosY'] += current[1] - self.origin[1]
            self.send('onMove', args)

    def stop(self):
        self.slot['active'] = False
        self.host.pyreact_unregister_animation_frame(self.slot)

    def up(self, args):
        if self.slot['active']:
            self.tick(0.)
        self.stop()
        self.send('onUp', args)

    def cancel(self, args):
        self.stop()
        self.send('onCancel', args)

    def move(self, args):
        self.send('onMove', args)

    def enter(self, args):
        self.send('onEnter', args)

    def leave(self, args):
        self.send('onLeave', args)


Pointer = PointerPrimitive()


@Component
def Scroll(style=None, children=None, resetKey=None):
    """Native wheel/touch scrolling with a proportional, draggable app thumb."""
    view, content, rail, thumb = use_ref(None), use_ref(None), use_ref(None), use_ref(None)
    metrics = use_ref((0., 0., 0., 0.))
    drag = use_ref(None)
    rendered = use_ref(None)

    def reset():
        if view.current:
            NativeScroll.scroll_to_top(view.current)
    use_effect(reset, [resetKey])

    def tick(unused):
        if not all(r.current for r in (view, content, rail, thumb)):
            return
        height = view.current.GetSize()[1]
        total = content.current.GetSize()[1]
        pos = NativeScroll.get_scroll_position(view.current) or 0.
        length = min(height, max(24 * Theme.scale, height * height / max(height, total, 1.)))
        offset = max(0., min(height - length, pos * (height - length) / max(1., total - height)))
        metrics.current = (height, total, length, pos)
        signature = (height, total, length, offset, Theme.scale)
        if signature == rendered.current:
            return
        rendered.current = signature
        rail.current.SetVisible(total > height + 1)
        thumb.current.SetSize((4 * Theme.scale, length))
        thumb.current.SetPosition((3 * Theme.scale, offset))

    def move(args):
        if drag.current is None:
            return
        height, total, length, unused = metrics.current
        y, initial = drag.current
        pos = initial + (args['TouchPosY'] - y) * (total - height) / max(1., height - length)
        NativeScroll.scroll_to(view.current, max(0., min(total - height, pos)))

    def down(args):
        height, total, length, pos = metrics.current
        y = args['TouchPosY'] - rail.current.GetGlobalPosition()[1]
        top = pos * (height - length) / max(1., total - height)
        if not top <= y <= top + length:
            pos = max(0., min(total - height, (y - length / 2.) * (total - height) / max(1., height - length)))
            NativeScroll.scroll_to(view.current, pos)
        drag.current = (args['TouchPosY'], pos)

    def up(unused):
        drag.current = None

    use_animation_frame(tick)
    return Panel(style=style, children=[
        NativeScroll(ref=view, showScrollbar=False, style=NativeStyle(width='100%', height='100%'),
            children=Panel(ref=content, style=NativeStyle(width='100%'), children=children)),
        Pointer(ref=rail, onDown=down, onMove=move, onUp=up, onCancel=up,
            buttonBuilder=transparent,
            style=S(position=Position.absolute, right=0, top=0, width=10, height='100%', zIndex=10),
            children=Image(ref=thumb, color=Color(0xAAB8CCFF),
                style=S(position=Position.absolute, left=3, top=0, width=4, height=24))),
    ])


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
    return Rounded(color=color, radius=radius * Theme.scale,
                   style=S(position=Position.absolute, left=0, top=0, width='100%', height='100%', zIndex=-3))


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
    # Translate one parent and fade one cover; never fade thousands of children.
    return Panel(style=S(width=width, height=height,
                        transform=[Translate(12 * (1 - eased) * Theme.scale, 0)]), children=[children,
        Image(color=Theme.bg, style=S(position=Position.absolute, width='100%', height='100%',
                                     zIndex=40, opacity=.65 * (1 - eased)))])


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
    stable_click = use_callback(clicked, [onClick])

    def tick(now):
        set_progress(min(1., (now - started.current) / .36))
    use_animation_frame(tick, progress < 1.)
    wobble = math.exp(-6 * progress) * math.sin(3 * math.pi * progress) if progress < 1. else 0.
    return Button(onClick=stable_click, buttonBuilder=buttonBuilder,
                  style=(style or NativeStyle()).merge(NativeStyle(transform=[Scale(1 + .06 * wobble, 1 - .08 * wobble)])),
                  children=children)


@Component
def Action(label='', onClick=None, width=None, height=32, accent=False, selected=False,
           enabled=True, glyph=None, danger=False, compact=False):
    progress, set_progress = use_state(1.)
    feedback, set_feedback = use_state(ButtonState.default)
    stable_feedback = use_callback(set_feedback, [])
    started = use_ref(0.)

    def click():
        if not enabled or not callable(onClick):
            return
        if Theme.motion:
            started.current = time.time()
            set_progress(0.)
        onClick()
    stable_click = use_callback(click, [onClick, enabled])

    def tick(now):
        set_progress(min(1., (now - started.current) / .44))
    use_animation_frame(tick, progress < 1.)
    wobble = math.exp(-6 * progress) * math.sin(3.5 * math.pi * progress) if progress < 1. else 0
    base = Theme.blue if accent else (Theme.tint if selected else Theme.pale)
    if enabled and feedback != ButtonState.default:
        base = base.darken(.10 if feedback == ButtonState.pressed else .035)
    ink = Theme.white if accent else (Theme.red if danger else (Theme.blue if selected else Theme.ink))

    def content():
        contents = []
        if glyph:
            contents.append(icon(glyph, ink, 15 if compact else 17))
        if label:
            contents.append(text(label, 11 if compact else 12, ink))
        return [rounded_skin(base), row(contents, justifyContent=JustifyContent.center, paddingHorizontal=9)]
    children = list(use_memo(content, [label, glyph, compact, accent, selected, danger, enabled, feedback, Theme.scale]))
    # One permanent sprite replaces six separately laid-out particle controls.
    children.append(Image(key='burst', src=TEX + 'transparent', frames=BURST_FRAMES,
        frameDuration=.0275, playing=progress < 1. and Theme.motion, loop=False,
        style=S(position=Position.absolute, left='50%', top='50%', width=60, height=48,
                opacity=1 if progress < 1. and Theme.motion else 0., zIndex=20,
                transform=[Translate(-30 * Theme.scale, -24 * Theme.scale)])))
    return FeedbackButton(buttonBuilder=transparent, onFeedback=stable_feedback, onClick=stable_click if enabled else None,
                  style=S(width=width, height=height, flexShrink=0,
                          opacity=1 if enabled else .38,
                          transform=[Scale(1 + .07 * wobble, 1 - .10 * wobble)]), children=children)


BURST_FRAMES = tuple(TEX + 'burst_%02d' % i for i in range(16))


@Component
def Range(label='', value=0., minimum=0., maximum=1., onChange=None, unit='', integer=False):
    current, set_current = use_state(value)
    track, fill, knob = use_ref(None), use_ref(None), use_ref(None)
    pulse = use_ref(0.)
    applied = use_ref(None)

    def sync():
        set_current(value)
    use_effect(sync, [value])
    normalized = max(0., min(1., (current - minimum) / float(maximum - minimum)))

    def change(v):
        val = minimum + v * (maximum - minimum)
        if integer:
            val = int(math.floor(val + .5))
        if val == current:
            return
        pulse.current = time.time()
        set_current(val)
        if onChange:
            onChange(val)

    def tick(now):
        if not all(r.current for r in (track, fill, knob)):
            return
        width = track.current.GetSize()[0]
        age = max(0., now - pulse.current)
        swell = 1 + .16 * math.exp(-18 * age) if Theme.motion and age < .4 else 1.
        size = 15 * Theme.scale * swell
        signature = (width, normalized, size, Theme.scale)
        if applied.current == signature:
            return
        applied.current = signature
        fill.current.SetSize((width * normalized, 4 * Theme.scale))
        knob.current.SetSize((size, size))
        knob.current.SetPosition((width * normalized - size / 2., 13 * Theme.scale - size / 2.))
    use_animation_frame(tick)
    stable_change = use_callback(change, [current, minimum, maximum, integer, onChange])
    return Panel(style=S(height=49, width='100%'), children=[
        row([text(label, 11, Theme.muted, flex=1),
             NativeText(content=('%d' % current if integer else '%.2f' % current) + unit,
                        fontSize=11 * Theme.scale, color=Theme.ink, shadow=False,
                        textAlign=TextAlignment.right, style=S(width=66, height=15))]),
        Panel(style=S(height=26, width='100%', marginTop=3, paddingHorizontal=10), children=[
          Panel(ref=track, style=S(height=26, width='100%'), children=[
            Image(color=Theme.line, style=S(position=Position.absolute, top=11, height=4, width='100%')),
            Image(ref=fill, color=Theme.blue, style=S(position=Position.absolute, top=11, height=4, width=0)),
            Image(ref=knob, src=TEX + 'knob', style=S(position=Position.absolute, width=15, height=15)),
            Slider(value=normalized, steps=1, onChange=stable_change, style=S(width='100%', height=26, zIndex=4)),
          ])])])


@Component
def Segments(items=None, value=None, onChange=None, width=216):
    items = items or []
    index = next((i for i, pair in enumerate(items) if pair[0] == value), 0)
    destination, set_destination = use_state(index)

    def travel():
        # Begin after the parent has committed its new page/parameters. Otherwise
        # their layout work consumes the first half of this short transition.
        set_destination(index)
    use_effect(travel, [index])
    cell = (width - 6) / max(1, len(items))
    return surface(color=Theme.pale, width=width, height=32, padding=3, children=[
        Animated(style=S(position=Position.absolute, left=3, top=3, width=cell, height=26),
                 transition=NativeStyle(transform=[Translate(destination * cell * Theme.scale, 0)]),
                 duration=.30 if Theme.motion else 0., transitionEasing=Easing.cubic_in_out,
                 children=surface(color=Theme.white, width='100%', height='100%')),
        row([JellyButton(key=pair[0], buttonBuilder=transparent, onClick=partial(onChange, pair[0]),
                    style=S(width=cell, height=26),
                    children=text(pair[1], 11, Theme.blue if pair[0] == value else Theme.muted,
                                  center=True, width=cell)) for pair in items], gap=0)])
