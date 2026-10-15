"""Dense native frames for glint motion; sparse screenshots can alias motion."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def validate(session, executable, expected_sha256):
    project = Path(session['project'])
    script = project/'tools/capture_native_burst.py'
    root=Path(__file__).resolve().parents[1]
    files=('tools/capture_native_burst.py',)+tuple('.agents/skills/pyreact-debugging/scripts/'+name
                                                 for name in ('_session.py','_window.py'))
    for name in files:
        target=project/name
        if not target.is_file() or target.read_bytes()!=(root/name).read_bytes():
            raise ValueError('Install the reviewed burst helper dependency first: '+name)
    if hashlib.sha256(Path(executable).read_bytes()).hexdigest()!=expected_sha256.lower():
        raise ValueError('Native burst executable differs from its reviewed hash')
    return script


def capture(session, output, executable, expected_sha256, duration_ms=8000):
    script=validate(session,executable,expected_sha256)
    turnstile = os.environ.get('MCDEV_BURST_TURNSTILE')
    if turnstile:
        directory = Path(turnstile).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        ready = directory / (output.name + '.ready.json')
        release = directory / (output.name + '.allow')
        if ready.exists() or release.exists():
            raise ValueError('Choose a fresh dense-capture coordination directory')
        ready.write_text(json.dumps({'owner': session['owner'], 'id': session['id'],
            'game_pid': session['game_pid'], 'game_identity': session['game_identity'],
            'output': str(output), 'duration_ms': duration_ms}, indent=2) + '\n', encoding='ascii')
        print(json.dumps({'dense_capture_waiting': str(ready)}), flush=True)
        deadline = time.monotonic() + 180.
        while not release.is_file():
            if time.monotonic() >= deadline:
                raise TimeoutError('Dense-capture coordination window was not released')
            time.sleep(.1)
    # This diagnostic compares motion at actual QPC intervals and grants no
    # animation qualification. Permit a bounded quarter-second background
    # stall; the measured cadence remains part of the report, not interpolated.
    result = subprocess.run([
        sys.executable, '-X', 'utf8', str(script), '--session', session['session_file'],
        '--owner', session['owner'], '--output', str(output), '--executable', str(executable),
        '--expected-sha256', expected_sha256, '--duration-ms', str(duration_ms),
        '--max-frames', '1800', '--max-gap-ms', '250'], capture_output=True, text=True,
        encoding='utf8', timeout=120)
    receipt_path = output.with_name(output.name+'.capture.json')
    if result.returncode or not receipt_path.is_file():
        raise RuntimeError('Native item animation capture failed: '+result.stdout[-2000:]+result.stderr[-2000:])
    raw = receipt_path.read_bytes()
    receipt = json.loads(raw)
    if not receipt.get('capture_valid') or not receipt.get('temporal_complete'):
        raise ValueError('Native item animation timeline is incomplete: '+str(receipt_path))
    return {'receipt': str(receipt_path), 'sha256': hashlib.sha256(raw).hexdigest(),
            'timeline': receipt['validated_timeline'], 'request': receipt['request']}
