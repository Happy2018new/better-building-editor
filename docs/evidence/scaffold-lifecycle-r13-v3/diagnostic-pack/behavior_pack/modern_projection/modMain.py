from mod.common.mod import Mod
import mod.client.extraClientApi as clientApi
@Mod.Binding(name='ScaffoldLifecycleDiagnostic',version='1.0.0')
class ScaffoldLifecycleDiagnostic(object):
 @Mod.InitClient()
 def client(self):
  clientApi.RegisterSystem('ScaffoldLifecycleDiagnostic','Client','modern_projection.client_system.ScaffoldDiagnosticClientSystem')
 @Mod.InitServer()
 def server(self):
  print('ScaffoldLifecycleDiagnostic server library ready')
