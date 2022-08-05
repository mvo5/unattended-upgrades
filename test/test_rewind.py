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


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
