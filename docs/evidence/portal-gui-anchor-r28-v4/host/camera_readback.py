"""Read the actual mounted Scene camera without changing its callback or pose."""
CAMERA_READBACK = '''row=json.loads(_result)
from modern_projection.pyreact.debug import _type_name
assert navigator.top is not None
camera_host=navigator.top._host
def camera_walk(fiber):
 yield fiber
 for child in fiber.child_fibers:
  for item in camera_walk(child):yield item
camera_scenes=[fiber for fiber in camera_walk(camera_host._root_fiber)
 if _type_name(fiber)=='Scene' and fiber.props.get('session') is s]
assert len(camera_scenes)==1,len(camera_scenes)
camera_scene=camera_scenes[0]
camera_hooks=[slot for slot in camera_scene.hooks if slot.get('type')=='animation_frame']
assert len(camera_hooks)==1,len(camera_hooks)
camera_hook=camera_hooks[0]
assert camera_hook['active'] and camera_hook.get('_registration_id')==id(camera_hook)
assert camera_host._animation_frames.get(id(camera_hook)) is camera_hook
camera_callback=camera_hook['callback']
camera_code=getattr(camera_callback,'func_code',getattr(camera_callback,'__code__',None))
camera_cells=getattr(camera_callback,'func_closure',getattr(camera_callback,'__closure__',None))
assert camera_code is not None and camera_cells is not None
camera_values=dict(zip(camera_code.co_freevars,[cell.cell_contents for cell in camera_cells]))
assert 'camera' in camera_values and camera_values.get('session') is s
actual_camera=camera_values['camera']
actual_pose=(actual_camera.yaw,actual_camera.pitch,actual_camera.zoom)
row['camera_readback']={'scene_fiber_id':id(camera_scene),'camera_object_id':id(actual_camera),
 'source':'actual mounted Scene animation callback closure; read only',
 'pose':actual_pose,'target':tuple(actual_camera.target),
 'session_matches_scene':tuple(s.camera_pose)==actual_pose,
 'at_target':actual_pose==tuple(actual_camera.target),
 'dragging':actual_camera.dragging,'velocity':tuple(actual_camera.velocity),
 'render_angles':actual_camera.render_angles()}
_result=json.dumps(row)
'''
