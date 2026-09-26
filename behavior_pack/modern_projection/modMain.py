# -*- coding: utf-8 -*-

from mod.common.mod import Mod
import mod.client.extraClientApi as clientApi
import mod.server.extraServerApi as serverApi


@Mod.Binding(name="ModernProjection", version="0.1.0")
class ModernProjectionMod(object):
    @Mod.InitClient()
    def init_client(self):
        clientApi.RegisterSystem(
            "ModernProjection",
            "ModernProjectionClientSystem",
            "modern_projection.client_system.ModernProjectionClientSystem",
        )
        print("=====> ModernProjection Client Init <=====")

    @Mod.DestroyClient()
    def destroy_client(self):
        print("=====> ModernProjection Client Destroy <=====")

    @Mod.InitServer()
    def init_server(self):
        serverApi.RegisterSystem(
            "ModernProjection",
            "ModernProjectionServerSystem",
            "modern_projection.server_system.ModernProjectionServerSystem",
        )
        print("=====> ModernProjection Server Init <=====")

    @Mod.DestroyServer()
    def destroy_server(self):
        print("=====> ModernProjection Server Destroy <=====")
