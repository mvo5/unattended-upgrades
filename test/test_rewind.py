#!/usr/bin/python3

import os
import unittest

import apt_pkg
apt_pkg.config.set("Dir", os.path.join(os.path.dirname(__file__), "./aptroot"))
import apt

import unattended_upgrade
from test.test_base import TestBase, MockOptions

apt.apt_pkg.config.set("APT::Architecture", "amd64")


class TestRewindCache(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        rootdir = os.path.join(self.testdir, "root.rewind")
        dpkg_status = os.path.abspath(
            os.path.join(rootdir, "var", "lib", "dpkg", "status"))
        apt.apt_pkg.config.set("Dir::State::status", dpkg_status)
        apt.apt_pkg.config.set(
            "Unattended-Upgrade::Allow-APT-Mark-Fallback", "true")
        self.cache = unattended_upgrade.UnattendedUpgradesCache(
            rootdir=rootdir)

    def test_rewind_cache(self):
        """ Test that rewinding the cache works correctly, debian #743594 """
        options = MockOptions()
        options.try_run = True
        to_upgrade = unattended_upgrade.calculate_upgradable_pkgs(
            self.cache, options)
        self.assertEqual(to_upgrade, [self.cache[p] for p
                                      in ["test-package", "test2-package",
                                          "test3-package"]])
        unattended_upgrade.rewind_cache(self.cache, to_upgrade)
        self.assertEqual(self.cache['test-package'].candidate.version, "2.0")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
