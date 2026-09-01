#!/usr/bin/python3

import os
import unittest

import unattended_upgrade
from test.test_base import MockOptions, TestBase


class TestDriverDeferral(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.mock_allowed_origins(
            "origin=Ubuntu,archive=lucid-security")
        rootdir = self.make_fake_aptroot(
            os.path.join(self.testdir, "root.driver-deferral"))
        self.cache = unattended_upgrade.UnattendedUpgradesCache(
            rootdir=rootdir)

    def test_deferred_dependency_defers_entire_root_transaction(self):
        root = self.cache["ordinary-root"]
        root.mark_upgrade(from_user=True)

        self.assertEqual(
            {pkg.name for pkg in self.cache.get_changes()},
            {"ordinary-root", "driver-dependency"})
        self.assertEqual(
            unattended_upgrade.sanity_problem(self.cache, root),
            "pkg driver-dependency is marked for deferred installation and "
            "is not safe to upgrade unattended")
        self.assertFalse(
            unattended_upgrade.check_changes_for_sanity(self.cache, root))

        self.cache.clear()
        to_upgrade = unattended_upgrade.calculate_upgradable_pkgs(
            self.cache, MockOptions())

        self.assertEqual(
            [pkg.name for pkg in to_upgrade], ["unrelated-safe"])


if __name__ == "__main__":
    unittest.main()
