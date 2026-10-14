import mod.client.extraClientApi as api
system=api.GetSystem('NemcProjectionCleanDemo','Client')
saved=getattr(system,'cauldron_audit',None)
factory=api.GetEngineCompFactory()
cam=factory.CreateCamera(api.GetLevelId())
cam.ResetCameraPos()
cam.UnDepartCamera()
cam.LockModCameraPitch(False)
cam.LockModCameraYaw(False)
_result={'destroy':system.DestroyClientEntity(saved['entity']) if saved else None,'pitch_locked':cam.IsModCameraLockPitch(),'yaw_locked':cam.IsModCameraLockYaw(),'ticks':system.render_ticks}
