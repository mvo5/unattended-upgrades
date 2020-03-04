#!/usr/bin/python3

import apt_pkg
apt_pkg.config.set("Dir", "./aptroot")
import apt
import os
import shutil
import tempfile
import unittest

try:
    from typing import List, Tuple
    List   # pyflaks
    Tuple  # pyflakes
except ImportError:
    pass

import unattended_upgrade


class LogInstallProgressMock(unattended_upgrade.LogInstallProgress):

    # klass data so that we can verify in the test as the actual
    # object is destroyed
    DATA = []  # type: List[Tuple[str, float]]

    # overwrite to log the data
    def status_change(self, pkg, percent, status):
        print(pkg, percent)
        self.DATA.append([pkg, percent])


class TestMinimalPartitions(unittest.TestCase):

    def setUp(self):
        # setup dry-run mode for apt
        apt_pkg.config.set("Dir", "./aptroot")
        apt_pkg.config.set("Dir::Cache", "/tmp")
        apt_pkg.config.set("Debug::NoLocking", "1")
        apt_pkg.config.set("Debug::pkgDPkgPM", "1")
        apt_pkg.config.set("Dir::State::extended_states", "./extended_states")
        apt_pkg.config.clear("Dpkg::Post-Invoke")
        apt_pkg.config.clear("Dpkg::Pre-Install-Pkgs")
        self.cache = apt.Cache()
        # for the log
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.tempdir))
        apt_pkg.config.set("Unattended-Upgrade::LogDir", self.tempdir)

    def tearDown(self):
        if os.path.exists("./extended_states"):
            os.remove("./extended_states")

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
