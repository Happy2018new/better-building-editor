# -*- coding: utf-8 -*-
import mod.client.extraClientApi as clientApi
from .pyreact import runtime_init, navigator
from .projection.bridge import ClientBridge
from .projection.session import Session
from .projection.ui import Workspace
from .projection.tool_hud import TerminalHud
from .projection.tool_items import TERMINAL, SURVEY_WAND, item_name
from .projection.input_mode import is_touch
import time

ClientSystem = clientApi.GetClientSystemCls()


class HelloClientSystem(ClientSystem):
    def __init__(self, namespace, systemName):
        ClientSystem.__init__(self, namespace, systemName)
        runtime_init(self, debug=True)
        self.bridge = None
        self.session = None
        self.hud = None
        self.tool_touch_pick = None
        self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(), 'UiInitFinished', self, self.UiInitFinished)
        self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(), 'DimensionChangeFinishClientEvent', self, self.dimension_changed)
        self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(), 'GameRenderTickEvent', self, self.render_tick)
        self.ListenForEvent('ModernProjection', 'HelloServerSystem', 'ProjectionResponse', self, self.response)
        self.ListenForEvent('ModernProjection', 'HelloServerSystem', 'BlockCatalogueResponse', self, self.block_catalogue)
        self.ListenForEvent('ModernProjection', 'HelloServerSystem', 'OpenProjectionUi', self, self.open_from_terminal)
        self.ListenForEvent('ModernProjection', 'HelloServerSystem', 'WorldToolPoint', self, self.world_tool_point)
        self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(),
                            'OnCarriedNewItemChangedClientEvent', self, self.carried_changed)
        for event in ('StartDestroyBlockClientEvent', 'PlayerTryDestroyBlockClientEvent'):
            self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(),
                                event, self, self.tool_prevent_break)
        for event,handler in (
                ('RightClickBeforeClientEvent',self.tool_use),
                ('TapBeforeClientEvent',self.tool_touch_tap),
                ('GetEntityByCoordEvent',self.tool_touch_down),
                ('LeftClickBeforeClientEvent',self.tool_import_click)):
            self.ListenForEvent(clientApi.GetEngineNamespace(),clientApi.GetEngineSystemName(),event,self,handler)

    def UiInitFinished(self, unused):
        if self.session is not None:
            return
        self.bridge = ClientBridge(self)
        self.session = Session(self.bridge)
        self.bridge.session = self.session
        self.session.initialize()
        self.hud = TerminalHud(self)

    def open_workspace(self):
        if self.session is not None and not navigator.contains('modern_projection_workspace'):
            navigator.push(Workspace(session=self.session), key='modern_projection_workspace')

    def open_from_terminal(self, unused=None):
        if unused is None and (self.hud is None or self.hud.carried != TERMINAL):
            return
        self.open_workspace()

    def carried_changed(self, args):
        self.tool_touch_pick = None
        if self.hud is not None:
            self.hud.carried = item_name(args.get('itemDict'))
            self.hud.update()

    def world_tool_point(self, args):
        if self.bridge is not None:
            self.bridge.world_tool_point(args)

    def tool_prevent_break(self, args):
        if self.hud and self.hud.carried in (SURVEY_WAND, TERMINAL):
            args['cancel'] = True

    def tool_use(self, args):
        if self.hud is None or self.hud.carried not in (SURVEY_WAND, TERMINAL):
            return
        if navigator.contains('modern_projection_workspace'):
            return
        args['cancel'] = True
        if self.hud.carried == TERMINAL:
            self.open_workspace()
        else:
            try:
                if is_touch():
                    self.tool_mark(self.bridge.factory.CreateCamera(self.bridge.level).GetChosen())
                elif self.bridge.factory.CreatePlayer(clientApi.GetLocalPlayerId()).isSneaking():
                    self.tool_reset()
                else:
                    self.tool_mark_facing()
            except (ValueError, TypeError, KeyError) as error:
                self.bridge.notify(error.args[0])

    def tool_touch_down(self, unused):
        self.tool_touch_pick = None
        if self.hud and self.hud.carried == SURVEY_WAND and not navigator.contains('modern_projection_workspace'):
            # GetChosen is the engine's actual screen-contact hit, independent
            # of whether the player uses a crosshair. Preserve it until the
            # native short-tap event; dragging never reaches that event.
            pick = self.bridge.factory.CreateCamera(self.bridge.level).GetChosen()
            self.tool_touch_pick = (pick,time.time())

    def tool_touch_tap(self, args):
        if self.hud is None or self.hud.carried not in (SURVEY_WAND,TERMINAL):
            return
        if navigator.contains('modern_projection_workspace'):
            return
        args['cancel'] = True
        if self.hud.carried == TERMINAL:
            self.open_workspace()
            return
        cached,self.tool_touch_pick = self.tool_touch_pick,None
        pick = cached[0] if cached and time.time()-cached[1] < .75 else None
        if pick and pick.get('type') == 'Block':
            self.bridge.factory.CreatePlayer(clientApi.GetLevelId()).Swing()
            self.tool_mark(pick)

    def tool_import_click(self, args):
        if self.hud is None or self.hud.carried != SURVEY_WAND or is_touch():
            return
        if navigator.contains('modern_projection_workspace'):
            return
        args['cancel'] = True
        if None not in self.bridge.corners:
            self.tool_hud_action()

    def tool_mark_facing(self):
        pick = self.bridge.factory.CreateCamera(self.bridge.level).PickFacing()
        self.tool_mark(pick)

    def tool_mark(self, pick):
        if not pick or pick.get('type') != 'Block':
            raise ValueError(u'请选择要测绘的方块')
        self.NotifyToServer('WorldToolRequest', {'action': 'point',
            'pos': [int(pick[axis]) for axis in ('x', 'y', 'z')], 'face': pick.get('face')})

    def tool_hud_action(self, unused=None):
        if self.hud is None or self.session is None:
            return
        if self.hud.carried == TERMINAL:
            self.open_workspace()
        elif self.hud.carried == SURVEY_WAND:
            try:
                if None in self.bridge.corners:
                    self.bridge.survey_tip('请先选择两个角点')
                    return
                self.bridge.capture_new()
                self.session.page = 'library'
                self.open_workspace()
            except (ValueError, TypeError, KeyError) as error:
                self.bridge.notify(error.args[0])

    def tool_reset(self, unused=None):
        if self.hud and self.hud.carried == SURVEY_WAND:
            self.NotifyToServer('WorldToolRequest', {'action': 'reset'})

    def response(self, args):
        if self.bridge:
            self.bridge.receive(args)

    def block_catalogue(self, args):
        if self.bridge:
            self.bridge.receive_catalogue(args)

    def dimension_changed(self, args):
        self.tool_touch_pick = None
        if self.bridge:
            self.bridge.dimension_changed(args)

    def render_tick(self, unused):
        if self.bridge:
            self.bridge.follow_projection()
        if self.hud:
            self.hud.update()

    def Destroy(self):
        if self.bridge:
            self.bridge.destroy()
        if self.hud:
            self.hud.destroy()
