"""Pixel regression for work-plane depth; only modifies an unsaved test draft.

Run via run_live_check.py in a managed world. Covers foreground and occluded
grid lines, reverse/underside views, raised demo grid and retained geometry.
"""
import json
import os
import time
import mss
import numpy as np
from PIL import Image
import verify_ui as ui
from native_input_mode import open_workspace
from verify_font_share_polish import game as execute_game
from verify_biome_tint import wait_preview
from verify_interaction import pointer
from projection.camera import OrbitCamera
import capture_screen as capture


def activate_game():
    window = capture._find_game_window(capture._list_windows(), pid=int(os.environ['MCDEV_GAME_PID']))
    assert window
    capture._activate_window(window['hwnd'])


def game(source):
    activate_game()
    return execute_game(source)


def frame(name):
    activate_game()
    time.sleep(.5)
    window=capture._find_game_window(capture._list_windows(),pid=int(os.environ['MCDEV_GAME_PID']))
    left,top,width,height=capture._window_rect(window['hwnd'])
    with mss.MSS() as screen:
        raw=screen.grab(dict(left=left,top=top,width=width,height=height))
        image=Image.frombytes('RGB',raw.size,raw.bgra,'raw','BGRX')
    image.save(ui.OUT / ('grid_depth_' + name + '.png'))
    return image


def view_patches():
    info = game('_result=[s.camera_pose,s.scene_origin,s.scene_size,s.camera_pan,s.camera_pivot]')
    pose, origin, size, pan, pivot = info
    camera = OrbitCamera(*pose)
    camera.pan, camera.pivot = tuple(pan), tuple(pivot) if pivot else None
    ctrl = ui.call('native_control', pointer()['id'])['result']
    width, height = ctrl['size']
    unit = min(width, height)*.72*pose[2]/max(size)
    root = ui.nodes('SafeArea')[0]['children'][0]['layout']
    def patch(frame_image, point, radius=5):
        x, y = camera.project(tuple(point[i]-origin[i] for i in range(3)), size, width, height, unit)
        gui=round(frame_image.width/root['width'])
        x = int((ctrl['global'][0]+x)*gui)
        y = int((ctrl['global'][1]+y)*gui)
        return frame_image.crop((x-radius, y-radius, x+radius+1, y+radius+1))
    return patch


def changed_pixels(a,b):
    return int((np.max(np.abs(np.asarray(a).astype(int)-np.asarray(b).astype(int)),axis=2)>5).sum())


def main():
    capture.user32.SetProcessDPIAware()
    activate_game()
    open_workspace()
    game('''fields=('editor','name','page','tool','direct_mode','section','solo_layer',
                'focus_view','focused','camera_yaw','camera_pitch','zoom','camera_pan',
                'camera_pivot','camera_depth','camera_depth_pose','camera_pose','grid',
                'reduced_motion','box_anchor')
api._grid_depth_saved=dict((key,getattr(s,key)) for key in fields)
from modern_projection.projection.model import Document
blocks=dict(((x,y,z),('minecraft:quartz_block',0))
            for x in range(2,6) for y in range(6) for z in range(2,6))
s._loaded(Document((8,8,8),blocks))
s.focus_view=False;s.focused=None;s.grid=True
s.direct_mode='browse';s.reduced_motion=True;s.box_anchor=None;s.layer(4);s.reset_camera(False)
s.camera_view(0,45,1.2);s.emit()
_result=True''')
    results = {}
    try:
        wait_preview()
        builds = game('_result=len(s.bridge.models)')
        for label, yaw, front, back in (
                ('front', 0, (4,4,6.5), (4,4,1.5)),
                ('back', 180, (4,4,1.5), (4,4,6.5))):
            game('s.camera_view(%r,45,1.2)\ns.set("grid",True)\n_result=True' % yaw)
            time.sleep(.8)
            shown = frame(label+'_on')
            game('s.set("grid",False)\n_result=True')
            hidden = frame(label+'_off')
            patch = view_patches()
            visible_delta = changed_pixels(patch(shown, front), patch(hidden, front))
            occluded_delta = changed_pixels(patch(shown, back), patch(hidden, back))
            results[label] = {'foreground_pixels': visible_delta, 'occluded_pixels': occluded_delta}
            ui.check(label+' grid in front of the wall is visible', visible_delta >= 3)
            ui.check(label+' grid behind the building stays hidden', occluded_delta == 0)
            empty = (4.5, 4, front[2])
            empty_delta = changed_pixels(patch(shown, empty, 0), patch(hidden, empty, 0))
            results[label]['empty_cell_pixels'] = empty_delta
            ui.check(label+' empty grid cells do not cover the building', empty_delta == 0)
        game('s.camera_view(0,-45,1.2)\ns.set("grid",True)\n_result=True')
        time.sleep(.8)
        shown = frame('underside_on')
        game('s.set("grid",False)\n_result=True')
        hidden = frame('underside_off')
        patch = view_patches()
        outside = changed_pixels(patch(shown,(1,4,6.5)),patch(hidden,(1,4,6.5)))
        ui.check('grid also renders from underneath',outside >= 3)
        ui.check('orbit and grid visibility reuse native geometry',game('_result=len(s.bridge.models)')==builds)
        game('''s._loaded(Document((7,9,11),{(0,0,0):('minecraft:quartz_block',0)}))
s.focus_view=False;s.focused=None;s.grid=True;s.layer(3)
s.camera_view(0,90,1.2);s.emit()
_result=True''')
        wait_preview()
        shown = frame('odd_on')
        game('s.set("grid",False)\n_result=True')
        hidden = frame('odd_off')
        patch = view_patches()
        ui.check('odd dimensions keep lines on integer block coordinates',
                 changed_pixels(patch(shown,(3,3,5.5)),patch(hidden,(3,3,5.5))) >= 3)
        game('s.camera_depth=7\ns.set("grid",True)\ns.emit("camera_depth")\n_result=True')
        time.sleep(1.)
        clipped = frame('clipped_on')
        game('s.set("grid",False)\n_result=True')
        clipped_off = frame('clipped_off')
        patch = view_patches()
        ui.check('work grid follows the same view-depth clipping plane',
                 changed_pixels(patch(clipped,(3,3,5.5)),patch(clipped_off,(3,3,5.5))) == 0)
        game('s.camera_depth=0\n_result=True')
        game('s.demo()\ns.focus_view=False\ns.focused=None\ns.layer(5)\ns.camera_view(35,25,1.6)\ns.emit()\n_result=True')
        wait_preview()
        game('s.set("grid",True)\n_result=True')
        frame('demo_y5')
        game('s.layer(8)\n_result=True')
        frame('demo_y8')
        game('s.set("page","library")\n_result=True')
        time.sleep(.3)
        game('s.set("page","workspace")\n_result=True')
        wait_preview()
        frame('reopened')
        (ui.OUT / 'grid_depth_checks.json').write_text(
            json.dumps({'checks':ui.checks,'pixels':results},indent=2),encoding='utf8')
    finally:
        game('''for key,value in api._grid_depth_saved.items():setattr(s,key,value)
s.camera_revision+=1;s.refresh_preview();s.emit()
_result=True''')
        wait_preview()


if __name__ == '__main__':
    main()
