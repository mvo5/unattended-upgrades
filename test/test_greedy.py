#!/usr/bin/python3

import itertools
import os
import unittest
from unittest.mock import patch

import apt

from test.test_base import TestBase, MockOptions
import unattended_upgrade

apt.apt_pkg.config.set("APT::Architecture", "amd64")


class TestGreedyMinimalSteps(TestBase):
    """The greedy minimal steps mode checks the upgrade candidates step
       by step in do_install() instead of up front, it must still report
       the ones that can not be upgraded like the non-greedy mode
    """

    def setUp(self):
        TestBase.setUp(self)
        self.rootdir = self.make_fake_aptroot(
            template=os.path.join(self.testdir, "root.unused-deps"),
            fake_pkgs=[
                ("test-package", "1.0",
                 {"Depends": ["test-package-dependency"]}),
                ("test-package-dependency", "1.0", {}),
            ]
        )
        # fake on_ac_power
        os.environ["PATH"] = (os.path.join(self.rootdir, "usr", "bin") + ":"
                              + os.environ["PATH"])
        self.apt_conf = os.path.join(self.rootdir, "etc", "apt", "apt.conf")
        with open(self.apt_conf, "w") as fp:
            fp.write("""
Unattended-Upgrade::Allowed-Origins {
    "Ubuntu:lucid-security";
};
Unattended-Upgrade::Skip-Updates-On-Metered-Connections "false";
""")
        self.log = os.path.join(
            self.rootdir, "var", "log", "unattended-upgrades",
            "unattended-upgrades.log")
        os.makedirs(os.path.dirname(self.log), exist_ok=True)
        with open(self.log, "w"):
            pass
        self.kept_back = os.path.join(
            self.rootdir, unattended_upgrade.KEPT_PACKAGES_FILE)
        os.makedirs(os.path.dirname(self.kept_back), exist_ok=True)
        with open(self.kept_back, "w"):
            pass

    def hold_test_package(self):
        status = os.path.join(self.rootdir, "var", "lib", "dpkg", "status")
        with open(status) as fp:
            content = fp.read()
        content = content.replace(
            "Package: test-package\nStatus: install ok installed",
            "Package: test-package\nStatus: hold ok installed")
        with open(status, "w") as fp:
            fp.write(content)

    def install_on_shutdown(self):
        # main() resets the Unattended-Upgrade config tree from the rootdir
        with open(self.apt_conf, "a") as fp:
            fp.write('Unattended-Upgrade::InstallOnShutdown "true";\n')

    def run_greedy(self):
        options = MockOptions()
        options.minimal_upgrade_steps = True
        unattended_upgrade.main(options, rootdir=self.rootdir)
        with open(self.log) as fp:
            return fp.read()

    def read_kept_back(self):
        with open(self.kept_back) as fp:
            return fp.read()

    def test_greedy_upgrade(self):
        log = self.run_greedy()
        self.assertIn("Packages that may be upgraded: test-package", log)
        self.assertIn("Packages that were upgraded: test-package", log)
        self.assertIn("All upgrades installed", log)

    def test_greedy_nothing_upgradable(self):
        # a candidate that turns out to be kept back must not be reported
        # as upgraded, the result is the same as in the non-greedy mode
        self.hold_test_package()
        log = self.run_greedy()
        self.assertNotIn("Packages that will be upgraded: test-package", log)
        self.assertNotIn("All upgrades installed", log)
        self.assertIn("No packages found that can be upgraded unattended "
                      "and no pending auto-removals", log)
        self.assertIn("Package test-package is marked to be held back.", log)
        self.assertIn("test-package", self.read_kept_back())

    def test_greedy_interrupted(self):
        # a run that is stopped (signal, battery, metered connection) before
        # all the steps are done must not report the packages not reached
        # yet as kept back: the kept-back list and the stamp are left alone
        stamp = os.path.join(self.rootdir, "var", "lib", "apt", "periodic",
                             "unattended-upgrades-stamp")
        stamp_mtime = os.path.getmtime(stamp)
        stop = itertools.chain([False], itertools.repeat(True))
        with patch.object(unattended_upgrade, "should_stop",
                          side_effect=lambda: next(stop)):
            log = self.run_greedy()
        self.assertIn("Packages that may be upgraded: test-package", log)
        self.assertNotIn("Packages that were upgraded", log)
        self.assertIn("Upgrade was interrupted", log)
        self.assertNotIn("Package test-package is kept back", log)
        self.assertEqual(self.read_kept_back(), "")
        self.assertEqual(os.path.getmtime(stamp), stamp_mtime)

    def test_greedy_install_on_shutdown(self):
        # the archives are downloaded now and installed on shutdown, there
        # is nothing to be greedy about
        self.install_on_shutdown()
        log = self.run_greedy()
        self.assertNotIn("Packages that were upgraded", log)
        self.assertNotIn("All upgrades installed", log)
        self.assertIn("Configured to install on shutdown, so exiting now", log)
        # the archives were downloaded and checked before exiting
        self.assertIn("check_conffile_prompt(", log)
        self.assertIn("test-package_2.0_all.deb", log)

    def test_greedy_install_on_shutdown_nothing_upgradable(self):
        self.install_on_shutdown()
        self.hold_test_package()
        log = self.run_greedy()
        self.assertIn("No packages found that can be upgraded unattended "
                      "and no pending auto-removals", log)
        self.assertIn("test-package", self.read_kept_back())


if __name__ == "__main__":
    # do not setup logging in here or the test will break
    unittest.main()
