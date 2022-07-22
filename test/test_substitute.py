#!/usr/bin/python3

import logging
import os
import unittest

import apt_pkg
apt_pkg.config.set("Dir", os.path.join(os.path.dirname(__file__), "aptroot"))

import unattended_upgrade
from unattended_upgrade import substitute, get_allowed_origins

from test.test_base import TestBase


class TestSubstitute(TestBase):

    def setUp(self):
        TestBase.setUp(self)
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
        li = get_allowed_origins()
        self.assertTrue(("o=MyDistroID,a=nacked-security") in li)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
