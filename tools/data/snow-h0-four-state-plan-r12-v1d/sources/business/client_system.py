# -*- coding: utf-8 -*-
import mod.client.extraClientApi as clientApi
from .pyreact import runtime_init, navigator
from .projection.bridge import ClientBridge
from .projection.session import Session
from .projection.ui import Workspace
from .projection.tool_hud import TerminalHud
from .projection.tool_items import TERMINAL, SURVEY_WAND, item_name
from .projection.input_mode import is_touch

ClientSystem = clientApi.GetClientSystemCls()


class ModernProjectionClientSystem(ClientSystem):
    def __init__(self, namespace, systemName):
        ClientSystem.__init__(self, namespace, systemName)
        runtime_init(self, debug=True)
        self.bridge = None
        self.session = None
        self.hud = None
        self.staff_aura = None
        self.nearby_staff_auras = None
        self.projection_loaded_chunks = set()
        self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(), 'UiInitFinished', self, self.UiInitFinished)
        self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(), 'DimensionChangeFinishClientEvent', self, self.dimension_changed)
        self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(), 'GameRenderTickEvent', self, self.render_tick)
        self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(),
                            'ChunkLoadedClientEvent', self, self.chunk_loaded)
        self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(),
                            'ChunkAcquireDiscardedClientEvent', self, self.chunk_unloaded)
        self.ListenForEvent('ModernProjection', 'ModernProjectionServerSystem', 'ProjectionResponse', self, self.response)
        self.ListenForEvent('ModernProjection', 'ModernProjectionServerSystem', 'BlockCatalogueResponse', self, self.block_catalogue)
        self.ListenForEvent('ModernProjection', 'ModernProjectionServerSystem', 'OpenProjectionUi', self, self.open_from_terminal)
        self.ListenForEvent('ModernProjection', 'ModernProjectionServerSystem', 'WorldToolPoint', self, self.world_tool_point)
        self.ListenForEvent('ModernProjection', 'ModernProjectionServerSystem', 'StaffAuraState', self, self.staff_aura_state)
        self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(),
                            'OnCarriedNewItemChangedClientEvent', self, self.carried_changed)
        for event in ('StartDestroyBlockClientEvent', 'PlayerTryDestroyBlockClientEvent'):
            self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(),
                                event, self, self.tool_prevent_break)
        for event,handler in (
                ('RightClickBeforeClientEvent',self.tool_use),
                ('TapBeforeClientEvent',self.tool_touch_tap),
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
        from .projection.staff_aura import StaffAura, NearbyStaffAuras
        self.staff_aura = StaffAura(self.bridge)
        self.nearby_staff_auras = NearbyStaffAuras(self.bridge)

    def chunk_loaded(self, args):
        self.projection_loaded_chunks.add((args['dimension'], args['chunkPosX'], args['chunkPosZ']))

    def chunk_unloaded(self, args):
        self.projection_loaded_chunks.discard((args['dimension'], args['chunkPosX'], args['chunkPosZ']))

    def open_workspace(self):
        if self.session is not None and not navigator.contains('modern_projection_workspace'):
            navigator.push(Workspace(session=self.session), key='modern_projection_workspace')

    def open_from_terminal(self, unused=None):
        if unused is None and (self.hud is None or self.hud.carried != TERMINAL):
            return
        self.open_workspace()

    def carried_changed(self, args):
        if self.hud is not None:
            self.hud.carried = item_name(args.get('itemDict'))
            self.hud.update()

    def world_tool_point(self, args):
        if self.bridge is not None:
            self.bridge.world_tool_point(args)

    def staff_aura_state(self, args):
        if self.nearby_staff_auras:
            # Query only loaded players in this client's current dimension.
            players = self.bridge.factory.CreateGame(self.bridge.level).GetEntitiesAroundByType(
                self.bridge.player, 64, clientApi.GetMinecraftEnum().EntityType.Player) or []
            carried = args.get('carried', {})
            self.nearby_staff_auras.sync(dict((player, carried[player])
                for player in players if player in carried))

    def tool_prevent_break(self, args):
        if self.hud and self.hud.carried in (SURVEY_WAND, TERMINAL):
            args['cancel'] = True
        elif self.bridge:
            # StartDestroy carries pos; PlayerTryDestroy carries x/y/z.
            pos = args.get('pos')
            if pos is None and all(axis in args for axis in ('x', 'y', 'z')):
                pos = tuple(args[axis] for axis in ('x', 'y', 'z'))
            if pos is not None:
                self.bridge.projection_interaction(tuple(int(v) for v in pos))

    def tool_use(self, args):
        if self.hud is None or self.hud.carried not in (SURVEY_WAND, TERMINAL):
            if self.bridge and self.bridge.projection_occupancy is not None:
                self.bridge.projection_interaction(touch=is_touch())
            return
        if navigator.contains('modern_projection_workspace'):
            return
        if self.hud.carried == TERMINAL:
            args['cancel'] = True
            self.open_workspace()

    def tool_touch_tap(self, args):
        if self.hud is None or self.hud.carried not in (SURVEY_WAND,TERMINAL):
            if self.bridge:
                self.bridge.projection_interaction(touch=True)
            return
        if navigator.contains('modern_projection_workspace'):
            return
        if self.hud.carried == TERMINAL:
            args['cancel'] = True
            self.open_workspace()

    def tool_import_click(self, args):
        if self.bridge and (self.hud is None or self.hud.carried not in (SURVEY_WAND, TERMINAL)):
            self.bridge.projection_interaction()
        if self.hud is None or self.hud.carried != SURVEY_WAND or is_touch():
            return
        if navigator.contains('modern_projection_workspace'):
            return
        args['cancel'] = True
        if None not in self.bridge.corners:
            self.tool_hud_action()

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
        self.NotifyToServer('WorldToolRequest', {'action': 'reset'})

    def response(self, args):
        if self.bridge:
            self.bridge.receive(args)

    def block_catalogue(self, args):
        if self.bridge:
            self.bridge.receive_catalogue(args)

    def dimension_changed(self, args):
        if self.staff_aura:
            self.staff_aura.clear()
        if self.nearby_staff_auras:
            self.nearby_staff_auras.clear()
        if self.bridge:
            self.bridge.dimension_changed(args)

    def render_tick(self, unused):
        if self.bridge:
            self.bridge.follow_projection()
            self.bridge.update_projection_occupancy()
        if self.hud:
            self.hud.update()
        if self.staff_aura and self.hud:
            self.staff_aura.update(self.hud.carried, not navigator.contains('modern_projection_workspace'))
        if self.nearby_staff_auras:
            self.nearby_staff_auras.update()

    def Destroy(self):
        # These listeners belong to the system, not individual projections.
        self.UnListenAllEvents()
        if self.staff_aura:
            self.staff_aura.clear()
        if self.nearby_staff_auras:
            self.nearby_staff_auras.clear()
        if self.bridge:
            self.bridge.destroy()
        if self.hud:
            self.hud.destroy()
