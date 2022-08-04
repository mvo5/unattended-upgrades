#!/usr/bin/python3

import os
import unittest

from test.test_base import MockOptions, TestBase

import unattended_upgrade


class TestOnBattery(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.rootdir = self.make_fake_aptroot(
            template=os.path.join(self.testdir, "root.on-battery"))
        # FIXME: make this more elegant
        # fake on_ac_power
        os.environ["PATH"] = (os.path.join(self.rootdir, "usr", "bin") + ":"
                              + os.environ["PATH"])
        self.log = os.path.join(
            self.rootdir, "var", "log", "unattended-upgrades",
            "unattended-upgrades.log")
        self.mock_distro("ubuntu", "artful", "Artful Aardvark (development branch)")

    def test_on_battery(self):
        # run it
        options = MockOptions()
        ret = unattended_upgrade.main(options, rootdir=self.rootdir)
        self.assertEqual(ret, 1)
        # read the log to see what happend
        with open(self.log) as f:
            needle = "System is on battery power, stopping"
            haystack = f.read()
            self.assertTrue(needle in haystack,
                            "Can not find '%s' in '%s'" % (needle, haystack))


if __name__ == "__main__":
    # do not setup logging in here or the test will break
    unittest.main()
