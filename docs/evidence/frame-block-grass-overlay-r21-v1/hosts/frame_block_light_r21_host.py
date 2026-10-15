"""Run one scheduled short holdout phase from its frozen project tools."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT / 'tools'), str(PROJECT / '.agents/skills/pyreact-debugging/scripts')]
import run_visible_items_r16 as runner
from item_sprite_capture_contract import snapshot_digest, snapshot_sources
from _session import load_session

READBACK = '''import mod.server.extraServerApi as api
import json
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
rules=factory.CreateGame(level).GetGameRulesInfoServer()['cheat_info']
_result=json.dumps({'time':factory.CreateTime(level).GetTime(),
 'raining':factory.CreateWeather(level).IsRaining(),
 'thunder':factory.CreateWeather(level).IsThunder(),
 'daylight_cycle':rules['daylight_cycle'],'weather_cycle':rules['weather_cycle']})
'''


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='ascii')


def run(args):
    plan = json.loads((args.control / 'plan.json').read_bytes())
    assert PROJECT.resolve() == Path(plan['project']).resolve()
    assert snapshot_digest(snapshot_sources(PROJECT)) == plan['source_sha256']
    session = load_session(args.session, plan['owner'], live=True)
    assert Path(session['project']).resolve() == PROJECT.resolve()
    phase = next(row for row in plan['phases'] if row['id'] == args.phase)
    output = Path(phase['capture_output'])
    assert not output.exists(), 'Retain prior capture evidence'
    batch = args.control / phase['matrix']
    assert hashlib.sha256(batch.read_bytes()).hexdigest() == phase['matrix_sha256']
    clock = phase['time_of_day']
    assert runner.ENV_SETUP.count('+6000') == 1
    runner.ENV_SETUP = runner.ENV_SETUP.replace('+6000', '+' + str(clock))
    environment_call, process_call = runner.environment, runner.process_snapshot
    environment_evidence = {'schema': 1, 'expected_time_of_day': clock,
        'phase': args.phase, 'setup_readback_passed': None, 'production_qualified': False}
    environment_valid = None
    started = time.monotonic()

    def environment(client, code):
        nonlocal environment_valid
        value = environment_call(client, code)
        if code == runner.ENV_SETUP:
            try:
                readback = environment_call(client, READBACK)
                environment_valid = (readback['time'] % 24000 == clock
                    and not any(readback[key] for key in ('raining', 'thunder', 'daylight_cycle', 'weather_cycle')))
                environment_evidence.update(saved_prior_state=value, setup_readback=readback,
                    setup_readback_passed=environment_valid)
            except Exception as error:
                environment_valid = False
                environment_evidence.update(setup_readback_passed=False,
                    readback_error=type(error).__name__ + ': ' + str(error))
            save(args.control / (args.phase + '-environment.json'), environment_evidence)
        elif code == runner.ENV_RESTORE:
            environment_evidence['restored_by_original_environment_helper'] = value
            save(args.control / (args.phase + '-environment.json'), environment_evidence)
        return value

    def process_snapshot(pid):
        if time.monotonic() - started >= plan['phase_policy']['capture_admission_seconds']:
            raise RuntimeError('Short-batch cooperative capture deadline reached; restore now')
        if environment_valid is False:
            raise RuntimeError('Independent environment setup readback failed; restore now')
        return process_call(pid)

    runner.environment, runner.process_snapshot = environment, process_snapshot
    options = argparse.Namespace(session=args.session, owner=plan['owner'], output=output,
        wgc=args.wgc, skip_closeup=True, production_profile=False, compact_closeup=False,
        closeup_only=False, burst_exe=None, burst_sha256=None, orientation_matrix=True,
        icons_only=True, orientation_cases=None, candidate_geometry=args.control / 'candidate.json',
        frame_block_item='minecraft:stone', frame_block_aux=0, frame_block_enchanted=False,
        frame_block_batch=batch, near_distance=3., view_angle=0., editor_zoom=5.,
        native_target_plain=True, native_target=None, maximum_handles=200000,
        minimum_commit_gib=6., names='diamond_sword')
    os.environ.update(MCDEV_SESSION_FILE=str(args.session), MCDEV_OWNER=plan['owner'],
        MCDEV_MCP_URL=session['mcp_url'], MCDEV_ALLOW_USER_FOREGROUND='1')
    result = runner.run(options)
    report = json.loads((output / 'report.json').read_bytes())
    elapsed = time.monotonic() - started
    outcome = {'schema': 1, 'phase': args.phase, 'completed': bool(report['completed']),
        'matrix_completed': bool(report.get('matrix_completed')), 'elapsed_seconds': elapsed,
        'within_180_seconds': elapsed <= 180., 'source_unchanged': report['source_unchanged'],
        'cleanup_errors': report['cleanup_errors'], 'environment': environment_evidence,
        'native_references_restored': all(row.get('native_reference', {}).get('restored')
            for row in report['cases']), 'production_qualified': False, 'appearance_accepted': False,
        'host_wrapper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'report_sha256': hashlib.sha256((output / 'report.json').read_bytes()).hexdigest()}
    outcome['phase_ready_for_review'] = (result == 0 and outcome['matrix_completed']
        and outcome['within_180_seconds'] and outcome['source_unchanged']
        and outcome['native_references_restored'] and environment_valid is True
        and not outcome['cleanup_errors'])
    save(args.control / (args.phase + '-outcome.json'), outcome)
    print(json.dumps(outcome))
    return 0 if outcome['phase_ready_for_review'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--phase', required=True)
    parser.add_argument('--wgc', type=Path, required=True)
    raise SystemExit(run(parser.parse_args()))
