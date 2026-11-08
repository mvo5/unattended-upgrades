#!/usr/bin/python3

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import apt

import unattended_upgrade
from test.test_base import TestBase

apt.apt_pkg.config.set("APT::Architecture", "amd64")


class LogInstallProgressMock(unattended_upgrade.LogInstallProgress):

    # klass data so that we can verify in the test as the actual
    # object is destroyed
    DATA: list[tuple[str, float]] = []

    # record the progress of each step, apt reports the progress of
    # the dpkg run in between with a status
    def status_change(self, pkg, percent, status):
        if not status:
            self.DATA.append((pkg, percent))
        super().status_change(pkg, percent, status)


class TestMinimalPartitions(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        # two independent upgrades in lucid-security, so that they are
        # installed in two steps
        self.rootdir = self.make_fake_aptroot(
            template=os.path.join(self.testdir, "root.unused-deps"),
            fake_pkgs=[
                ("test-package", "1.0", {}),
                ("test-package-dependency", "0.5", {}),
            ]
        )
        self.apt_conf = os.path.join(self.rootdir, "etc", "apt", "apt.conf")
        self.set_archive([("test-package", "2.0", ""),
                          ("test-package-dependency", "1.0", "")])
        # fake on_ac_power
        patcher = patch.dict(os.environ, {
            "PATH": os.path.join(self.rootdir, "usr", "bin") + ":"
            + os.environ["PATH"]})
        patcher.start()
        self.addCleanup(patcher.stop)
        unattended_upgrade._setup_alternative_rootdir(self.rootdir)
        self.cache = unattended_upgrade.UnattendedUpgradesCache(
            rootdir=self.rootdir)
        # cache.commit() releases and retakes the apt lock, it has to be
        # held like in main() (Debug::NoLocking only counts)
        apt.apt_pkg.pkgsystem_lock()
        self.addCleanup(apt.apt_pkg.pkgsystem_unlock)
        # mock LogInstallProgress
        patcher = patch.object(unattended_upgrade, "LogInstallProgress",
                               LogInstallProgressMock)
        patcher.start()
        self.addCleanup(patcher.stop)
        LogInstallProgressMock.DATA = []

    def test_upgrade_in_minimal_steps(self):
        pkgs_to_upgrade = ["test-package", "test-package-dependency"]
        logfile_dpkg = os.path.join(self.tempdir, "dpkg.log")
        (success, pkgs_upgraded,
         conffile_prompt) = unattended_upgrade.upgrade_in_minimal_steps(
            self.cache, pkgs_to_upgrade, logfile_dpkg)
        self.assertTrue(success)
        self.assertEqual(sorted(pkgs_upgraded), pkgs_to_upgrade)
        self.assertFalse(conffile_prompt)
        # one step per package, the progress counts upwards
        self.assertEqual(
            sorted(pkg for pkg, percent in LogInstallProgressMock.DATA),
            pkgs_to_upgrade)
        self.assertEqual(
            [percent for pkg, percent in LogInstallProgressMock.DATA],
            [0.0, 50.0])
        with open(os.path.join(self.rootdir, "var", "run",
                               "unattended-upgrades.progress")) as fp:
            self.assertIn("Progress: 50.0 %", fp.read())
        # one dpkg run per step
        with open(logfile_dpkg) as fp:
            self.assertEqual(fp.read().count("Log started: "), 2)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
