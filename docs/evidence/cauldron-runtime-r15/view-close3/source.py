import mod.client.extraClientApi as api
system=api.GetSystem('NemcProjectionCleanDemo','Client')
origin=(-8, -60, 8)
local=(1.0, 0.5, 23.0)
offset=(0.0, 20.0, -18.0)
point=tuple(origin[i]+local[i] for i in range(3))
position=tuple(point[i]+offset[i] for i in range(3))
rot=api.GetRotFromDir(tuple(point[i]-position[i] for i in range(3)))
cam=api.GetEngineCompFactory().CreateCamera(api.GetLevelId())
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
cam.DepartCamera()
_result={'position':position,'target':point,'requested_rotation':(rot[0],rot[1]+180.,0.),'set':(cam.SetCameraPos(position),cam.SetCameraRotation((rot[0],rot[1]+180.,0.))),'ticks':system.render_ticks}
