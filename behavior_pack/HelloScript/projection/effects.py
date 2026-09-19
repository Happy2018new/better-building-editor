# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""One non-interactive, bounded sprite pool for page-wide pointer feedback."""
import time
import mod.client.extraClientApi as clientApi
from ..pyreact import Component, Panel, Position, use_ref
from ..pyreact.hooks import use_animation_frame
from ..pyreact.primitives import PanelPrimitive
from .widgets import Theme, S, Image, TEX, use_theme
from .pointer import release_pointers

FRAME_UVS = tuple(((i % 4) * 112, (i // 4) * 112) for i in range(16))


class ClickObserverPrimitive(PanelPrimitive):
    """Native global menu-select mapping, explicitly non-consuming."""
    template_path = '/root/mp_click_observer_tmpl'

    def apply_props(self, host, fiber, control, prev_props, next_props):
        if prev_props is not None:
            return
        motion = clientApi.GetEngineCompFactory().CreateActorMotion(clientApi.GetLocalPlayerId())

        def down(screen, args):
            # Native input_panel can deliver the same down through two routes.
            # PC pointer coordinates also stay correct after moving the window.
            point = motion.GetMousePosition()
            if point is None:
                point = (args['TouchPosX'], args['TouchPosY'])
            contact = (args.get('TouchId'), point)
            now = time.time()
            previous = fiber.primitive_state.get('last_contact')
            if previous and previous[0] == contact and now - previous[1] < .02:
                return False
            fiber.primitive_state['last_contact'] = (contact, now)
            fiber.props['onPointer'](point)
            return False
        def up(screen, args):
            release_pointers(host, args)
            return False

        # Both bindings observe the same non-consuming global input mapping.
        # A lost control-local up must not leave PC mouse polling enabled.
        names = []
        binder = clientApi.GetViewBinderCls()
        for phase, callback, flag in (('down', down, binder.BF_ButtonClickDown),
                                       ('up', up, binder.BF_ButtonClickUp)):
            name = '__projection_pointer_%s_%s' % (phase, id(fiber))
            callback.__name__ = name
            callback.binding_flags = flag
            callback.binding_name = '#modern_projection_pointer_down'
            setattr(host.__class__, name, callback)
            host._process_default(getattr(host, name), host.screen_name)
            names.append(name)
        fiber.primitive_state['binding_methods'] = names

    def unmount(self, host, fiber):
        for name in fiber.primitive_state.pop('binding_methods', []):
            host._process_default_unregister(getattr(host, name), host.screen_name)
            delattr(host.__class__, name)
        for tracker in tuple(getattr(host, '_projection_pointers', ())):
            tracker.cancel({})
        PanelPrimitive.unmount(self, host, fiber)


ClickObserver = ClickObserverPrimitive()


@Component
def ClickEffects():
    use_theme()
    overlay = use_ref(None)
    sprites = [use_ref(None) for unused in range(6)]
    live = use_ref(lambda: {})
    cursor = use_ref(0)

    def burst(point):
        if not Theme.motion or point is None or overlay.current is None:
            return
        ox, oy = overlay.current.GetGlobalPosition()
        width, height = overlay.current.GetSize()
        x, y = point[0] - ox, point[1] - oy
        if not (0 <= x < width and 0 <= y < height):
            return
        slot = cursor.current
        cursor.current = (slot + 1) % len(sprites)
        control = sprites[slot].current
        if control is None:
            return
        size = 56 * Theme.scale
        control.SetSize((size, size))
        control.SetPosition((x - size / 2., y - size / 2.))
        control.asImage().SetSpriteUV(FRAME_UVS[0])
        control.SetVisible(True)
        live.current[slot] = (time.time(), 0, Theme.scale)

    def tick(now):
        for slot, (started, previous, scale) in list(live.current.items()):
            frame = int((now - started) / .02)
            control = sprites[slot].current
            if frame >= len(FRAME_UVS) or not Theme.motion or scale != Theme.scale:
                control.SetVisible(False)
                del live.current[slot]
            elif frame != previous:
                control.asImage().SetSpriteUV(FRAME_UVS[frame])
                live.current[slot] = (started, frame, scale)

    use_animation_frame(tick)
    # An input mapping has no button hit area and does not steal focus/hover.
    return Panel(ref=overlay, style=S(position=Position.absolute, left=0, top=0,
        width='100%', height='100%', clipsChildren=True, zIndex=200), children=[
        ClickObserver(onPointer=burst, style=S(position=Position.absolute, width='100%', height='100%'))] + [
        Image(ref=ref, key='click%d' % i, src=TEX + 'click_flecks', uv=FRAME_UVS[0], uvSize=(112, 112),
            style=S(position=Position.absolute, width=0, height=0, visible=False))
        for i, ref in enumerate(sprites)])
