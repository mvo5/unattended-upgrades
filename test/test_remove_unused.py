#!/usr/bin/python

import os
import unittest

import apt

import unattended_upgrade

apt.apt_pkg.config.set("APT::Architecture", "amd64")


class MockOptions(object):
    debug = False
    verbose = False
    dry_run = True
    apt_debug = False
    minimal_upgrade_steps = False


class TestRemoveUnused(unittest.TestCase):

    def setUp(self):
        self.rootdir = os.path.abspath("./root.unused-deps")
        dpkg_status = os.path.abspath(
            os.path.join(self.rootdir, "var", "lib", "dpkg", "status"))
        apt.apt_pkg.config.set("Dir::State::status", dpkg_status)
        apt.apt_pkg.config.clear("DPkg::Pre-Invoke")
        apt.apt_pkg.config.clear("DPkg::Post-Invoke")
        # pretend test-package-dependency is auto-installed
        extended_states = os.path.join(
            self.rootdir, "var", "lib", "apt", "extended_states")
        with open(extended_states, "w") as f:
            f.write("Package: test-package-dependency\nAuto-Installed: 1\n")

    def test_remove_unused_dependencies(self):
        options = MockOptions()
        unattended_upgrade.main(
            options, rootdir="./root.unused-deps")
        log = os.path.join(
            self.rootdir, "var", "log", "unattended-upgrades",
            "unattended-upgrades.log")
        with open(log) as f:
            needle = "Packages that are auto removed: "\
                     "'test-package-dependency'"
            haystack = f.read()
            self.assertTrue(needle in haystack,
                            "Can not find '%s' in '%s'" % (needle, haystack))


if __name__ == "__main__":
    # do not setup logging in here or the test will break
    unittest.main()
