#!/usr/bin/python3

import unittest
from unittest.mock import Mock

import apt_pkg

from unattended_upgrade import UnattendedUpgradesCache

from test.test_base import TestBase


class TestKeptPackageExcuse(TestBase):

    def excuse(self, whitelist=(), strict_whitelist=False, blacklist=(),
               hold=False, trusted=True):
        pkg = Mock()
        pkg.name = "foo"
        pkg.selected_state = (apt_pkg.SELSTATE_HOLD if hold
                              else apt_pkg.SELSTATE_INSTALL)
        better_version = Mock(origins=[Mock(trusted=trusted)])
        # the method does not use the cache itself
        return UnattendedUpgradesCache.kept_package_excuse(
            None, pkg, blacklist, whitelist, strict_whitelist,
            better_version)

    def test_held(self):
        self.assertEqual(self.excuse(hold=True),
                         "Package foo is marked to be held back.")

    def test_blacklisted(self):
        self.assertEqual(self.excuse(blacklist=("foo",)),
                         "Package foo is blacklisted.")

    def test_not_on_strict_whitelist(self):
        self.assertEqual(
            self.excuse(whitelist=("bar",), strict_whitelist=True),
            "Package foo is not on the strict whitelist.")

    def test_not_whitelisted(self):
        self.assertEqual(
            self.excuse(whitelist=("bar",)),
            "Package foo is not whitelisted and it is not a dependency of a "
            "whitelisted package.")

    def test_untrusted(self):
        for whitelist in ((), ("foo",)):
            self.assertEqual(self.excuse(whitelist=whitelist, trusted=False),
                             "Package foo's origin is not trusted.")

    def test_other_reason(self):
        for whitelist in ((), ("foo",)):
            self.assertEqual(
                self.excuse(whitelist=whitelist),
                "Package foo is kept back because a related package is kept "
                "back or due to local apt_preferences(5).")


if __name__ == "__main__":
    unittest.main()
