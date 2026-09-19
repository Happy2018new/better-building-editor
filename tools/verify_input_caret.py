"""Native input/placeholder checks and diagnostic caret strip; no world writes."""
import sys
import time
import json
import mss
import numpy as np
from PIL import Image
import verify_ui as ui
import capture_screen as capture


def caret_contrast(frames):
    # Ignore the initial hover transition. Detect blinking pixels, rather than
    # treating every pale background column as a visible white caret.
    samples = np.array([np.array(frame) for frame in frames[3:]])
    changed = np.ptp(samples.astype('int16'), axis=0).max(axis=2) >= 6
    changed[:8] = False; changed[-8:] = False
    changed[:,:18] = False; changed[:,-8:] = False
    column = int(changed.sum(axis=0).argmax())
    rows = np.where(changed[:,column])[0]
    if len(rows) < frames[0].height * .25:
        return {'detected':False, 'readable':False}
    colors = samples[:,int(rows[len(rows)//2]),column].astype(float)/255.
    linear = np.where(colors<=.04045, colors/12.92, ((colors+.055)/1.055)**2.4)
    luminance = linear @ np.array([.2126,.7152,.0722])
    contrast = float((luminance.max()+.05)/(luminance.min()+.05))
    return {'detected':True, 'column':column, 'height':len(rows),
            'colors':(colors*255).astype(int).tolist(), 'contrast':contrast,
            'readable':contrast>=3.}


def main():
    name=sys.argv[1] if len(sys.argv)>1 and not sys.argv[1].startswith('--') else 'input_caret'
    capture.user32.SetProcessDPIAware()
    ui.click('建筑库')
    field=ui.nodes('Input',ui.nodes('Library')[0])[0]
    original=field['props']['value']
    long_text='--long' in sys.argv
    sample='Cursor 123' if '--ascii' in sys.argv else '光标 Cursor 123'
    if long_text:
        sample=(sample+' / ')*30
    try:
        inspect_field(field,name,long_text,sample)
    finally:
        ui.call('set_input',field['id'],original)


def inspect_field(field,name,long_text,sample):
    ui.call('set_input',field['id'],sample)
    native=ui.call('native_control',field['id'])['result']
    root=ui.nodes('SafeArea')[0]['children'][0]['layout']
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    left,top,width,height=capture._window_rect(window['hwnd'])
    scale=width/root['width']
    x,y=native['global'];w,h=native['size']
    capture.user32.SetCursorPos(int(left+(x+20)*scale),int(top+(y+h/2)*scale))
    time.sleep(.08)
    capture.user32.mouse_event(2,0,0,0,0);time.sleep(.08)
    capture.user32.mouse_event(4,0,0,0,0)
    time.sleep(.15)
    capture.user32.keybd_event(35,0,0,0);time.sleep(.06)
    capture.user32.keybd_event(35,0,2,0)
    capture.user32.keybd_event(49,0,0,0);time.sleep(.06)
    capture.user32.keybd_event(49,0,2,0)
    time.sleep(.5)
    capture.user32.SetCursorPos(int(left+width-5),int(top+height-5))
    frames=[]
    with mss.MSS() as screen:
        for unused in range(12):
            raw=screen.grab(dict(left=left,top=top,width=width,height=height))
            frame=Image.frombytes('RGB',raw.size,raw.bgra,'raw','BGRX')
            frames.append(frame.crop((int(x*scale),int(y*scale),int((x+(w if long_text else min(w,260)))*scale),int((y+h)*scale))))
            time.sleep(.09)
    strip=Image.new('RGB',(frames[0].width,frames[0].height*len(frames)))
    for i,frame in enumerate(frames):strip.paste(frame,(0,i*frame.height))
    path=ui.OUT/(name+'.png');strip.save(path);print(path)
    focused=ui.call('native_control',field['id'])['result']
    ui.check('native placeholder child remains present',focused['placeholderPresent'])
    others=[n for n in ui.nodes('Input',ui.nodes('Library')[0]) if n['id']!=field['id']]
    ui.check('all input templates retain native placeholder children',all(ui.call('native_control',n['id'])['result']['placeholderPresent'] for n in others))
    ui.check('focused field retains pale background',all(frame.getpixel((frame.width-20,frame.height//2))[0]>200 for frame in frames))
    contrast=caret_contrast(frames)
    ui.check('native keyboard editing remains active',focused['text'].endswith('1'))
    (ui.OUT/(name+'.json')).write_text(json.dumps({'checks':ui.checks,'caret':contrast},ensure_ascii=False,indent=2),encoding='utf8')
    print('CARET '+json.dumps(contrast),flush=True)
    if '--require-visible' in sys.argv:
        ui.check('native caret has at least 3:1 contrast',contrast['readable'])


if __name__=='__main__':main()
