#!/usr/bin/python3

import os
import unittest

import apt

import unattended_upgrade
from test.test_base import TestBase, MockOptions


class TestWhitelist(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.mock_allowed_origins("origin=Ubuntu,archive=lucid-security")

    def make_cache(self):
        rootdir = self.make_fake_aptroot(
            os.path.join(self.testdir, "root.rewind"))
        return unattended_upgrade.UnattendedUpgradesCache(rootdir=rootdir)

    def mock_whitelist(self, *pkgnames):
        for pkgname in pkgnames:
            apt.apt_pkg.config.set(
                "Unattended-Upgrade::Package-Whitelist::", pkgname)
        self.addCleanup(
            apt.apt_pkg.config.clear, "Unattended-Upgrade::Package-Whitelist")

    def test_empty_whitelist_upgrades_all_pkgs(self):
        """ without a whitelist every upgradable package is picked """
        to_upgrade = unattended_upgrade.calculate_upgradable_pkgs(
            self.make_cache(), MockOptions())
        self.assertEqual(
            [pkg.name for pkg in to_upgrade],
            ["test-package", "test2-package", "test3-package"])

    def test_whitelist_limits_upgrades_to_listed_pkgs(self):
        """ a non-strict whitelist keeps back the packages not listed """
        self.mock_whitelist("test2-package")
        to_upgrade = unattended_upgrade.calculate_upgradable_pkgs(
            self.make_cache(), MockOptions())
        self.assertEqual([pkg.name for pkg in to_upgrade], ["test2-package"])


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
