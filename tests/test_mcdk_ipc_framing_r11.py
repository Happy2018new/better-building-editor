"""Pinned MCDK IPC receive behavior under fragmented TCP data and timeouts."""
import ast
from contextlib import redirect_stdout
import hashlib
from io import StringIO
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / 'tools/data/mcdk_ipc_runtime_v1.6.1.py'
PATCH = ROOT / 'tools/mcdk_patches/ipc-framing-r11.patch'
RELATIVE = Path('mods/INCLUDE_TEST_MOD/DEBUG_ENV_SCRIPT/IPCSystem.py')
ORIGINAL_LF_SHA256 = '09c8fb609d32008784114c3d34a729c4bb83e53ebfa06bf4ae279a35cf3437b9'
FROZEN_LF_SHA256 = 'a9d7d9cac39633701efc9f31d20931681dabf535a9bb053aecc77da36b35fe33'


def load_runtime(source, factory):
    tree = ast.parse(source)
    nodes = [node for node in tree.body if
             isinstance(node, ast.ClassDef) and node.name == 'IPCSystem' or
             isinstance(node, ast.FunctionDef) and node.name in ('U16_BE', 'U32_BE')]
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    namespace = {'socket': SimpleNamespace(socket=factory, AF_INET=socket.AF_INET,
                                          SOCK_STREAM=socket.SOCK_STREAM,
                                          SHUT_RDWR=socket.SHUT_RDWR,
                                          timeout=socket.timeout, error=socket.error),
                 'threading': threading, 'IPC_JSON_REQUEST_TYPE': 100,
                 'traceback': SimpleNamespace(print_exc=lambda: None)}
    exec(compile(module, '<pinned-mcdk-ipc>', 'exec'), namespace)
    return namespace


class FakeSocket:
    def __init__(self, chunks=(), connect_error=None, shutdown_error=None, close_error=None):
        self.chunks = list(chunks)
        self.connect_error = connect_error
        self.shutdown_error = shutdown_error
        self.close_error = close_error
        self.connects = []
        self.timeout = None
        self.closed = 0
        self.shutdowns = 0
        self.read_lengths = []

    def connect(self, endpoint):
        self.connects.append(endpoint)
        if self.connect_error:
            raise self.connect_error

    def settimeout(self, timeout):
        self.timeout = timeout

    def recv(self, length):
        self.read_lengths.append(length)
        if self.closed:
            raise socket.error('socket closed')
        if not self.chunks:
            return b''
        item = self.chunks.pop(0)
        if callable(item):
            item = item()
        if isinstance(item, BaseException):
            raise item
        if len(item) > length:
            self.chunks.insert(0, item[length:])
            item = item[:length]
        return item

    def shutdown(self, how):
        self.shutdowns += 1
        if self.shutdown_error:
            raise self.shutdown_error

    def close(self):
        self.closed += 1
        if self.close_error:
            raise self.close_error


def packet(kind, payload):
    return kind.to_bytes(2, 'big') + len(payload).to_bytes(4, 'big') + payload


class MCDKIpcFramingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frozen = FROZEN.read_bytes().replace(b'\r\n', b'\n')
        if hashlib.sha256(frozen).hexdigest() != FROZEN_LF_SHA256:
            raise AssertionError('Frozen source fingerprint differs')
        # The official blob has no final newline; the tracked Python fixture
        # has one. Restore the pinned EOF convention before checking the patch.
        original = frozen[:-1]
        if hashlib.sha256(original).hexdigest() != ORIGINAL_LF_SHA256:
            raise AssertionError('Frozen official source fingerprint differs')
        cls.original_source = original.decode('utf8')
        # Apply the shipped patch to the exact frozen official source, outside
        # the repository so a clean checkout needs no ignored MCDK tree.
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / RELATIVE
            destination.parent.mkdir(parents=True)
            destination.write_bytes(original)
            for arguments in (['--check'], []):
                result = subprocess.run(['git', 'apply', *arguments, str(PATCH)],
                                        cwd=directory, capture_output=True, text=True)
                if result.returncode:
                    raise AssertionError(result.stderr)
            cls.source = destination.read_text(encoding='utf8')

    def runtime(self, sock):
        namespace = load_runtime(self.source, lambda *args: sock)
        return namespace['IPCSystem'](19133)

    def receive(self, chunks):
        sock = FakeSocket(chunks)
        runtime = self.runtime(sock)
        received = []
        runtime.registerHandler(7, lambda data: received.append(bytes(data)))
        with redirect_stdout(StringIO()):
            runtime._threadListenLoop()
        self.assertIsNone(runtime.sock)
        self.assertEqual(1, sock.closed)
        return received, sock

    def test_original_partial_header_timeout_corrupts_next_header(self):
        tree = ast.parse(self.original_source)
        receiver = next(node for node in ast.walk(tree) if
                        isinstance(node, ast.FunctionDef) and node.name == '_recvAll')
        converters = [node for node in tree.body if
                      isinstance(node, ast.FunctionDef) and node.name in ('U16_BE', 'U32_BE')]
        namespace = {}
        module = ast.fix_missing_locations(ast.Module(body=converters + [receiver], type_ignores=[]))
        exec(compile(module, '<official-mcdk-receive>', 'exec'), namespace)
        header = packet(100, b'0123456789')[:6]
        sock = FakeSocket([header[:2], socket.timeout(), header[2:], b'{"'])
        with self.assertRaises(socket.timeout):
            namespace['_recvAll'](sock, 6)
        damaged = namespace['_recvAll'](sock, 6)
        self.assertEqual(0, namespace['U16_BE'](damaged[:2]))
        self.assertEqual(686882, namespace['U32_BE'](damaged[2:]))

    def test_partial_header_timeout_keeps_the_full_packet(self):
        wire = packet(7, b'payload')
        received, sock = self.receive([wire[:2], socket.timeout(), wire[2:]])
        self.assertEqual([b'payload'], received)
        self.assertEqual(.05, sock.timeout)

    def test_partial_payload_timeouts_keep_every_byte(self):
        wire = packet(7, b'abcdef')
        received, _ = self.receive([wire[:8], socket.timeout(), b'c',
                                    socket.timeout(), b'def'])
        self.assertEqual([b'abcdef'], received)

    def test_json_request_payload_survives_a_partial_receive_timeout(self):
        payload = b'{"id":1,"method":"ping","params":{}}'
        wire = packet(100, payload)
        sock = FakeSocket([wire[:10], socket.timeout(), wire[10:]])
        runtime = self.runtime(sock)
        received = []
        runtime._handleJsonRequest = lambda data: received.append(bytes(data))
        with redirect_stdout(StringIO()):
            runtime._threadListenLoop()
        self.assertEqual([payload], received)
        self.assertEqual(1, sock.closed)

    def test_close_interrupts_a_pending_partial_header(self):
        sock = FakeSocket([b'\x00'])
        runtime = self.runtime(sock)
        def close_during_timeout():
            runtime.close()
            return socket.timeout()
        sock.chunks.append(close_during_timeout)
        with redirect_stdout(StringIO()):
            runtime._threadListenLoop()
        self.assertEqual(1, sock.shutdowns)
        self.assertEqual(2, sock.closed)
        self.assertIsNone(runtime.sock)

    def test_idle_timeouts_then_eof_exit_and_close(self):
        received, _ = self.receive([socket.timeout(), socket.timeout(), socket.timeout(), b''])
        self.assertEqual([], received)

    def test_timeouts_between_complete_packets_keep_order(self):
        received, _ = self.receive([packet(7, b'first'), socket.timeout(),
                                    packet(7, b''), packet(7, b'last')])
        self.assertEqual([b'first', b'', b'last'], received)

    def test_eof_during_partial_payload_does_not_dispatch(self):
        received, _ = self.receive([packet(7, b'abcdef')[:8], b''])
        self.assertEqual([], received)

    def test_socket_error_during_partial_header_exits_and_closes(self):
        received, _ = self.receive([b'\x00', socket.error('receive failure')])
        self.assertEqual([], received)

    def test_connect_failure_closes_socket_and_clears_reference(self):
        sock = FakeSocket(connect_error=socket.error('connect failure'))
        runtime = self.runtime(sock)
        with self.assertRaises(socket.error), redirect_stdout(StringIO()):
            runtime._threadListenLoop()
        self.assertEqual(1, sock.closed)
        self.assertIsNone(runtime.sock)

    def test_shutdown_failure_still_closes_and_clears(self):
        sock = FakeSocket(shutdown_error=socket.error('not connected'))
        runtime = self.runtime(sock)
        runtime.sock = sock
        runtime.close()
        self.assertEqual(1, sock.shutdowns)
        self.assertEqual(1, sock.closed)
        self.assertIsNone(runtime.sock)

    def test_receive_cleanup_does_not_clear_a_replacement_socket(self):
        old, replacement = FakeSocket(), FakeSocket()
        runtime = self.runtime(old)
        def replace():
            runtime.sock = replacement
            return b''
        old.chunks.append(replace)
        with redirect_stdout(StringIO()):
            runtime._threadListenLoop()
        self.assertEqual(1, old.closed)
        self.assertEqual(0, replacement.closed)
        self.assertIs(runtime.sock, replacement)

    def test_close_error_still_clears_the_thread_socket_reference(self):
        sock = FakeSocket(close_error=RuntimeError('close failure'))
        runtime = self.runtime(sock)
        with self.assertRaises(RuntimeError), redirect_stdout(StringIO()):
            runtime._threadListenLoop()
        self.assertEqual(1, sock.closed)
        self.assertIsNone(runtime.sock)


if __name__ == '__main__':
    unittest.main()
