# -*- coding: utf-8 -*-
"""Local clipboard workflow: prepare, inspect and atomically save a new archive."""
from __future__ import unicode_literals
import time
from .model import Document
from .sharing_codec import encode_steps, decode_steps, split_text, Inbox, PART_SIZE, PART_SIZES


class Sharing(object):
    def __init__(self, session):
        self.session = session
        self.opened = False
        self.mode = 'import'
        self.busy = False
        self.message = ''
        self.error = False
        self.progress = (0, 1)
        self.document = None
        self.text = None
        self.parts = []
        self.part = 0
        self.part_size = PART_SIZE
        self.inbox_page = 0
        self.inbox = Inbox()
        self.serial = 0
        self.saved = False
        self.iterator = None
        self.io_owner = None

    def release_io(self):
        if self.io_owner is not None and self.session.io_job is self.io_owner:
            self.session.io_job = None
        self.io_owner = None

    def emit(self):
        self.session.emit('sharing')

    def close(self):
        was_open = self.opened
        self.serial += 1
        if self.iterator is not None:
            self.iterator.close()
        self.iterator = None
        self.release_io()
        self.busy = self.opened = False
        self.emit()
        if was_open:
            self.session.emit('sharing_visibility')

    def fail(self, error):
        self.busy = False
        self.iterator = None
        self.release_io()
        self.error = True
        value = error.args[0] if getattr(error, 'args', None) else '分享操作失败，请重试'
        self.message = value.decode('utf8') if isinstance(value, bytes) else type('')(value)
        self.emit()

    def begin(self, mode):
        if self.session.io_job is not None or self.session.edit_job is not None:
            raise ValueError('请等待当前建筑操作完成')
        self.close()
        self.opened, self.mode = True, mode
        self.message, self.error = '', False
        self.document = self.text = None
        self.parts, self.part, self.saved = [], 0, False
        self.inbox = Inbox()
        self.inbox_page = 0
        self.progress = (0, 1)
        self.emit()
        self.session.emit('sharing_visibility')

    def run(self, iterator, complete, message):
        self.serial += 1
        serial = self.serial
        self.iterator, self.busy, self.message, self.error = iterator, True, message, False
        self.progress = (0, 1)
        self.emit()
        published = [0.]
        def advance():
            if serial != self.serial or not self.opened:
                return
            try:
                deadline = time.time()+.003
                while time.time() < deadline:
                    result = next(iterator)
                    if result is None:
                        continue
                    if 'progress' in result:
                        self.progress = result['progress']
                    else:
                        self.busy, self.iterator = False, None
                        complete(result)
                        self.emit()
                        return
                if time.time()-published[0] >= .1:
                    published[0] = time.time()
                    self.emit()
                self.session.next_frame(advance)
            except (ValueError, TypeError, KeyError, RuntimeError, StopIteration, UnicodeError) as error:
                self.fail(error)
        # Let the shared modal entrance finish before codec/config work begins.
        self.session.bridge.later(.3, advance)

    def open_export(self, identity=None):
        self.begin('export')
        def prepare():
            s = self.session
            if identity is None:
                document = Document(s.editor.document.size, name=s.name.strip() or s.editor.document.name)
                document.blocks = s.editor.document.blocks.copy()
            else:
                entry = next((row for row in s.library if row['id']==identity), None)
                if entry is None:
                    raise ValueError('这份配置已不存在')
                data = dict(entry['data'])
                if data.get('version') == 3:
                    from .archive import load_steps
                    iterator = load_steps(s.bridge, identity, data)
                elif data.get('version') == 2:
                    from .codec import load_steps
                    iterator = load_steps(data)
                else:
                    iterator = iter([Document.from_data(data)])
                document = None
                for step in iterator:
                    if step is not None:
                        document = step
                    yield None
                if document is None:
                    raise ValueError('配置不完整，无法分享')
            self.document = document
            for result in encode_steps(document):
                yield result
        def ready(result):
            self.text = result['text']
            self.parts = split_text(self.text,self.part_size) if len(self.text)>min(PART_SIZES) else []
            self.message = '分享码已准备好，共 %s 字符' % format(len(self.text), ',')
        self.run(prepare(), ready, '正在准备建筑分享码…')

    def open_import(self):
        self.begin('import')
        self.message = '复制收到的分享码，再点击从剪贴板读取。'
        self.emit()

    def copy(self, segmented=False):
        if self.busy or not self.text:
            return
        try:
            text = self.parts[self.part] if segmented and self.parts else self.text
            if not self.session.bridge.set_clipboard(text):
                raise ValueError('复制失败，请检查系统剪贴板权限后重试')
            self.error = False
            self.message = ('已复制第 %d / %d 段' % (self.part+1,len(self.parts))) if segmented else '分享码已复制，可粘贴发送给其他玩家'
            self.emit()
        except (ValueError, RuntimeError, UnicodeError) as error:
            self.fail(error)

    def select_part(self, change):
        self.part = max(0,min(len(self.parts)-1,self.part+change))
        self.emit()

    def set_part_size(self, size):
        if size not in PART_SIZES or self.busy or not self.text:
            return
        self.part_size = size
        self.parts = split_text(self.text,size)
        self.part = 0
        self.message = '每段约 %d 字符，请使用同一种分段长度发送完整建筑' % size
        self.emit()

    def inbox_move(self, change):
        self.inbox_page = max(0,min((self.inbox.total-1)//24,self.inbox_page+change))
        self.emit()

    def first_missing(self):
        missing = self.inbox.missing()
        self.inbox_page = (missing[0]-1)//24 if missing else 0
        self.emit()

    def clear_parts(self):
        self.serial += 1
        self.iterator = None
        self.busy = False
        self.inbox = Inbox()
        self.inbox_page = 0
        self.document = None
        self.saved = False
        self.message, self.error = '已清空，等待新的分享码', False
        self.emit()

    def paste(self):
        if self.busy:
            return
        self.document, self.saved = None, False
        try:
            value = self.session.bridge.get_clipboard()
            if not value:
                raise ValueError('剪贴板没有文字，请先复制建筑分享码')
            text = self.inbox.add(value)
            if text is None:
                self.message = '已接收 %d / %d 段，复制下一段后继续读取' % (len(self.inbox.parts),self.inbox.total)
                self.error = False
                self.emit()
                return
            def ready(result):
                self.document = result['document']
                self.message = '校验通过，确认后作为新配置加入建筑库'
            self.run(decode_steps(text), ready, '正在读取并校验建筑…')
        except (ValueError, TypeError, RuntimeError, UnicodeError) as error:
            self.fail(error)

    def accept(self):
        s, document = self.session, self.document
        if self.busy or self.saved or document is None:
            return
        if s.io_job is not None or s.edit_job is not None:
            self.fail(ValueError('请等待当前建筑操作完成'))
            return
        if len(s.library) >= 32:
            self.fail(ValueError('建筑库已满，请先删除不需要的配置'))
            return
        from .archive import save_steps
        identity = s.library_serial+1
        iterator = save_steps(s.bridge, document, identity)
        s.io_job = iterator
        self.io_owner = iterator
        def write():
            try:
                for index, result in enumerate(iterator):
                    if result is None:
                        yield {'progress': (index+1,index+2)}
                    else:
                        yield {'archive': result}
            finally:
                if s.io_job is iterator:
                    s.io_job = None
        def committed(result):
            entry = {'id': identity, 'data': result['archive'], 'saved': int(time.time())}
            candidate = s.library+[entry]
            try:
                if not s.bridge.save_library({'version':1,'serial':identity,'buildings':candidate}):
                    raise ValueError('建筑库保存失败，原配置保持完整')
                s.library, s.library_serial = candidate, identity
                self.saved = True
                self.message = '已添加到建筑库，当前草稿保持完整'
                s.emit('library')
            finally:
                if s.io_job is iterator:
                    s.io_job = None
        self.run(write(), committed, '正在保存导入的建筑…')
