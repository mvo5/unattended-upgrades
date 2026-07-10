#!/usr/bin/python3

import logging
import unittest

import apt_pkg


from unattended_upgrade import substitute, get_origins_from_conf

from test.test_base import TestBase


class TestSubstitute(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.mock_distro("MyDistroID", "mycodename", "MyDistroID descr",
                         release="42")

    def testSubstitute(self):
        """ test if the substitute function works """
        self.assertEqual(substitute("${distro_codename}-updates"),
                         "mycodename-updates")
        self.assertEqual(substitute("${distro_id}"), "MyDistroID")
        self.assertEqual(substitute("${distro_release}"), "42")
        self.assertEqual(
            substitute("o=obs://x/Debian_${distro_release},"
                       "n=Debian_${distro_release}"),
            "o=obs://x/Debian_42,n=Debian_42")

    def test_get_allowed_origins_with_substitute(self):
        """ test if substitute for get_origins_from_conf works """
        apt_pkg.config.clear("Unattended-Upgrade::Allowed-Origins")
        apt_pkg.config.set("Unattended-Upgrade::Allowed-Origins::",
                           "${distro_id} ${distro_codename}-security")
        li = get_origins_from_conf()
        self.assertIn("o=MyDistroID,a=mycodename-security", li)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
