#!/usr/bin/python3

import os
import unittest

import apt_pkg
apt_pkg.config.set("Dir", os.path.join(os.path.dirname(__file__), "aptroot"))
import apt

from test.test_base import MockOptions, TestBase

import unattended_upgrade

apt.apt_pkg.config.set("APT::Architecture", "amd64")


class OnBattery(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.rootdir = os.path.join(self.testdir, "root.on-battery")
        # fake on_ac_power
        os.environ["PATH"] = (os.path.join(self.rootdir, "usr", "bin") + ":"
                              + os.environ["PATH"])
        dpkg_status = os.path.abspath(
            os.path.join(self.rootdir, "var", "lib", "dpkg", "status"))
        apt.apt_pkg.config.set("Dir::State::status", dpkg_status)
        apt.apt_pkg.config.clear("DPkg::Pre-Invoke")
        apt.apt_pkg.config.clear("DPkg::Post-Invoke")
        self.log = os.path.join(
            self.rootdir, "var", "log", "unattended-upgrades",
            "unattended-upgrades.log")

    def tearDown(self):
        os.remove(self.log)

    def test_on_battery(self):
        # ensure there is no conffile_prompt check

        # run it
        options = MockOptions()
        unattended_upgrade.DISTRO_DESC = "Ubuntu 10.04"
        ret = unattended_upgrade.main(options, rootdir=self.rootdir)
        self.assertTrue(ret == 1)
        # read the log to see what happend
        with open(self.log) as f:
            needle = "System is on battery power, stopping"
            haystack = f.read()
            self.assertTrue(needle in haystack,
                            "Can not find '%s' in '%s'" % (needle, haystack))


if __name__ == "__main__":
    # do not setup logging in here or the test will break
    unittest.main()
