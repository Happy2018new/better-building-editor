import mod.client.extraClientApi as api
ClientSystem=api.GetClientSystemCls()
class ScaffoldDiagnosticClientSystem(ClientSystem):
 def __init__(self,namespace,systemName):
  ClientSystem.__init__(self,namespace,systemName)
  self.ui_initialized=False
  self.render_ticks=0
  self.ListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'UiInitFinished',self,self.ui_init)
  self.ListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'GameRenderTickEvent',self,self.render_tick)
 def ui_init(self,unused):
  self.ui_initialized=True
  self.render_ticks=0
 def render_tick(self,unused):
  if self.ui_initialized:self.render_ticks+=1
 def Destroy(self):
  self.UnListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'UiInitFinished',self,self.ui_init)
  self.UnListenForEvent(api.GetEngineNamespace(),api.GetEngineSystemName(),'GameRenderTickEvent',self,self.render_tick)
