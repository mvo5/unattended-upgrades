#!/usr/bin/python3

import os
import unittest

import apt_pkg
apt_pkg.config.set("Dir", os.path.join(os.path.dirname(__file__), "aptroot"))
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
        rootdir = os.path.join(self.testdir, "aptroot")
        apt_pkg.config.set("Dir", rootdir)
        apt_pkg.config.set("Dir::Cache", "/tmp")
        self.addCleanup(apt_pkg.config.clear, "Dir::Cache")
        apt_pkg.config.set("Debug::NoLocking", "1")
        apt_pkg.config.set("Debug::pkgDPkgPM", "1")
        apt_pkg.config.set(
            "Dir::State::extended_states",
            os.path.join(self.tempdir, "extended_states"))
        self.addCleanup(apt_pkg.config.clear, "Dir::state::extended_states")
        apt_pkg.config.clear("Dpkg::Post-Invoke")
        apt_pkg.config.clear("Dpkg::Pre-Install-Pkgs")
        self.cache = apt.Cache(rootdir=rootdir)
        # for the log
        apt_pkg.config.set("Unattended-Upgrade::LogDir", self.tempdir)
        self.addCleanup(apt_pkg.config.clear, "Unattended-Upgrade::LogDir")

    def test_upgrade_in_minimal_steps(self):
        self.cache.upgrade(True)
        # upgrade only a tiny subset in the test
        pkgs_to_upgrade = [
            pkg.name for pkg in self.cache.get_changes()][:5]
        unattended_upgrade.PROGRESS_LOG = \
            "./aptroot/var/run/unatteded-upgrades.progress"
        unattended_upgrade.LogInstallProgress = LogInstallProgressMock
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
