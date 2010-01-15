#!/usr/bin/python

import apt_pkg
import logging
import unittest
import sys

from unattended_upgrade import conffile_prompt

class TestConffilePrompt(unittest.TestCase):
    def setUp(self):
        apt_pkg.Config.Set("Dir::State::status", "./var/lib/dpkg/status")

    def testWillPrompt(self):
        test_pkg = "./packages/conf-test-package_1.1.deb"
        self.assertTrue(conffile_prompt(test_pkg), 
                        "conffile prompt detection incorrect")


if __name__ == "__main__":
    #logging.basicConfig(level=logging.DEBUG)
    unittest.main()

