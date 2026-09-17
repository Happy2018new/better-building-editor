"""Small stdio MCP client; keeps the installed knowledge tools usable in this task."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('tool', nargs='?', default='list')
    parser.add_argument('arguments', nargs='?', default='{}')
    args = parser.parse_args()
    binary = ROOT / '.tools/mcdk-runtime/mcdk-asst-lite.exe'
    process = subprocess.Popen([str(binary), '--stdio'], cwd=binary.parent,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL)

    def send(message):
        process.stdin.write((json.dumps(message) + '\n').encode('utf8'))
        process.stdin.flush()

    def receive(identity):
        while True:
            line = process.stdout.readline()
            if not line:
                raise RuntimeError('MCDK exited before replying')
            try:
                result = json.loads(line)
            except ValueError:
                continue
            if result.get('id') == identity:
                return result

    try:
        send({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
            'protocolVersion': '2024-11-05', 'capabilities': {},
            'clientInfo': {'name': 'modern-projection-dev', 'version': '1.0'}}})
        receive(1)
        send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        method = 'tools/list' if args.tool == 'list' else 'tools/call'
        params = {} if args.tool == 'list' else {
            'name': args.tool, 'arguments': json.loads(args.arguments)}
        send({'jsonrpc': '2.0', 'id': 2, 'method': method, 'params': params})
        result = receive(2)
        sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False, indent=2).encode('utf8'))
    finally:
        process.terminate()
        process.wait(timeout=10)


if __name__ == '__main__':
    main()
