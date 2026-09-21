# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""App-local typography, rounded surfaces and spring feedback."""
from __future__ import unicode_literals
import math
import time
import mod.client.extraClientApi as clientApi
from functools import partial
from ..pyreact import *
from ..pyreact import native
from ..pyreact.hooks import use_animation_frame
from ..pyreact.style import Style as NativeStyle
from ..pyreact.primitives import LabelPrimitive as BaseLabelPrimitive, ImagePrimitive, SliderPrimitive, InputPrimitive as BaseInputPrimitive, PaperDollPrimitive as BasePaperDollPrimitive, ScrollViewPrimitive, ButtonPrimitive as BaseButtonPrimitive, PanelPrimitive
from .type_assets import ASSETS
from .catalog import ACTION_ICONS, SEGMENT_ICONS
from .pointer import PointerTracker
from .input_mode import is_touch

TEX = 'textures/modern_projection/'


class Theme(object):
    scale = 1.
    motion = True
    input_font_scale = 1.
    listeners = set()
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

    @classmethod
    def configure(cls, scale, motion):
        game = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
        # GetScreenViewInfo rounds its canvas up to a whole GUI-scale step.
        # GetScreenSize truncates the logical width; their raw ratio therefore
        # is not a fractional GUI scale (e.g. a 1600px window at 3x).
        gui = max(1., round(float(game.GetScreenViewInfo()[0]) / game.GetScreenSize()[0]))
        # Keep the original bitmap glyphs at whole screen magnifications. A
        # fixed .5 becomes too small when the engine changes GUI scale to 2.
        font = max(3., round(scale * 1.7 * gui)) / gui
        if (cls.scale, cls.motion, cls.input_font_scale) == (scale, motion, font):
            return
        cls.scale, cls.motion, cls.input_font_scale = scale, motion, font
        for listener in tuple(cls.listeners):
            listener((scale, motion, font))


def use_theme():
    """Invalidate otherwise memoized app components only when theme changes.

    Theme.scale is read by S/text, so ordinary prop equality cannot see it.
    Keep native controls mounted while recomputing all their design dimensions.
    """
    unused, update = use_state((Theme.scale, Theme.motion, Theme.input_font_scale))

    def subscribe():
        Theme.listeners.add(update)

        def cleanup():
            Theme.listeners.discard(update)
        return cleanup
    use_effect(subscribe, [])


def S(**values):
    dimensions = ('width', 'height', 'minWidth', 'minHeight', 'maxWidth', 'maxHeight',
                  'top', 'right', 'bottom', 'left', 'gap', 'rowGap', 'columnGap', 'flexBasis')
    for name, value in list(values.items()):
        if name in dimensions or name.startswith(('padding', 'margin')):
            if isinstance(value, (int, float)):
                values[name] = value * Theme.scale
    return NativeStyle(**values)


class LabelPrimitive(BaseLabelPrimitive):
    def props_affect_layout(self, prev_props, next_props, style):
        # Retained captions reserve their geometry, including flex-assigned
        # width. Their count/name changes never resize the workspace.
        if next_props.get('glyphSlots'):
            return False
        return BaseLabelPrimitive.props_affect_layout(self, prev_props, next_props, style)

    def apply_props(self, host, fiber, control, prev_props, next_props):
        # Typography changes (including resize) make the base primitive reapply
        # text. Keep its native content empty whenever the glyph atlas owns ink.
        # Preserve the logical text on the fiber for accessibility/debugging.
        native_next = dict(next_props, content='') if next_props.get('rasterText') else next_props
        native_prev = dict(prev_props, content='') if prev_props and prev_props.get('rasterText') else prev_props
        BaseLabelPrimitive.apply_props(self, host, fiber, control, native_prev, native_next)
        if next_props.get('glyphSlots'):
            state = fiber.primitive_state
            if 'glyph_pool' not in state:
                state['glyph_pool'] = []
                for i in range(next_props['glyphSlots']):
                    name = str('ink%d' % i)
                    native.clone(host, '/root/mp_type_tmpl', fiber.native_path, name)
                    state['glyph_pool'].append(host.GetBaseUIControl(fiber.native_path + '/' + name))
            self.paint_glyphs(fiber)

    def apply_layout(self, host, node):
        self.paint_glyphs(node.fiber)

    def paint_glyphs(self, fiber):
        """A bounded atlas pool; changing names never clones controls."""
        state, props = fiber.primitive_state, fiber.props
        if not state.get('glyph_pool') or not state.get('_layout_applied'):
            return
        width, height = state['_layout_applied'][:2]
        unused_sx, sy = state.get('_visual_scale', (1., 1.))
        font = props['fontSize'] * sy
        value = props.get('content', '')
        color = props.get('color') or Theme.ink
        alpha = state.get('_inherited_opacity', 1.) * color.a
        signature = (value, font, width, height, color.to_rgb_tuple(), props.get('textAlign'),
                     props.get('rasterText'), props.get('glyphLines'))
        if state.get('glyph_paint') == signature:
            # Dialog fades only change alpha. Avoid reassigning textures,
            # positions and sizes for every retained inventory glyph each frame.
            if state.get('glyph_alpha') != alpha:
                for patch in state['glyph_pool'][:state.get('glyph_visible', 0)]:
                    patch.SetAlpha(alpha)
                state['glyph_alpha'] = alpha
            return
        state['glyph_paint'] = signature
        state['glyph_alpha'] = alpha
        pieces, advance, row = [], 0., 0
        widths = [0.]
        for char in value[:props['glyphSlots']]:
            data = ASSETS.get(char)
            if data is None:
                break
            if advance + data[3]*font > width:
                if row+1 >= props.get('glyphLines', 1):
                    break
                row, advance = row+1, 0.
                widths.append(0.)
            pieces.append((data, row, advance))
            advance += data[3]*font
            widths[row] = advance
        state['glyph_visible'] = len(pieces) if props.get('rasterText') else 0
        for i, patch in enumerate(state['glyph_pool']):
            shown = i < len(pieces) and props.get('rasterText')
            patch.SetVisible(bool(shown), False)
            if shown:
                data, row, x = pieces[i]
                name, w, h, unused_step = data
                if props.get('textAlign') == TextAlignment.center:
                    x += (width-widths[row])/2.
                patch.asImage().SetSprite(TEX + 'type/' + name)
                patch.asImage().SetSpriteColor(color.to_rgb_tuple())
                patch.SetPosition((x, row*font*1.5))
                patch.SetSize((w*font, h*font))
                patch.SetAlpha(alpha)


class PaperDollPrimitive(BasePaperDollPrimitive):
    def apply_props(self, host, fiber, control, prev_props, next_props):
        if next_props.get('managed'):
            return  # Scene owns native submissions; props remain inspectable.
        if prev_props and prev_props.get('renderKey') != next_props.get('renderKey'):
            prev_props = None
        BasePaperDollPrimitive.apply_props(self, host, fiber, control, prev_props, next_props)


class InputPrimitive(BaseInputPrimitive):
    def apply_props(self, host, fiber, control, prev_props, next_props):
        BaseInputPrimitive.apply_props(self, host, fiber, control, prev_props, next_props)
        scale = next_props.get('fontScale', 1.)
        if prev_props is None or prev_props.get('fontScale') != scale:
            label = host.GetBaseUIControl(fiber.native_path + '/centering_panel/clipper_panel/display_text')
            label.asLabel().SetTextFontSize(scale)

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
        xs, ys = (0., rx, width - rx, width), (0., ry, height - ry, height)
        if fiber.props.get('snapEdges'):
            # The native image renderer rounds each patch separately. Shared
            # integral cuts keep translucent patches from overlapping at joins.
            xs = (0., round(rx), round(width - rx), width)
            ys = (0., round(ry), round(height - ry), height)
        for i, patch in enumerate(state['patches']):
            row_index, col = i // 3, i % 3
            if old is None or old[:4] != signature[:4]:
                patch.SetPosition((xs[col], ys[row_index]))
                patch.SetSize((max(0., xs[col + 1] - xs[col]),
                               max(0., ys[row_index + 1] - ys[row_index])))
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
    use_theme()
    # The native edit box already reserves text/caret padding; adding another
    # inset would clip digits in compact auxiliary-value fields.
    return Panel(style=style, children=[
        rounded_skin(Theme.tint, 5),
        NativeInput(value=value, onChange=onChange, fontScale=Theme.input_font_scale,
                    style=S(width='100%', height='100%', zIndex=2))])


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
    # SDK move callbacks also require is_handle_button_move_event in JSON.
    template_path = '/root/mp_pointer_tmpl'

    def apply_props(self, host, fiber, control, prev_props, next_props):
        BaseButtonPrimitive.apply_props(self, host, fiber, control, prev_props, next_props)
        tracker = fiber.primitive_state.get('pointer_tracker')
        if tracker is None:
            motion = clientApi.GetEngineCompFactory().CreateActorMotion(clientApi.GetLocalPlayerId())
            tracker = PointerTracker(host, fiber, motion, is_touch)
            fiber.primitive_state['pointer_tracker'] = tracker
            if not hasattr(host, '_projection_pointer_surfaces'):
                host._projection_pointer_surfaces = set()
            host._projection_pointer_surfaces.add(tracker)
        tracker.props = next_props
        if next_props.get('enabled') is False:
            tracker.cancel({})
        button = control.asButton()
        if prev_props is None:
            button.AddHoverEventParams()
            for name, method in (('down', 'SetButtonTouchDownCallback'), ('move', 'SetButtonTouchMoveCallback'),
                                 ('up', 'SetButtonTouchUpCallback'), ('cancel', 'SetButtonTouchCancelCallback'),
                                 ('move_out', 'SetButtonTouchMoveOutCallback'),
                                 ('enter', 'SetButtonHoverInCallback'), ('leave', 'SetButtonHoverOutCallback')):
                getattr(button, method)(getattr(tracker, name))

    def unmount(self, host, fiber):
        tracker = fiber.primitive_state.get('pointer_tracker')
        if tracker:
            tracker.cancel({})
            host._projection_pointer_surfaces.discard(tracker)
        BaseButtonPrimitive.unmount(self, host, fiber)


Pointer = PointerPrimitive()


@Component
def Scroll(style=None, children=None, resetKey=None):
    """Native wheel/touch scrolling with a proportional, draggable app thumb."""
    use_theme()
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
        Pointer(ref=rail, retainCapture=True, onDown=down, onMove=move, onUp=up, onCancel=up,
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
        # Newly introduced labels may contain a glyph absent from the existing
        # atlas. Give native fallback text a real box even before its first
        # engine measurement; zero-width row children otherwise draw no ink.
        advance = sum(.62 if ord(char) < 128 else 1. for char in value) * font
        props['style'] = NativeStyle(width=advance+1., height=font*1.4).merge(S(**style))
    return NativeText(**props)


def retained_text(value, size=12, color=None, center=False, slots=40, lines=1, **style):
    """Fixed-size dynamic captions using the existing font/glyph assets."""
    if isinstance(value, bytes):
        value = value.decode('utf8')
    value = value or ''
    values = dict(height=size*1.5*lines, clipsChildren=True)
    values.update(style)
    return NativeText(content=value, fontSize=size*Theme.scale, color=color or Theme.ink,
                      shadow=False, rasterText=all(char in ASSETS for char in value),
                      glyphSlots=slots, glyphLines=lines, textAlign=TextAlignment.center if center else TextAlignment.left,
                      style=S(**values))


def row(children, **style):
    values = dict(flexDirection=FlexDirection.row, alignItems=AlignItems.center, gap=6)
    values.update(style)
    return Panel(style=S(**values), children=children)


def rounded_skin(color, radius=7):
    return Rounded(color=color, radius=radius * Theme.scale,
                   style=S(position=Position.absolute, left=0, top=0, width='100%', height='100%', zIndex=-3))


def surface(children=None, color=None, radius=7, key=None, **style):
    content = list(children) if isinstance(children, (list, tuple)) else ([children] if children is not None else [])
    radius = min(radius, style.get('height', 32) / 2.) if isinstance(style.get('height', 32), (int, float)) else radius
    inset = dict((k, style.pop(k)) for k in list(style) if k.startswith('padding') or k in ('gap', 'alignItems', 'justifyContent'))
    inset['width'] = '100%'
    if style.get('height') is not None:
        inset['height'] = '100%'
    return Panel(key=key, cacheLayout=True, style=S(**style), children=[rounded_skin(color or Theme.white, radius), Panel(style=S(**inset), children=content)])


def icon(name, color=None, size=18):
    return Image(src=TEX + 'icons/' + ('array' if name == 'array_vertical' else name),
                 rotate=90 if name == 'array_vertical' else 0, rotatePivot=(.5,.5),
                 color=color or Theme.muted, style=S(width=size, height=size))


def line():
    return Image(color=Theme.line, style=S(height=1, width='100%', marginVertical=10))


def transparent(unused):
    return Image(color=Colors.transparent)


@Component
def PageMotion(page=None, children=None, width=760, height=440):
    use_theme()
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
def JellyButton(onClick=None, buttonBuilder=None, style=None, children=None,
                backgroundColor=None, hoverColor=None, radius=4, inset=0, cacheLayout=False):
    use_theme()
    progress, set_progress = use_state(1.)
    feedback, set_feedback = use_state(ButtonState.default)
    stable_feedback = use_callback(set_feedback, [])
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
    wobble = math.exp(-5 * progress) * math.sin(3 * math.pi * progress) if progress < 1. and Theme.motion else 0.
    content = list(children) if isinstance(children, (list, tuple)) else ([children] if children is not None else [])
    skins = []
    if backgroundColor is not None:
        skins.append(rounded_skin(backgroundColor, radius))
    if hoverColor is not None:
        # A local overlay fades above the moving selection, below the text.
        # Hover never updates the selection or schedules a Workspace render.
        strength = 0. if feedback == ButtonState.default else (1. if feedback == ButtonState.pressed else .55)
        skins.append(Animated(key='hover', style=S(position=Position.absolute, left=inset,
            right=inset, top=0, height='100%', zIndex=-1),
            transition=NativeStyle(opacity=strength), duration=.12 if Theme.motion else 0.,
            transitionEasing=Easing.cubic_out,
            children=Rounded(color=hoverColor, radius=radius * Theme.scale, snapEdges=True,
                style=S(width='100%', height='100%'))))
    control = FeedbackButton if hoverColor is not None else Button
    extra = {'onFeedback': stable_feedback} if hoverColor is not None else {}
    return control(onClick=stable_click, buttonBuilder=buttonBuilder, cacheLayout=cacheLayout,
                  style=(style or NativeStyle()).merge(NativeStyle(transform=[Scale(1 + .13 * wobble, 1 - .18 * wobble)])),
                  children=skins + content, **extra)


@Component
def Action(label='', onClick=None, width=None, height=32, accent=False, selected=False,
           enabled=True, glyph=None, danger=False, compact=False, leading=False, labelWidth=None):
    use_theme()
    glyph = glyph or ACTION_ICONS.get(label)
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
    wobble = math.exp(-5 * progress) * math.sin(3.5 * math.pi * progress) if progress < 1. and Theme.motion else 0
    base = Theme.blue if accent else (Theme.tint if selected else Theme.pale)
    if enabled and feedback != ButtonState.default:
        base = base.darken(.10 if feedback == ButtonState.pressed else .035)
    ink = Theme.white if accent else (Theme.red if danger else (Theme.blue if selected else Theme.ink))
    if not enabled:
        base, ink = Theme.pale, Color(0xA8B1BEFF)

    def content():
        contents = []
        if glyph:
            contents.append(icon(glyph, ink, 15 if compact else 17))
        if label:
            contents.append(text(label, 11 if compact else 12, ink) if labelWidth is None else
                            retained_text(label, 11 if compact else 12, ink, width=labelWidth, slots=24, center=True))
        return [rounded_skin(base), row(contents, width='100%' if leading else None,
            justifyContent=JustifyContent.flex_start if leading else JustifyContent.center,
            paddingHorizontal=4 if compact else 9, gap=4 if compact else 6)]
    children = list(use_memo(content, [label, glyph, compact, accent, selected, danger, enabled, feedback, leading, labelWidth, Theme.scale]))
    return FeedbackButton(buttonBuilder=transparent, onFeedback=stable_feedback, onClick=stable_click if enabled else None,
                  style=S(width=width, height=height, flexShrink=0,
                          opacity=1,
                          transform=[Scale(1 + .13 * wobble, 1 - .18 * wobble)]), children=children)


@Component
def Range(label='', value=0., minimum=0., maximum=1., onChange=None, unit='', integer=False):
    use_theme()
    current, set_current = use_state(value)
    track, knob = use_ref(None), use_ref(None)
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
        if not all(r.current for r in (track, knob)):
            return
        width = track.current.GetSize()[0]
        age = max(0., now - pulse.current)
        swell = 1 + .16 * math.exp(-18 * age) if Theme.motion and age < .4 else 1.
        size = 15 * Theme.scale * swell
        signature = (width, normalized, size, Theme.scale)
        if applied.current == signature:
            return
        applied.current = signature
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
            Image(color=Theme.line, style=S(position=Position.absolute, top=11, height=4, width='100%', zIndex=1)),
            Image(color=Theme.blue, style=S(position=Position.absolute, left=0, top=11, height=4, width='100%', zIndex=2,
                transform=[Scale(normalized, 1., origin=(0., 0.))])),
            Image(ref=knob, src=TEX + 'knob', style=S(position=Position.absolute, width=15, height=15, zIndex=3)),
            Slider(value=normalized, steps=1, onChange=stable_change, style=S(width='100%', height=26, zIndex=4)),
          ])])])


@Component
def Segments(items=None, value=None, onChange=None, width=216):
    use_theme()
    items = items or []
    index = next((i for i, pair in enumerate(items) if pair[0] == value), 0)
    destination, set_destination = use_state(index)

    def travel():
        # Begin after the parent has committed its new page/parameters. Otherwise
        # their layout work consumes the first half of this short transition.
        set_destination(index)
    use_effect(travel, [index])
    cell = (width - 6) / max(1, len(items))
    # The moving fill and hit targets share an unpadded coordinate system.
    # Nesting absolute insets inside surface(padding=3) applied the inset twice.
    return Panel(style=S(width=width, height=32), children=[
        rounded_skin(Theme.pale, 5),
        Animated(style=S(position=Position.absolute, left=4, top=3, width=cell - 2, height=26),
                 transition=NativeStyle(transform=[Translate(destination * cell * Theme.scale, 0)]),
                 duration=.30 if Theme.motion else 0., transitionEasing=Easing.cubic_in_out,
                 children=surface(color=Theme.tint, radius=4, width='100%', height='100%', children=[
                     Image(color=Theme.blue, style=S(position=Position.absolute,
                         left=8, right=8, bottom=0, height=2))])),
        row([JellyButton(key=pair[0], buttonBuilder=transparent, onClick=partial(onChange, pair[0]),
                    hoverColor=Color(0x477AF42E), radius=4, inset=1,
                    style=S(width=cell, height=26),
                    children=row(([icon(SEGMENT_ICONS[pair[1]], Theme.blue if pair[0] == value else Theme.muted, 13)]
                                  if pair[1] in SEGMENT_ICONS else []) +
                                 [text(pair[1], 11, Theme.blue if pair[0] == value else Theme.muted)],
                                 width='100%', gap=5, justifyContent=JustifyContent.center)) for pair in items], gap=0,
            position=Position.absolute, left=3, top=3, width=width - 6, height=26)])
