#!/usr/bin/python3

import os
import unittest

import unattended_upgrade
from test.test_base import TestBase, MockOptions


class TestRewindCache(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.mock_allowed_origins("origin=Ubuntu,archive=lucid-security")
        rootdir = self.make_fake_aptroot(os.path.join(self.testdir, "root.rewind"))
        self.cache = unattended_upgrade.UnattendedUpgradesCache(rootdir=rootdir)

    def test_rewind_cache(self):
        """ Test that rewinding the cache works correctly, debian #743594 """
        options = MockOptions()
        options.try_run = True
        to_upgrade = unattended_upgrade.calculate_upgradable_pkgs(self.cache, options)
        self.assertEqual(to_upgrade, [self.cache[p] for p
                                      in ["test-package", "test2-package",
                                          "test3-package"]])
        unattended_upgrade.rewind_cache(self.cache, to_upgrade)
        self.assertEqual(self.cache['test-package'].candidate.version, "2.0")

    def test_rewind_cache_uses_fast_path(self):
        """ rewind uses the cheap mark_install path when it is sufficient """
        options = MockOptions()
        options.try_run = True
        to_upgrade = unattended_upgrade.calculate_upgradable_pkgs(
            self.cache, options)
        # spy on the expensive adjusted path to prove it is not used
        adjusted_calls = []
        orig_mark_install_adjusted = self.cache.mark_install_adjusted

        def spy(pkg, **kwargs):
            adjusted_calls.append(pkg.name)
            return orig_mark_install_adjusted(pkg, **kwargs)
        self.cache.mark_install_adjusted = spy

        unattended_upgrade.rewind_cache(self.cache, to_upgrade)

        self.assertEqual(adjusted_calls, [])
        self.assertEqual(self.cache['test-package'].candidate.version, "2.0")
        self.assertEqual(self.cache.broken_count, 0)
        for pkg in to_upgrade:
            self.assertTrue(pkg.marked_install or pkg.marked_upgrade)

    def test_calculate_upgradable_pkgs_stops_on_signal(self):
        """ a stop signal aborts the package check at the next save point """
        options = MockOptions()
        options.try_run = True
        self.addCleanup(
            setattr, unattended_upgrade, "SIGNAL_STOP_REQUEST", False)
        unattended_upgrade.SIGNAL_STOP_REQUEST = True
        to_upgrade = unattended_upgrade.calculate_upgradable_pkgs(
            self.cache, options)
        self.assertEqual(to_upgrade, [])


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
