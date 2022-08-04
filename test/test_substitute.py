#!/usr/bin/python3

import logging
import unittest

import apt_pkg


from unattended_upgrade import substitute, get_allowed_origins

from test.test_base import TestBase


class TestSubstitute(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.mock_distro("MyDistroID", "mycodename", "MyDistroID descr")

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
        self.assertIn("o=MyDistroID,a=mycodename-security", li)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
