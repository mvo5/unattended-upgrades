#!/usr/bin/python

import apt_pkg
import logging
import unittest
import sys

from unattended_upgrade import conffile_prompt

class TestConffilePrompt(unittest.TestCase):
    def setUp(self):
        apt_pkg.config.set("Dir::State::status",
                           "./root.conffile/var/lib/dpkg/status")

    def testWillPrompt(self):
        # conf-test 0.9 is installed, 1.1 gets installed
        # they both have different config files
        test_pkg = "./packages/conf-test-package_1.1.deb"
        self.assertTrue(conffile_prompt(test_pkg, prefix="./root.conffile"),
                        "conffile prompt detection incorrect")
    
    def testWillNotPrompt(self):
        # conf-test 0.9 is installed, 1.0 gets installed
        # they both have the same config files
        test_pkg = "./packages/conf-test-package_1.0.deb"
        self.assertFalse(conffile_prompt(test_pkg, prefix="./root.conffile"),
                        "conffile prompt detection incorrect")

    def testWillNotPrompt(self):
        # ensure we don't crash when encountering a conffile with overly
        # many entries
        test_pkg = "./packages/conf-test-package-257-conffiles_1.deb"
        self.assertFalse(conffile_prompt(test_pkg, prefix="./root.conffile"),
                        "conffile prompt detection incorrect")
        # no conffiles anymore in the pkg
        test_pkg = "./packages/conf-test-package-no-conffiles-anymore_2.deb"
        self.assertFalse(conffile_prompt(test_pkg, prefix="./root.conffile"),
                        "conffile prompt detection incorrect")

    def testWillPromptMultiple(self):
        test_pkg = "./packages/multiple-conffiles_2_all.deb"
        self.assertTrue(conffile_prompt(test_pkg, prefix="./root.conffile"),
                        "conffile prompt detection incorrect")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()

