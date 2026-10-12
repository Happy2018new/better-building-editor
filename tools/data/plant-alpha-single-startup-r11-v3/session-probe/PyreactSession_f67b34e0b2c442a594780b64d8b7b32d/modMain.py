from mod.common.mod import Mod
import sys
@Mod.Binding(name='PyreactSession_f67b34e0b2c442a594780b64d8b7b32d', version='1.0.0')
class SessionProbe(object):
    @Mod.InitClient()
    def client(self):
        sys._pyreact_mcdk_session = '70a6ef937040443fac558c9205a5fd9a'
    @Mod.InitServer()
    def server(self):
        sys._pyreact_mcdk_session = '70a6ef937040443fac558c9205a5fd9a'
