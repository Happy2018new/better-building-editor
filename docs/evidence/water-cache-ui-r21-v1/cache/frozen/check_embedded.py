"""Exercise the prepared instrumentation with fake owners, without IPC."""
import json
import sys
from types import SimpleNamespace
from types import ModuleType

from offline_compare import LiquidControlsTests, baseline_class
from embedded_ab import WaterDepthAB
from projection import liquid_viewport, liquid_render, liquid_transport


def fixture_and_engine():
    fixture = LiquidControlsTests(methodName='runTest')
    fixture.setUp()
    fixture.settle()
    for control in fixture.dolls:
        control.GetGlobalPosition = lambda control=control: control.position
        control.GetSize = lambda control=control: control.size
    session = SimpleNamespace(liquid_controls=fixture.controls, camera_pose=(35., 25., 4.6),
                              camera_pan=(0., 0.), camera_depth_pose=0.)
    class UnboundMethod:
        def __init__(self, function):
            self.im_func = function
        def __call__(self, *args):
            raise AssertionError('Python 2 unbound baseline method must be unwrapped')
    engine = WaterDepthAB(session, liquid_viewport, liquid_render, liquid_transport,
                          UnboundMethod(baseline_class().update))
    return fixture, engine


def drive(fixture, engine, name, mode='candidate', ticks=60, warmup=5, start=1.):
    engine.begin(name, mode, ticks, warmup)
    for tick in range(ticks + warmup):
        fixture.update(start + tick * .04)
    phase = engine.state()
    assert phase['done'] and len(phase['rows']) == ticks
    return json.loads(json.dumps(phase))


def total(phase, field):
    return sum(row[field] for row in phase['rows'])


def main():
    fixture, engine = fixture_and_engine()
    phases = {}
    try:
        engine.install()
        phases['baseline'] = drive(fixture, engine, 'baseline', 'baseline')
        phases['candidate'] = drive(fixture, engine, 'candidate')
        assert total(phases['baseline'], 'source_validations') == 60
        assert total(phases['candidate'], 'source_validations') == 0
        assert phases['baseline']['after'] == phases['candidate']['after']
        for field in ('view_callbacks', 'pose_callbacks', 'renderer_validations', 'publication_restores'):
            assert total(phases['baseline'], field) == total(phases['candidate'], field) == 60
        fixture.view = fixture.view._replace(distance=-3.)
        phases['depth'] = drive(fixture, engine, 'depth')
        assert sum(row['source_validations'] for row in phases['depth']['warmup_rows']) == 1
        assert phases['depth']['after']['entries'][0]['uniforms'] != phases['candidate']['after']['entries'][0]['uniforms']
        phases['clip'] = drive(fixture, engine, 'clip', 'clip', 1, 0)
        assert phases['clip']['rows'][0]['cached_entries'] == 0
        assert not any(phases['clip']['after']['entries'][0]['visible'])
        phases['unclip'] = drive(fixture, engine, 'unclip')
        assert not phases['unclip']['after']['pending']
        phases['invalid'] = drive(fixture, engine, 'invalid', 'invalid', 1, 0)
        assert phases['invalid']['rows'][0]['source_validations'] == 1
        assert phases['invalid']['rows'][0]['cached_entries'] == 0
        assert 'signed16 depth range' in phases['invalid']['after']['error']
        assert phases['invalid']['before']['entries'] == phases['invalid']['after']['entries']
        fixture.controls.retry()
        phases['retry'] = drive(fixture, engine, 'retry')
        assert not phases['retry']['after']['pending'] and phases['retry']['after']['error'] is None
        assert sum(row['source_validations'] for row in phases['retry']['warmup_rows']) == 1
    finally:
        restored = engine.uninstall()
        assert restored['restored']
    fixture, engine = fixture_and_engine()
    try:
        engine.install()
        engine.begin('injected-abort')
        raise RuntimeError('Injected host abort before phase collection')
    except RuntimeError as error:
        assert str(error).startswith('Injected host abort')
    finally:
        assert engine.uninstall()['restored']
    import host
    import projection
    fixture, unused_engine = fixture_and_engine()
    namespace = {'sys': sys, 's': unused_engine.session}
    aliases = {'modern_projection': ModuleType('modern_projection'),
               'modern_projection.projection': projection}
    aliases.update({'modern_projection.' + name: value for name, value in list(sys.modules.items())
                    if name.startswith('projection.')})
    assert not any(name in sys.modules for name in aliases)
    sys.modules.update(aliases)
    try:
        eval(compile(host.install_code(), 'prepared-runtime-install', 'exec'), namespace)
        assert namespace['_result']['installed']
        assert sys._water_depth_ab.uninstall()['restored']
    finally:
        if hasattr(sys, '_water_depth_ab'):
            sys._water_depth_ab.uninstall()
            del sys._water_depth_ab
        for name in aliases:
            del sys.modules[name]
    print(json.dumps({'offline_only': True, 'runtime_action': False,
                      'phases': list(phases), 'baseline_source_validations': 60,
                      'candidate_source_validations': 0, 'restored': True,
                      'injected_abort_restored': True, 'python2_unbound_method_path': True,
                      'exact_install_snippet_checked': True, 'passed': True}))


if __name__ == '__main__':
    main()
