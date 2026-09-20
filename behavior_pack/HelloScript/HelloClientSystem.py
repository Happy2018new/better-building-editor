# -*- coding: utf-8 -*-
import mod.client.extraClientApi as clientApi
from .pyreact import runtime_init, navigator
from .projection.bridge import ClientBridge
from .projection.session import Session
from .projection.ui import Workspace

ClientSystem = clientApi.GetClientSystemCls()


class HelloClientSystem(ClientSystem):
    def __init__(self, namespace, systemName):
        ClientSystem.__init__(self, namespace, systemName)
        runtime_init(self, debug=True)
        self.bridge = None
        self.session = None
        self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(), 'UiInitFinished', self, self.UiInitFinished)
        self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(), 'OnKeyPressInGame', self, self.key)
        self.ListenForEvent(clientApi.GetEngineNamespace(), clientApi.GetEngineSystemName(), 'DimensionChangeFinishClientEvent', self, self.dimension_changed)
        self.ListenForEvent('ModernProjection', 'HelloServerSystem', 'ProjectionResponse', self, self.response)
        self.ListenForEvent('ModernProjection', 'HelloServerSystem', 'BlockCatalogueResponse', self, self.block_catalogue)

    def UiInitFinished(self, unused):
        if self.session is not None:
            return
        self.bridge = ClientBridge(self)
        self.session = Session(self.bridge)
        self.bridge.session = self.session
        self.session.initialize()
        navigator.push(Workspace(session=self.session), key='modern_projection_workspace')

    def key(self, args):
        if self.session is None or str(args.get('isDown')) != '1':
            return
        key = str(args.get('key'))
        if navigator.contains('modern_projection_workspace'):
            return
        if args.get('screenName') not in ('hud_screen', 'in_game_play_screen'):
            return
        if key == '80':
            navigator.push(Workspace(session=self.session), key='modern_projection_workspace')
        elif key in ('117', '118'):
            self.session.action(self.bridge.mark, 0 if key == '117' else 1)

    def response(self, args):
        if self.bridge:
            self.bridge.receive(args)

    def block_catalogue(self, args):
        if self.bridge:
            self.bridge.receive_catalogue(args)

    def dimension_changed(self, args):
        if self.bridge:
            self.bridge.dimension_changed(args)

    def Destroy(self):
        if self.bridge:
            self.bridge.destroy()
