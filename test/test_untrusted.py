#!/usr/bin/python3

import os
import unittest

from test.test_base import TestBase, MockOptions

import unattended_upgrade


class TestUntrusted(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.rootdir = self.make_fake_aptroot(
            template=os.path.join(self.testdir, "root.untrusted"))
        self.log = os.path.join(
            self.rootdir, "var", "log", "unattended-upgrades",
            "unattended-upgrades.log")
        self.mock_distro("Ubuntu", "lucid", "Ubuntu 10.04")

    def test_untrusted_check_without_conffile_check(self):
        options = MockOptions()
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
