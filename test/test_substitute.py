#!/usr/bin/python

import apt
import apt_pkg
import os
import logging
import unittest
import sys

from StringIO import StringIO

import unattended_upgrade
from unattended_upgrade import substitute, get_allowed_origins

class TestSubstitude(unittest.TestCase):

    def setUp(self):
        # monkey patch DISTRO_{CODENAME, ID}
        unattended_upgrade.DISTRO_CODENAME = "nacked"
        unattended_upgrade.DISTRO_ID = "MyDistroID"

    def testSubstitute(self):
        """ test if the substitute function works """
        self.assertTrue(substitute("${distro_codename}-updates"),
                        "nacked-updates")
        self.assertTrue(substitute("${distro_id}"), "MyDistroID")

    def test_get_allowed_origins_with_substitute(self):
        """ test if substitute for get_allowed_origins works """
        apt_pkg.config.clear("Unattended-Upgrade::Allowed-Origins")
        apt_pkg.config.set("Unattended-Upgrade::Allowed-Origins::",
                           "${distro_id} ${distro_codename}-security")
        l = get_allowed_origins()
        self.assertTrue(("o=MyDistroID,a=nacked-security") in l)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()

