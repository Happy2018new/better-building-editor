# pylint: disable=unexpected-keyword-arg,E1123
"""Mount bounded, independently owned water PaperDolls in the existing Scene."""
from ..pyreact import Component, Panel, Position, PaperDollRenderType, use_ref, use_state, use_effect
from .widgets import Doll, S


@Component
def LiquidTile(identity=None, registry=None, width=400, height=300):
    dolls = [use_ref(None), use_ref(None)]
    surfaces = [use_ref(None), use_ref(None)]
    def register():
        entry = {'dolls': dolls, 'surfaces': surfaces}
        registry[identity] = entry
        def cleanup():
            renderer = entry.get('renderer')
            if renderer is not None:
                renderer.close()
            if registry.get(identity) is entry:
                registry.pop(identity, None)
        return cleanup
    use_effect(register, [identity, registry])
    return Panel(cacheLayout=True, style=S(position=Position.absolute, width=width, height=height), children=[
        Panel(ref=surfaces[slot], key='water_bank_%d' % slot,
              style=S(position=Position.absolute, width='100%', height='100%'), children=[
            Doll(ref=dolls[slot], managed=True, renderType=PaperDollRenderType.skeleton,
                 style=S(position=Position.absolute, width='100%', height='100%', zIndex=306))])
        for slot in range(2)])


@Component
def LiquidModels(session=None, registry=None, width=400, height=300, keys=()):
    mounted, set_mounted = use_state(())
    def prepare():
        wanted = frozenset(keys)
        retained = tuple(key for key in mounted if key in wanted)
        present = frozenset(retained)
        missing = tuple(key for key in keys if key not in present)
        if missing or retained != mounted:
            alive = [True]
            def step():
                if not alive[0]:
                    return
                if session.camera_dragging:
                    session.bridge.later(.1, step)
                else:
                    set_mounted(retained + missing[:4])
            session.next_frame(step)
            return lambda: alive.__setitem__(0, False)
    use_effect(prepare, [session, keys, mounted])
    wanted = frozenset(keys)
    return Panel(cacheLayout=True, style=S(position=Position.absolute, width=width, height=height), children=[
        LiquidTile(key='liquid_' + repr(identity), identity=identity, registry=registry, width=width, height=height)
        for identity in mounted if identity in wanted])
