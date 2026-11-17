#!/usr/bin/python3

import datetime
import hashlib
import os
import shutil
import subprocess
import unittest
from unittest.mock import Mock, patch

import apt_pkg
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

                    # Resolve real APT changes, but do not invoke dpkg; the
                    # minimal steps download each step before committing it.
                    with patch.object(cache, "commit",
                                      side_effect=record_commit), \
                            patch("unattended_upgrade.fetch_archives",
                                  return_value=Mock(items=[])):
                        if minimal:
                            success, _, _ = (
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


class TestDriverFlow(TestBase):
    """Exercise real resolution, acquisition and commit, replacing only dpkg."""

    def setUp(self):
        super().setUp()
        apt_pkg.config.clear("Unattended-Upgrade::Package-Blacklist")
        self.addCleanup(apt_pkg.config.clear, "Unattended-Upgrade::Package-Blacklist")
        apt_pkg.config.set("Debug::pkgDPkgPM", "false")
        self.mock_allowed_origins("origin=Ubuntu,archive=lucid-security")
        self.rootdir = self.make_fake_aptroot(
            os.path.join(self.testdir, "root.driver-deferral"),
            fake_pkgs=[("driver-root", "1.0", {}),
                       ("ordinary-dependency", "1.0", {})])
        self.archives = os.path.join(self.rootdir, "var/cache/apt/archives")
        os.makedirs(os.path.join(self.archives, "partial"), exist_ok=True)
        os.makedirs(os.path.join(self.rootdir, "var/run"), exist_ok=True)
        os.makedirs(os.path.join(self.rootdir, "var/lib/dpkg/updates"), exist_ok=True)
        self.marker = os.path.join(
            self.rootdir, unattended_upgrade.APPLY_ON_SHUTDOWN_FILE.lstrip("/"))
        self.repo = os.path.join(self.tempdir, "repo")
        os.makedirs(self.repo)
        lists = os.path.join(self.rootdir, "var/lib/apt/lists")
        old_prefix = "archive.ubuntu.com_ubuntu_dists_lucid-security_"
        uri = "copy:" + self.repo + "/dists/lucid-security/"
        prefix = apt_pkg.uri_to_filename(uri)
        index = os.path.join(lists, old_prefix + "main_binary-amd64_Packages")
        with open(index) as f:
            sections = f.read().strip().split("\n\n")
        records = [self.build_package(section) for section in sections]
        with open(index, "w") as f:
            f.write("\n".join(records))
        for suffix in ("Release", "Release.gpg", "main_binary-amd64_Packages"):
            os.rename(os.path.join(lists, old_prefix + suffix),
                      os.path.join(lists, prefix + suffix))
        self.index = os.path.join(lists, prefix + "main_binary-amd64_Packages")
        with open(os.path.join(self.rootdir, "etc/apt/sources.list"), "w") as f:
            f.write("deb [trusted=yes] copy:%s lucid-security main\n" % self.repo)
        self.installed = []
        self.modes = []
        for target, kwargs in (
                ("unattended_upgrade.should_stop", {"return_value": False}),
                ("unattended_upgrade.is_update_day", {"return_value": True}),
                ("apt.Cache.install_archives",
                 {"autospec": True, "side_effect": self.install_archives})):
            patcher = patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)
        for key in ("Remove-Unused-Kernel-Packages", "Remove-Unused-Dependencies",
                    "Remove-New-Unused-Dependencies", "InstallOnShutdown",
                    "Keep-Debs-After-Install"):
            apt_pkg.config.set("Unattended-Upgrade::" + key, "false")

    def build_package(self, section):
        record = apt_pkg.TagSection(section + "\n")
        control_dir = os.path.join(self.tempdir, record["Package"], "DEBIAN")
        os.makedirs(control_dir, exist_ok=True)
        with open(os.path.join(control_dir, "control"), "w") as f:
            f.write(section + "\nDescription: driver deferral test\n"
                    "Maintainer: Test <test@example.org>\n")
        deb = os.path.join(self.repo, record["Filename"])
        subprocess.check_call(
            ["dpkg-deb", "--root-owner-group", "--build",
             os.path.dirname(control_dir), deb],
            stdout=subprocess.DEVNULL)
        with open(deb, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        return section + "\nSize: %s\nSHA256: %s\n" % (
            os.path.getsize(deb), digest)

    def install_archives(self, cache, pm, progress):
        changes = cache.get_changes()
        self.installed.extend(pkg.name for pkg in changes)
        self.modes.append(cache.upgrade_filter)
        if not apt_pkg.config.find_b("Debug::pkgDPkgPM", False):
            # Model dpkg's status update so cache.open() sees installed versions.
            # Replace the file atomically: APT still maps the old records.
            status = apt_pkg.config.find_file("Dir::State::status")
            next_mtime = int(os.stat(status).st_mtime) + 1
            with open(status + ".new", "w") as f:
                for pkg in cache:
                    version = pkg.candidate if pkg in changes else pkg.installed
                    if version:
                        f.write("Package: %s\nStatus: install ok installed\n"
                                "Architecture: %s\nVersion: %s\n" %
                                (pkg.shortname, version.architecture, version.version))
                        if version.record.get("Depends"):
                            f.write("Depends: %s\n" % version.record["Depends"])
                        f.write("\n")
            # Ensure APT notices same-size status updates within one second.
            os.utime(status + ".new", (next_mtime, next_mtime))
            os.replace(status + ".new", status)
        return pm.RESULT_COMPLETED

    def run_upgrade(self, shutdown=False, **kwargs):
        options = MockOptions()
        options.debug = False
        for key, value in kwargs.items():
            setattr(options, key, value)
        env = dict(os.environ)
        env.pop("UNATTENDED_UPGRADES_FORCE_INSTALL_ON_SHUTDOWN", None)
        if shutdown:
            env["UNATTENDED_UPGRADES_FORCE_INSTALL_ON_SHUTDOWN"] = "1"
        with patch.dict(os.environ, env, clear=True):
            return unattended_upgrade.run(
                options, self.rootdir, None,
                os.path.join(self.tempdir, "dpkg.log"), datetime.datetime.now())

    def cached_packages(self):
        return {unattended_upgrade.pkgname_from_deb(
            os.path.join(self.archives, filename))
            for filename in os.listdir(self.archives)
            if filename.endswith(".deb")}

    def test_mixed_run_and_cached_shutdown(self):
        self.assertTrue(self.run_upgrade().success)
        self.assertEqual(set(self.installed),
                         {"ordinary-dependency", "unrelated-safe"})
        self.assertEqual(set(self.modes),
                         {unattended_upgrade.UpgradeFilter.NO_DRIVERS})
        self.assertTrue(os.path.isfile(self.marker))
        self.assertEqual(self.cached_packages(), {
            "driver-root", "driver-dependency", "ordinary-root",
            "ordinary-dependency"})
        self.installed.clear()
        self.modes.clear()
        # There is no repository to fall back to at shutdown.
        shutil.rmtree(self.repo)
        self.assertTrue(self.run_upgrade(shutdown=True).success)
        self.assertEqual(set(self.installed),
                         {"driver-root", "driver-dependency", "ordinary-root"})
        self.assertEqual(set(self.modes),
                         {unattended_upgrade.UpgradeFilter.DRIVERS_ONLY})
        self.assertFalse(os.path.exists(self.marker))

    def test_driver_only_early_return(self):
        apt_pkg.config.set("Unattended-Upgrade::Package-Blacklist::",
                           "unrelated-safe$")
        apt_pkg.config.set("Unattended-Upgrade::Package-Blacklist::",
                           "driver-root$")
        apt_pkg.config.set("Unattended-Upgrade::Package-Blacklist::",
                           "ordinary-dependency$")
        self.assertTrue(self.run_upgrade().success)
        self.assertEqual(self.installed, [])
        self.assertEqual(self.cached_packages(),
                         {"ordinary-root", "driver-dependency"})
        self.assertTrue(os.path.exists(self.marker))

    def test_install_on_shutdown_preserves_all_upgrades(self):
        apt_pkg.config.set("Unattended-Upgrade::InstallOnShutdown", "true")
        self.assertTrue(self.run_upgrade().success)
        self.assertEqual(self.installed, [])
        self.assertEqual(len(self.cached_packages()), 5)
        self.assertTrue(os.path.exists(self.marker))
        self.assertTrue(self.run_upgrade(
            shutdown=True, minimal_upgrade_steps=False).success)
        self.assertEqual(len(self.installed), 5)
        self.assertEqual(self.modes,
                         [unattended_upgrade.UpgradeFilter.ALL_UPGRADES])
        self.assertFalse(os.path.exists(self.marker))
        self.assertEqual(self.cached_packages(), set())

    def test_pending_work_survives_incomplete_shutdown(self):
        self.assertTrue(self.run_upgrade(download_only=True).success)
        # A successful return alone does not mean all selected work was applied
        # (minimal steps can skip transactions that fail the final sanity check).
        with patch("unattended_upgrade.do_install",
                   return_value=(True, [], False)):
            self.assertTrue(self.run_upgrade(shutdown=True).success)
        self.assertTrue(os.path.exists(self.marker))
        self.assertEqual(len(self.cached_packages()), 5)

    def test_failure_preserves_marker_and_archives(self):
        # A failed install and an interrupted shutdown must both keep the
        # pending marker and the retained archives, installing nothing.
        with self.subTest(case="failed install"):
            with patch("apt.Cache.install_archives", side_effect=SystemError):
                self.assertFalse(self.run_upgrade().success)
            self.assertTrue(os.path.exists(self.marker))
            # minimal steps stop at the failed step, later steps are not
            # downloaded, but the deferred work is kept for the shutdown
            self.assertLessEqual({
                "driver-root", "driver-dependency", "ordinary-root",
                "ordinary-dependency"}, self.cached_packages())

        with self.subTest(case="interrupted shutdown"):
            self.assertTrue(self.run_upgrade().success)
            cached = self.cached_packages()
            self.installed.clear()
            with patch("unattended_upgrade.should_stop", return_value=True):
                self.assertFalse(self.run_upgrade(shutdown=True).success)
            self.assertTrue(os.path.exists(self.marker))
            self.assertEqual(self.cached_packages(), cached)
            self.assertEqual(self.installed, [])

    def test_conffile_blacklist_survives_filter_switch(self):
        with patch("unattended_upgrade.dpkg_conffile_prompt", return_value=True), \
                patch("unattended_upgrade.conffile_prompt", side_effect=lambda p:
                      unattended_upgrade.pkgname_from_deb(p) == "driver-dependency"):
            self.assertFalse(self.run_upgrade().success)
        self.assertEqual(set(self.installed),
                         {"ordinary-dependency", "unrelated-safe"})
        self.assertEqual(self.cached_packages(),
                         {"driver-root", "ordinary-dependency"})
        self.assertTrue(os.path.exists(self.marker))

    def test_stale_marker_is_cleared_after_completed_check(self):
        unattended_upgrade.update_apply_on_shutdown_marker(self.rootdir, True)
        apt_pkg.config.set("Unattended-Upgrade::Package-Blacklist::", ".*")
        self.assertTrue(self.run_upgrade(shutdown=True).success)
        self.assertFalse(os.path.exists(self.marker))
        self.assertEqual(self.installed, [])

    def test_keep_debs_option(self):
        apt_pkg.config.set("Unattended-Upgrade::Keep-Debs-After-Install", "true")
        self.assertTrue(self.run_upgrade().success)
        self.assertEqual(len(self.cached_packages()), 5)

    def test_download_only_and_dry_run_leave_marker_unchanged(self):
        # download-only prepares archives but never schedules or installs...
        self.assertTrue(self.run_upgrade(download_only=True).success)
        self.assertEqual(len(self.cached_packages()), 5)
        self.assertEqual(self.installed, [])
        self.assertFalse(os.path.exists(self.marker))

        # ...and dry-run never changes an existing marker either way.
        for exists in (False, True):
            with self.subTest(exists=exists):
                unattended_upgrade.update_apply_on_shutdown_marker(
                    self.rootdir, exists)
                self.assertTrue(self.run_upgrade(dry_run=True).success)
                self.assertEqual(os.path.exists(self.marker), exists)

    def test_incomplete_download_does_not_schedule(self):
        os.unlink(os.path.join(self.repo, "driver-root_2.0_all.deb"))
        self.assertFalse(self.run_upgrade().success)
        self.assertEqual(self.installed, [])
        self.assertFalse(os.path.exists(self.marker))

    def test_cached_commit_rejects_missing_and_corrupt_archives(self):
        self.assertTrue(self.run_upgrade(download_only=True).success)
        unattended_upgrade.update_apply_on_shutdown_marker(self.rootdir, True)
        archive = os.path.join(self.archives, "driver-root_2.0_all.deb")
        source = os.path.join(self.repo, "driver-root_2.0_all.deb")
        for minimal in (False, True):
            for damage in ("missing", "same-size corruption"):
                with self.subTest(minimal=minimal, damage=damage):
                    shutil.copyfile(source, archive)
                    if damage == "missing":
                        os.unlink(archive)
                    else:
                        with open(archive, "r+b") as f:
                            f.write(b"corrupt!")
                    self.assertFalse(self.run_upgrade(shutdown=True).success)
                    self.assertEqual(self.installed, [])
                    cache = unattended_upgrade.UnattendedUpgradesCache(
                        self.rootdir, unattended_upgrade.UpgradeFilter.DRIVERS_ONLY)
                    cache.cache_only = True
                    # Exercise commit's own acquisition, not just run's preflight.
                    options = MockOptions()
                    options.minimal_upgrade_steps = minimal
                    success, _, _ = unattended_upgrade.do_install(
                        cache, ["driver-root"], options,
                        os.path.join(self.tempdir, "dpkg.log"))
                    self.assertFalse(success)
                    self.assertEqual(self.installed, [])
                    self.assertTrue(os.path.exists(self.marker))
                    # The available repository must not have repaired the file.
                    if damage == "missing":
                        self.assertFalse(os.path.exists(archive))
                    else:
                        with open(archive, "rb") as f:
                            self.assertEqual(f.read(8), b"corrupt!")


if __name__ == "__main__":
    unittest.main()
