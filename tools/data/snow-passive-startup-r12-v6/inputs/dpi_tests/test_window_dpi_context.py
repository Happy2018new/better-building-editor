"""Verify physical geometry context entry and exact restoration without OS access."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from diagnose_window_dpi import PER_MONITOR_V2, physical_dpi_context


class FakeDpiApi:
    def __init__(self):
        self.context = 123
        self.calls = []
        self.enter_failed = False
        self.restore_failed = False
        self.wrong_entry = False

    def current(self):
        return self.context

    def set(self, context):
        self.calls.append(context)
        if context == PER_MONITOR_V2 and self.enter_failed:
            return None
        if context == 123 and self.restore_failed:
            return None
        previous = self.context
        self.context = 456 if context == PER_MONITOR_V2 and self.wrong_entry else context
        return previous

    def equal(self, first, second):
        return first == second


class PhysicalDpiContextTests(unittest.TestCase):
    def test_success_restores_exact_original_context(self):
        api = FakeDpiApi()
        with physical_dpi_context(api) as entered:
            self.assertIs(api, entered)
            self.assertEqual(PER_MONITOR_V2, api.context)
        self.assertEqual(123, api.context)
        self.assertEqual([PER_MONITOR_V2, 123], api.calls)

    def test_geometry_failure_still_restores_original_context(self):
        api = FakeDpiApi()
        with self.assertRaisesRegex(OSError, 'GetClientRect failed'):
            with physical_dpi_context(api):
                raise OSError('GetClientRect failed')
        self.assertEqual(123, api.context)
        self.assertEqual([PER_MONITOR_V2, 123], api.calls)

    def test_failed_context_entry_never_reads_geometry(self):
        api = FakeDpiApi()
        api.enter_failed = True
        with self.assertRaisesRegex(RuntimeError, 'Could not enter'):
            with physical_dpi_context(api):
                self.fail('Unverified physical context entered')
        self.assertEqual(123, api.context)

    def test_wrong_context_entry_fails_and_restores(self):
        api = FakeDpiApi()
        api.wrong_entry = True
        with self.assertRaisesRegex(RuntimeError, 'entry did not match'):
            with physical_dpi_context(api):
                self.fail('Wrong DPI context entered')
        self.assertEqual(123, api.context)

    def test_restoration_failure_cannot_return_success(self):
        api = FakeDpiApi()
        api.restore_failed = True
        with self.assertRaisesRegex(RuntimeError, 'Could not restore'):
            with physical_dpi_context(api):
                pass


if __name__ == '__main__':
    unittest.main()
