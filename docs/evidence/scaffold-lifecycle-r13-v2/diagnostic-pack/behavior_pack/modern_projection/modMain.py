from mod.common.mod import Mod
@Mod.Binding(name='ScaffoldLifecycleDiagnostic',version='1.0.0')
class ScaffoldLifecycleDiagnostic(object):
 @Mod.InitClient()
 def client(self):
  print('ScaffoldLifecycleDiagnostic client library ready')
 @Mod.InitServer()
 def server(self):
  print('ScaffoldLifecycleDiagnostic server library ready')
