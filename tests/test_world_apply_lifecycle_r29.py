"""Lifecycle checks using the real server request, tick and world writer.

The established fixture mocks SDK calls; these checks do not qualify native
Minecraft placement or visuals. Start-only authorization remains unchanged.
"""
from contextlib import contextmanager
import unittest
from unittest.mock import patch

import test_server_stream as fixture
from modern_projection.projection import world


@contextmanager
def server_case():
    case = fixture.ServerStreamTests()
    case.setUp()
    try:
        yield case
    finally:
        case.doCleanups()


def upload(case, one_cell_batches=True):
    case.send(doc=fixture.Document(
        (4, 1, 1), {(x, 0, 0): ('minecraft:stone', 0) for x in range(4)}))
    job = case.host.jobs['player'][2]
    if one_cell_batches:
        original_step = job.step
        job.step = lambda: original_step(budget=1)
    return job


def finals(case):
    return [data for unused_player, unused_request, data in case.replies
            if data.get('done')]


class WorldApplyLifecycleTests(unittest.TestCase):
    def assert_stopped(self, case, job, progress, reply=True):
        self.assertTrue(job.done)
        self.assertTrue(job.cancelled)
        self.assertFalse(case.host.jobs)
        self.assertFalse(case.host.uploads)
        responses = finals(case)
        self.assertEqual(int(reply), len(responses))
        if reply:
            self.assertEqual(progress, responses[0]['progress'])
        checks, writes = case.allowed_checks, list(case.writes)
        for unused in range(3):
            case.host.tick()
        self.assertEqual(checks, case.allowed_checks)
        self.assertEqual(writes, case.writes)
        self.assertEqual(responses, finals(case))

    def test_dimension_or_missing_leave_event_stops_the_next_batch(self):
        for change in ('dimension', 'absent_without_leave_event'):
            for written in (0, 1):
                with self.subTest(change=change, written=written), server_case() as case:
                    job = upload(case)
                    if written:
                        case.host.tick()
                    self.assertEqual(written, job.written)
                    player_list = lambda: ['real_player', 'player']
                    if change == 'dimension':
                        case.dimension = 1
                    else:
                        player_list = lambda: ['real_player']
                    with patch.object(fixture.server.serverApi, 'GetPlayerList', player_list):
                        case.host.tick()
                        self.assertEqual(written, len(case.writes))
                        self.assertTrue(all(row[1] == 0 for row in case.palette_writes))
                        self.assertIn('玩家已离开或维度已改变', job.error)
                        self.assert_stopped(case, job, {
                            'total': 4, 'processed': written, 'written': written, 'failed': 0},
                            reply=change == 'dimension')
                    self.assertEqual(1, case.allowed_checks)

    def test_dimension_sdk_errors_are_readable_and_prevent_the_next_write(self):
        reason = '原生维度查询失败'
        for error_type in (ValueError, TypeError, KeyError, RuntimeError):
            for written in (0, 1):
                with self.subTest(error=error_type.__name__, written=written), server_case() as case:
                    job = upload(case)
                    if written:
                        case.host.tick()
                    with patch.object(case.factory, 'CreateDimension',
                                      side_effect=error_type(reason.encode('utf8'))):
                        case.host.tick()
                    self.assertEqual(written, len(case.writes))
                    self.assertIn('世界写入状态检查失败：' + reason, job.error)
                    self.assertEqual(1, case.allowed_checks)
                    self.assert_stopped(case, job, {
                        'total': 4, 'processed': written, 'written': written, 'failed': 0})

    def test_presence_sdk_errors_are_readable_and_release_the_cancelled_job(self):
        reason = '原生在线玩家查询失败'
        for error_type in (ValueError, TypeError, KeyError, RuntimeError):
            for written in (0, 1):
                with self.subTest(error=error_type.__name__, written=written), server_case() as case:
                    job = upload(case)
                    if written:
                        case.host.tick()
                    with patch.object(fixture.server.serverApi, 'GetPlayerList',
                                      side_effect=error_type(reason.encode('utf8'))) as presence:
                        case.host.tick()
                    self.assertEqual(1, presence.call_count)
                    self.assertEqual(written, len(case.writes))
                    self.assertIn('世界写入状态检查失败：' + reason, job.error)
                    self.assertEqual(1, case.allowed_checks)
                    self.assert_stopped(case, job, {
                        'total': 4, 'processed': written, 'written': written, 'failed': 0})

    def test_dimension_change_retains_first_cell_error_and_stops_later_cells(self):
        with server_case() as case:
            job = upload(case)
            reason = '第一格原生写入失败'
            with patch.object(job.adapter, 'write', side_effect=RuntimeError(reason.encode('utf8'))):
                case.host.tick()
            self.assertEqual((1, 0, 1), (job.cursor, job.written, job.failed))
            case.dimension = 1
            case.host.tick()
            self.assertEqual([], case.writes)
            self.assertIn('首处失败 (0, 64, 0)：' + reason, job.error)
            self.assertEqual(1, case.allowed_checks)
            self.assert_stopped(case, job, {
                'total': 4, 'processed': 1, 'written': 0, 'failed': 1})

    def test_multi_cell_step_finishes_without_any_extra_permission_query(self):
        with server_case() as case:
            job = upload(case, one_cell_batches=False)
            self.assertEqual(1, case.allowed_checks)
            # Make the existing six-millisecond budget deterministic for four cells.
            with patch.object(world.time, 'time', return_value=0), \
                    patch.object(fixture.server.serverApi, 'GetPlayerList',
                                 wraps=fixture.server.serverApi.GetPlayerList) as presence, \
                    patch.object(case.factory, 'CreateDimension',
                                 wraps=case.factory.CreateDimension) as dimension:
                case.host.tick()
            self.assertEqual(1, presence.call_count)
            self.assertEqual(1, dimension.call_count)
            self.assertEqual(4, job.written)
            self.assertEqual(1, case.allowed_checks)
            self.assertEqual(4, len(case.palette_writes))
            self.assertFalse(job.cancelled)
            self.assertFalse(case.host.jobs)
            self.assertEqual(1, len(finals(case)))
            self.assertNotIn('error', finals(case)[0])

    def test_explicit_cancel_and_leave_event_keep_prefix_and_do_not_finish_twice(self):
        for change in ('cancel', 'leave_event'):
            with self.subTest(change=change), server_case() as case:
                job = upload(case)
                case.host.tick()
                if change == 'cancel':
                    case.host.request({'__id__': 'player', 'request': 1, 'action': 'cancel'})
                else:
                    case.host.leave({'id': 'player'})
                self.assert_stopped(case, job, {
                    'total': 4, 'processed': 1, 'written': 1, 'failed': 0},
                    reply=change == 'cancel')
                self.assertEqual(1, case.allowed_checks)
                self.assertEqual([(0, 64, 0)], case.writes)

    def test_read_and_resolve_remain_available_without_write_permission_queries(self):
        with server_case() as case:
            case.creative = False
            case.abilities['build'] = False
            case.send(action='check')
            case.finish()
            self.assertNotIn('error', finals(case)[-1])
            case.host.request({'__id__': 'player', 'request': 2, 'action': 'resolve',
                               'palette': [['minecraft:stone', 0]]})
            case.finish()
            self.assertEqual([['minecraft:stone', 0]], finals(case)[-1]['palette'])
            self.assertEqual(0, case.allowed_checks)
            self.assertEqual([], case.writes)

    def test_write_step_exception_is_not_caught_as_a_lifecycle_error(self):
        with server_case() as case:
            job = upload(case)
            error = RuntimeError('unexpected step failure')
            with patch.object(job, 'step', side_effect=error):
                with self.assertRaises(RuntimeError) as caught:
                    case.host.tick()
            self.assertIs(error, caught.exception)
            self.assertFalse(job.cancelled)
            self.assertFalse(finals(case))


if __name__ == '__main__':
    unittest.main()
