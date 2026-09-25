#!/usr/bin/python3

import os
import unittest
from unittest.mock import patch

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


class TestUpgradeFilter(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.mock_allowed_origins("origin=Ubuntu,archive=lucid-security")
        self.rootdir = self.make_fake_aptroot(
            os.path.join(self.testdir, "root.driver-deferral"),
            fake_pkgs=[("driver-root", "1.0", {}),
                       ("ordinary-dependency", "1.0", {})])
        os.makedirs(os.path.join(self.rootdir, "var/run"), exist_ok=True)

    def test_filter_selects_roots_and_resolves_dependencies(self):
        filters = unattended_upgrade.UpgradeFilter
        for mode, roots, changes in (
                (filters.NO_DRIVERS,
                 {"ordinary-dependency", "unrelated-safe"},
                 {"ordinary-dependency", "unrelated-safe"}),
                (filters.DRIVERS_ONLY,
                 {"driver-root", "ordinary-root"},
                 {"driver-root", "ordinary-dependency", "ordinary-root",
                  "driver-dependency"}),
                (filters.ALL_UPGRADES,
                 {"driver-root", "ordinary-root", "ordinary-dependency",
                  "unrelated-safe"},
                 {"driver-root", "ordinary-root", "ordinary-dependency",
                  "driver-dependency", "unrelated-safe"})):
            with self.subTest(mode=mode):
                cache = unattended_upgrade.UnattendedUpgradesCache(
                    self.rootdir, upgrade_filter=mode)
                selected = unattended_upgrade.calculate_upgradable_pkgs(
                    cache, MockOptions())
                self.assertEqual({pkg.name for pkg in selected}, roots)
                unattended_upgrade.mark_pkgs_to_upgrade(
                    cache, [pkg.name for pkg in selected])
                self.assertEqual(
                    {pkg.name for pkg in cache.get_changes()}, changes)
                self.assertIsNone(
                    unattended_upgrade.sanity_problem(cache, None))

    def test_driver_modes_still_reject_blacklisted_dependencies(self):
        filters = unattended_upgrade.UpgradeFilter
        for mode in (filters.DRIVERS_ONLY, filters.ALL_UPGRADES):
            with self.subTest(mode=mode):
                cache = unattended_upgrade.UnattendedUpgradesCache(
                    self.rootdir, upgrade_filter=mode)
                cache["driver-root"].mark_upgrade()
                cache.blacklist = ["ordinary-dependency$"]
                self.assertEqual(
                    unattended_upgrade.sanity_problem(cache, None),
                    "pkg ordinary-dependency is blacklisted or is not "
                    "whitelisted")

    def test_no_drivers_commit_guard_checks_resolved_changes(self):
        cache = unattended_upgrade.UnattendedUpgradesCache(self.rootdir)
        cache["ordinary-root"].mark_upgrade()
        with patch.object(cache, "commit") as commit:
            success, error = unattended_upgrade.cache_commit(cache, "", False)
        self.assertFalse(success)
        self.assertIsInstance(error, RuntimeError)
        commit.assert_not_called()
        self.assertEqual(cache.get_changes(), [])

    def test_driver_modes_reach_commit_in_both_install_paths(self):
        filters = unattended_upgrade.UpgradeFilter
        for mode in (filters.DRIVERS_ONLY, filters.ALL_UPGRADES):
            for minimal in (False, True):
                with self.subTest(mode=mode, minimal=minimal):
                    cache = unattended_upgrade.UnattendedUpgradesCache(
                        self.rootdir, upgrade_filter=mode)
                    committed = []

                    def record_commit(**kwargs):
                        committed.append(
                            {pkg.name for pkg in cache.get_changes()})
                        return True

                    # Resolve real APT changes, but do not invoke dpkg.
                    with patch.object(cache, "commit",
                                      side_effect=record_commit):
                        if minimal:
                            success = (
                                unattended_upgrade.upgrade_in_minimal_steps(
                                    cache, ["driver-root"]))
                        else:
                            unattended_upgrade.mark_pkgs_to_upgrade(
                                cache, ["driver-root"])
                            success = unattended_upgrade.upgrade_normal(
                                cache, "", False)
                    self.assertTrue(success)
                    self.assertEqual(
                        committed, [{"driver-root", "ordinary-dependency"}])
                    # Both install paths reopen the cache after committing.
                    self.assertEqual(cache.upgrade_filter, mode)


if __name__ == "__main__":
    unittest.main()
