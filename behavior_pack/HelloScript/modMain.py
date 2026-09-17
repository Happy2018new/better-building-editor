# -*- coding: utf-8 -*-

from mod.common.mod import Mod
import mod.client.extraClientApi as clientApi
import mod.server.extraServerApi as serverApi


@Mod.Binding(name="HelloMod", version="1.0.0")
class HelloClient(object):
    @Mod.InitClient()
    def HelloClientInit(self):
        clientApi.RegisterSystem(
            "HelloMod",
            "HelloClientSystem",
            "HelloScript.HelloClientSystem.HelloClientSystem",
        )
        print("=====> Hello Init <=====")

    @Mod.DestroyClient()
    def HelloClientDestroy(self):
        print("=====> Hello Destroy <=====")

    @Mod.InitServer()
    def HelloServerInit(self):
        serverApi.RegisterSystem(
            "HelloMod",
            "HelloServerSystem",
            "HelloScript.HelloServerSystem.HelloServerSystem",
        )
        print("=====> Hello(Server Side) Init <=====")

    @Mod.DestroyServer()
    def HelloServerDestroy(self):
        print("=====> Hello(Server Side) Destroy <=====")
