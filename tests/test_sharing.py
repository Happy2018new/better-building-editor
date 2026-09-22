import base64
import json
import sys
import unittest
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'behavior_pack/HelloScript'))
from projection.model import Document
from projection.sharing_codec import encode_steps,decode_steps,split_text,Inbox,checksum,MAX_RAW
from projection.sharing import Sharing
from projection.session import Session


def encode(doc):return list(encode_steps(doc))[-1]['text']
def decode(text):return list(decode_steps(text))[-1]['document']
def envelope(raw):return 'MP2:'+base64.b64encode(zlib.compress(raw)).decode('ascii')+':'+checksum(raw)


class Bridge:
    def __init__(self):
        self.queue=[];self.clip='';self.pages={};self.index=None;self.succeed=True
    def later(self,delay,callback):self.queue.append(callback)
    def set_clipboard(self,text):self.clip=text;return self.succeed
    def get_clipboard(self):return self.clip
    def save_archive_page(self,identity,page,data):self.pages[(identity,page)]=data;return True
    def load_archive_page(self,identity,page):return self.pages.get((identity,page))
    def save_library(self,data):
        if self.succeed:self.index=data
        return self.succeed
    def settle(self):
        for unused in range(10000):
            if not self.queue:return
            self.queue.pop(0)()
        raise AssertionError('sharing job did not finish')


class SharingTests(unittest.TestCase):
    def test_exact_roundtrip_maximum_dimensions_and_unicode_title(self):
        doc=Document((64,128,64),{(0,0,0):('minecraft:glass',0),(63,127,63):('minecraft:log',5)},name='我的建筑 α')
        restored=decode(encode(doc))
        self.assertEqual(doc.size,restored.size)
        self.assertEqual(doc.name,restored.name)
        self.assertEqual(doc.blocks,restored.blocks)
        self.assertFalse(decode(encode(Document((64,128,64)))).blocks)

    def test_corruption_truncated_zlib_and_trailing_data_are_rejected(self):
        text=encode(Document((1,1,1)))
        fields=text.split(':');packed=base64.b64decode(fields[1])
        for raw in (packed[:-1],packed+b'junk'):
            with self.assertRaises(ValueError):decode('MP2:'+base64.b64encode(raw).decode('ascii')+':'+fields[2])
        for value in (text[:-1]+'g',text.replace('MP2:','MP99:'),'MP2:not-base64:00000000'):
            with self.assertRaises(ValueError):decode(value)

    def test_bounded_decompression_and_invalid_structures(self):
        with self.assertRaises(ValueError):decode(envelope(b' '* (MAX_RAW+1)))
        for packet in ({'seq':0,'kind':'begin','size':[65,128,64]}, {'seq':0,'kind':'begin','size':[1,1,1],'name':'x','paletteCount':65537,'chunkCount':0,'blockCount':0}):
            with self.assertRaises(ValueError):decode(envelope((json.dumps(packet)+'\n').encode('ascii')))
        text=encode(Document((1,1,1)))
        raw=zlib.decompress(base64.b64decode(text.split(':')[1]))
        with self.assertRaises(ValueError):decode(envelope(raw+raw))

    def test_segments_accept_reordering_and_duplicates_but_not_mixed_archives(self):
        text='MP2:'+('abcdefgh'*5000)+':00000000'
        parts=split_text(text);box=Inbox()
        self.assertIsNone(box.add(parts[-1]));self.assertIsNone(box.add(parts[-1]))
        with self.assertRaises(ValueError):box.add(split_text(text+'A')[0])
        result=None
        for part in parts[:-1]:result=box.add(part)
        self.assertEqual(text,result)
        with self.assertRaises(ValueError):Inbox().add(parts[0]+'x')

    def test_short_segments_and_missing_range_tracking_preserve_legacy_import(self):
        text='MP2:'+('abcdefgh'*5000)+':00000000'
        for size in (256,512,1024):
            parts=split_text(text,size);box=Inbox()
            self.assertTrue(all(len(part)<=size+40 for part in parts))
            box.add(parts[1]);box.add(parts[3]);box.add(parts[1])
            self.assertEqual(len(parts)-2,len(box.missing()))
            self.assertTrue(box.missing_summary().startswith('1、3、5–'))
            for part in parts:
                result=box.add(part)
            self.assertEqual(text,result);self.assertFalse(box.missing())
        # Previous releases used 12,000 payload characters per MPS2 segment.
        box=Inbox();total=(len(text)+11999)//12000
        for index in range(total):
            data=text[index*12000:(index+1)*12000]
            result=box.add('MPS2:%s:%d:%d:%s:%s'%(checksum(text.encode('ascii')),index+1,total,checksum(data.encode('ascii')),data))
        self.assertEqual(text,result)

    def test_import_only_commits_new_archive_after_confirmation(self):
        b=Bridge();s=Session(b);share=Sharing(s);original=s.editor
        source=Document((64,128,64),{(63,127,63):('minecraft:stone',0)},name='分享建筑')
        b.clip=encode(source);share.open_import();share.paste();b.settle()
        self.assertFalse(s.library);self.assertIs(original,s.editor)
        self.assertEqual(source.blocks,share.document.blocks)
        share.accept();b.settle()
        self.assertTrue(share.saved);self.assertEqual(1,len(s.library));self.assertIsNone(s.io_job)
        share.accept();b.settle();self.assertEqual(1,len(s.library))
        identity=s.library[0]['id'];share.open_export(identity);b.settle();share.copy()
        self.assertEqual(source.blocks,decode(b.clip).blocks)
        self.assertIs(original,s.editor)

    def test_cancellation_and_failed_save_preserve_draft_and_library(self):
        b=Bridge();s=Session(b);share=Sharing(s);b.clip=encode(Document((2,2,2)))
        share.open_import();share.paste();share.close();b.settle()
        self.assertIsNone(share.document);self.assertFalse(s.library)
        share.open_import();share.paste();b.settle();share.accept();share.close();b.settle()
        self.assertIsNone(s.io_job);self.assertFalse(s.library)
        share.open_import();share.paste();b.settle();b.succeed=False;share.accept();b.settle()
        self.assertTrue(share.error);self.assertFalse(s.library);self.assertIsNone(s.io_job)

    def test_failed_clipboard_read_clears_previous_import_candidate(self):
        b=Bridge();s=Session(b);share=Sharing(s);b.clip=encode(Document((2,2,2)))
        share.open_import();share.paste();b.settle()
        self.assertIsNotNone(share.document)
        b.clip='';share.paste();share.accept();b.settle()
        self.assertTrue(share.error);self.assertIsNone(share.document);self.assertFalse(s.library)


if __name__=='__main__':unittest.main()
