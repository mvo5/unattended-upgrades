#!/usr/bin/python3

import os
import shutil
import tempfile
import unittest

import apt_pkg
apt_pkg.config.set("Dir", os.path.join(os.path.dirname(__file__), "aptroot"))
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
        self.rootdir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "./root.untrusted"))
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
        unattended_upgrade.DISTRO_DESC = "Ubuntu 10.04"
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)
        unattended_upgrade.LOCK_FILE = os.path.join(tmpdir, "u-u.lock")
        unattended_upgrade.main(options, rootdir=self.rootdir)
        # read the log to see what happend
        with open(self.log) as f:
            haystack = f.read()
            self.assertTrue(
                "pkg test-package is not from a trusted origin" in haystack)
            if unattended_upgrade.get_distro_codename() == "sid":
                self.assertFalse(
                    "falling back to adjusting" in haystack)
            else:
                self.assertTrue(
                    "falling back to adjusting" in haystack)


if __name__ == "__main__":
    # do not setup logging in here or the test will break
    unittest.main()
