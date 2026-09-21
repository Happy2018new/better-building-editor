"""Embedded-codec/clipboard feasibility check, preserving existing clipboard formats."""
import ctypes as c
from ctypes import wintypes as w
import json
import sys
from pathlib import Path
import verify_ui as ui
from verify_projection_outline import game


class ClipboardBackup:
    def __init__(self):
        self.rows=[]
        self.user=c.windll.user32
        self.kernel=c.windll.kernel32
        self.gdi=c.windll.gdi32
        for fn,result,args in (
            (self.user.CreateWindowExW,w.HWND,[w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,c.c_int,c.c_int,c.c_int,c.c_int,w.HWND,w.HMENU,w.HINSTANCE,c.c_void_p]),
            (self.user.DestroyWindow,w.BOOL,[w.HWND]),
            (self.user.OpenClipboard,w.BOOL,[w.HWND]),
            (self.user.GetClipboardData,w.HANDLE,[w.UINT]),
            (self.user.SetClipboardData,w.HANDLE,[w.UINT,w.HANDLE]),
            (self.user.EnumClipboardFormats,w.UINT,[w.UINT]),
            (self.user.CopyImage,w.HANDLE,[w.HANDLE,w.UINT,c.c_int,c.c_int,w.UINT]),
            (self.kernel.GlobalSize,c.c_size_t,[w.HANDLE]),
            (self.kernel.GlobalLock,c.c_void_p,[w.HANDLE]),
            (self.kernel.GlobalUnlock,w.BOOL,[w.HANDLE]),
            (self.kernel.GlobalAlloc,w.HANDLE,[w.UINT,c.c_size_t]),
            (self.kernel.GlobalFree,w.HANDLE,[w.HANDLE]),
            (self.gdi.DeleteObject,w.BOOL,[w.HANDLE])):
            fn.restype,fn.argtypes=result,args
        # EmptyClipboard must have an owner for subsequent SetClipboardData.
        # This native STATIC window is hidden throughout the assessment.
        self.hwnd=self.user.CreateWindowExW(0,'STATIC','Projection clipboard assessment',0,0,0,0,0,None,None,None,None)

    def save(self):
        if not self.hwnd or not self.user.OpenClipboard(self.hwnd):return False
        try:
            kind=0
            while True:
                kind=self.user.EnumClipboardFormats(kind)
                if not kind:break
                handle=self.user.GetClipboardData(kind)
                if not handle:return False
                if kind==2:
                    clone=self.user.CopyImage(handle,0,0,0,0)
                    if not clone:return False
                    self.rows.append((kind,clone,True))
                else:
                    size=self.kernel.GlobalSize(handle)
                    if not 0<size<=32*1024*1024:return False
                    ptr=self.kernel.GlobalLock(handle)
                    if not ptr:return False
                    try:data=c.string_at(ptr,size)
                    finally:self.kernel.GlobalUnlock(handle)
                    self.rows.append((kind,data,False))
            return True
        finally:self.user.CloseClipboard()

    def restore(self):
        assert self.user.OpenClipboard(self.hwnd),'Could not reopen clipboard for restoration'
        try:
            assert self.user.EmptyClipboard()
            for kind,value,bitmap in self.rows:
                handle=value if bitmap else self.kernel.GlobalAlloc(2,len(value))
                assert handle
                if not bitmap:
                    ptr=self.kernel.GlobalLock(handle)
                    assert ptr
                    c.memmove(ptr,value,len(value))
                    self.kernel.GlobalUnlock(handle)
                if not self.user.SetClipboardData(kind,handle):
                    if not bitmap:self.kernel.GlobalFree(handle)
                    raise AssertionError('Clipboard restoration failed for format %d'%kind)
            self.rows=[]
        finally:self.user.CloseClipboard()

    def discard(self):
        for unused,value,bitmap in self.rows:
            if bitmap:self.gdi.DeleteObject(value)
        self.rows=[]
        if self.hwnd:self.user.DestroyWindow(self.hwnd)
        self.hwnd=None


def main():
    source=(Path(__file__).parent/'assess_clipboard_sharing.py').read_text(encoding='utf8').split("if __name__=='__main__':")[0]
    game('import types,sys,time\napi._share_assessment=types.ModuleType("share_assessment".encode("ascii"))\nexec(compile('+repr(source)+',"share_assessment","exec"),api._share_assessment.__dict__)\n_result=True')
    backup=ClipboardBackup()
    can_restore=backup.save()
    if not can_restore:backup.discard()
    results=[]
    try:
        for kind in ('empty','solid','shell','building','random16','random256','random65535'):
            row=game('api._share_sample=api._share_assessment.measure('+repr(kind)+',True)\n_result=api._share_sample[0]')
            if can_restore:
                clip=game('''comp=s.bridge.factory.CreateGame(s.bridge.level)
text=api._share_sample[1].encode('ascii')
started=time.time()
success=comp.SetClipboardContent(text)
received=comp.GetClipboardContent()
_result={"ok":success,"exact":received==text,"characters":len(received) if received is not None else None,"roundtrip_ms":round((time.time()-started)*1000,2)}''')
                row['clipboard']=clip
                assert clip['ok'] and clip['exact'],row
            results.append(row)
            print(json.dumps(row,ensure_ascii=False),flush=True)
    finally:
        if can_restore:
            backup.restore()
            backup.discard()
        result={'runtime':game('_result=sys.version'),'clipboard_tested':can_restore,'cases':results}
        (ui.OUT/'stage50_share_runtime.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        game('del api._share_assessment\nif hasattr(api,"_share_sample"):del api._share_sample\n_result=True')


if __name__=='__main__':main()
