# -*- coding: utf-8 -*-

import mod.client.extraClientApi as clientApi
from .pyreact import *
from .pyreact.navigator import navigator
from .examples.AnimationDemo import AnimationDemo

ClientSystem = clientApi.GetClientSystemCls()


class HelloClientSystem(ClientSystem):
    def __init__(self, namespace, systemName):
        ClientSystem.__init__(self, namespace, systemName)
        runtime_init(self, debug=True)
        self.ListenForEvent(
            clientApi.GetEngineNamespace(),
            clientApi.GetEngineSystemName(),
            "UiInitFinished",
            self,
            self.UiInitFinished,
        )

    def UiInitFinished(self, _):
        navigator.push(AnimationDemo())

    def Destroy(self):
        pass
