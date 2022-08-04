#!/usr/bin/python3

import os
import unittest

import apt_pkg

import apt

try:
    from typing import List, Tuple
    List   # pyflaks
    Tuple  # pyflakes
except ImportError:
    pass

import unattended_upgrade
from test.test_base import TestBase


class LogInstallProgressMock(unattended_upgrade.LogInstallProgress):

    # klass data so that we can verify in the test as the actual
    # object is destroyed
    DATA = []  # type: List[Tuple[str, float]]

    # overwrite to log the data
    def status_change(self, pkg, percent, status):
        print(pkg, percent)
        self.DATA.append([pkg, percent])


class TestMinimalPartitions(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        # setup dry-run mode for apt
        apt_pkg.config.set("Debug::NoLocking", "1")
        # apt_pkg.config.set("Debug::pkgDPkgPM", "1")
        apt_pkg.config.set(
            "Dir::State::extended_states",
            os.path.join(self.tempdir, "extended_states"))
        self.addCleanup(apt_pkg.config.clear, "Dir::state::extended_states")
        apt_pkg.config.clear("Dpkg::Post-Invoke")
        apt_pkg.config.clear("Dpkg::Pre-Install-Pkgs")
        rootdir = os.path.join(self.testdir, "aptroot")
        self.cache = apt.Cache(rootdir=rootdir)
        # mock LogDir config
        self.u_u_logdir = apt_pkg.config.get("Unattended-Upgrade::LogDir")
        apt_pkg.config.set("Unattended-Upgrade::LogDir", self.tempdir)
        # mock PROGRESS_LOG
        self.progress_log = unattended_upgrade.PROGRESS_LOG
        unattended_upgrade.PROGRESS_LOG = os.path.join(
            self.tempdir, "var/run/unatteded-upgrades.progress")
        # mock LogInstallProgress
        self.log_install_progress = unattended_upgrade.LogInstallProgress
        unattended_upgrade.LogInstallProgress = LogInstallProgressMock

    def tearDown(self):
        # restore mocks
        unattended_upgrade.PROGRESS_LOG = self.progress_log
        apt_pkg.config.set("Unattended-Upgrade::LogDir", self.u_u_logdir)
        unattended_upgrade.LogInstallProgress = self.log_install_progress

    def test_upgrade_in_minimal_steps(self):
        self.cache.upgrade(True)
        # upgrade only a tiny subset in the test
        pkgs_to_upgrade = [
            pkg.name for pkg in self.cache.get_changes()][:5]
        unattended_upgrade.upgrade_in_minimal_steps(
            self.cache, pkgs_to_upgrade, "",
            os.path.join(self.tempdir, "mylog"))
        # ensure we count upwarts
        last_percent = -1
        for (pkg, percent) in LogInstallProgressMock.DATA:
            self.assertTrue(last_percent < percent)
            last_percent = percent
        # cleanup class data
        LogInstallProgressMock.DATA = []


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
