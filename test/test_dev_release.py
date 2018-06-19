#!/usr/bin/python

import os
import unittest

import apt

import unattended_upgrade

apt.apt_pkg.config.set("APT::Architecture", "amd64")


class MockOptions(object):
    debug = True
    verbose = False
    dry_run = True
    apt_debug = False
    minimal_upgrade_steps = False


class TestUntrusted(unittest.TestCase):

    def setUp(self):
        self.rootdir = os.path.abspath("./root.untrusted")
        self.log = os.path.join(
            self.rootdir, "var", "log", "unattended-upgrades",
            "unattended-upgrades.log")

    def tearDown(self):
        os.remove(self.log)

    def test_do_not_run_on_devrelease(self):
        apt_conf = os.path.join(self.rootdir, "etc", "apt", "apt.conf")
        with open(apt_conf, "w") as fp:
            fp.write("""Unattended-Upgrade::DevRelease "false";
Unattended-Upgrade::OnlyOnACPower "false";
""")

        # run it
        options = MockOptions()
        unattended_upgrade.DISTRO_DESC = "Artful Aardvark (development branch)"
        unattended_upgrade.main(options, rootdir=self.rootdir)
        # read the log to see what happend
        with open(self.log) as f:
            needle = "Not running on the development release."
            haystack = f.read()
            self.assertTrue(needle in haystack,
                            "Can not find '%s' in '%s'" % (needle, haystack))


if __name__ == "__main__":
    # do not setup logging in here or the test will break
    unittest.main()
