#!/usr/bin/python3

import os
import unittest

import apt_pkg
apt_pkg.config.set("Dir", "./aptroot")
import apt

import unattended_upgrade

apt.apt_pkg.config.set("APT::Architecture", "amd64")


class MockOptions(object):
    debug = False
    verbose = False
    download_only = False
    dry_run = True
    apt_debug = False
    minimal_upgrade_steps = True


class OnBattery(unittest.TestCase):

    def setUp(self):
        self.rootdir = os.path.abspath("./root.on-battery")
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
        unattended_upgrade.LOCK_FILE = "./u-u.lock"
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
