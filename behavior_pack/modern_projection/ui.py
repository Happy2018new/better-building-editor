# -*- coding: utf-8 -*-

import mod.client.extraClientApi as clientApi

ScreenNode = clientApi.GetScreenNodeCls()
ViewBinder = clientApi.GetViewBinderCls()
ViewRequest = clientApi.GetViewViewRequestCls()


class ModernProjectionScreen(ScreenNode):
    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        self.mPlayerId = clientApi.GetLocalPlayerId()
        self.mLevelId = clientApi.GetLevelId()
        self.data = param.get("data", {})
        self.client = param.get("client", None)

    def Create(self):
        print("=====> ModernProjection UI Created <=====")

    def OnActive(self):
        pass

    def OnDeactive(self):
        pass

    def Update(self):
        pass

    def Destroy(self):
        print("=====> ModernProjection UI Destroyed <=====")
