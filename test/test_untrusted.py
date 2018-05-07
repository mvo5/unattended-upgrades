#!/usr/bin/python3

import os
import unittest

import apt_pkg
apt_pkg.config.set("Dir", "./aptroot")
import apt

import unattended_upgrade

apt.apt_pkg.config.set("APT::Architecture", "amd64")


class MockOptions(object):
    debug = True
    verbose = False
    download_only = False
    dry_run = True
    apt_debug = False
    minimal_upgrade_steps = True


class TestUntrusted(unittest.TestCase):

    def setUp(self):
        self.rootdir = os.path.abspath("./root.untrusted")
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

    def test_untrusted_check_without_conffile_check(self):
        # ensure there is no conffile_prompt check
        apt.apt_pkg.config.set("DPkg::Options::", "--force-confold")

        # run it
        options = MockOptions()
        unattended_upgrade.LOCK_FILE = "./u-u.lock"
        unattended_upgrade.main(options, rootdir=self.rootdir)
        # read the log to see what happend
        with open(self.log) as f:
            needle = "DEBUG InstCount=0 DelCount=0 BrokenCount=0"
            haystack = f.read()
            self.assertTrue(needle in haystack,
                            "Can not find '%s' in '%s'" % (needle, haystack))
            self.assertTrue("pkg test-package is untrusted" in haystack)


if __name__ == "__main__":
    # do not setup logging in here or the test will break
    unittest.main()
