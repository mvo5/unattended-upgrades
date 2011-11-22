#!/usr/bin/python

import apt
import apt_pkg
import os
import logging
import unittest
import sys

import unattended_upgrade
from unattended_upgrade import (
    match_whitelist_string, check_changes_for_sanity, is_allowed_origin)

class MockOrigin():
    pass
class MockCandidate():
    pass
class MockPackage():
    pass
class MockCache(list):
    pass
class MockDepCache():
    pass

class TestOriginPatern(unittest.TestCase):

    def setUp(self):
        pass
    def tearDown(self):
        pass
    def test_match_whitelist_string(self):
        origin = self._get_mock_origin(
            "OriginUbuntu", "LabelUbuntu", "ArchiveUbuntu",
            "archive.ubuntu.com", "main")
        # good
        s="o=OriginUbuntu"
        self.assertTrue(match_whitelist_string(s, origin))
        s="o=OriginUbuntu,l=LabelUbuntu,a=ArchiveUbuntu,site=archive.ubuntu.com"
        self.assertTrue(match_whitelist_string(s, origin))
        # bad
        s=""
        self.assertFalse(match_whitelist_string(s, origin))
        s="o=something"
        self.assertFalse(match_whitelist_string(s, origin))
        s="o=LabelUbuntu,a=no-match"
        self.assertFalse(match_whitelist_string(s, origin))
        # with escaping
        origin = self._get_mock_origin("Google, Inc.", archive="stable")
        # good
        s="o=Google\, Inc.,a=stable"
        self.assertTrue(match_whitelist_string(s, origin))

    def test_match_whitelist_from_conffile(self):
        # read some
        apt_pkg.config.clear("Unattended-Upgrade")
        apt_pkg.read_config_file(apt_pkg.config, "./data/50unattended-upgrades.Test")
        allowed_origins = unattended_upgrade.get_allowed_origins()
        #print allowed_origins
        self.assertTrue("o=aOrigin,a=aArchive" in allowed_origins)
        self.assertTrue("s=aSite,l=aLabel" in allowed_origins)
        self.assertTrue("o=Google\, Inc.,suite=stable" in allowed_origins)

    def test_compatiblity(self):
        apt_pkg.config.clear("Unattended-Upgrade")
        apt_pkg.read_config_file(apt_pkg.config, "./data/50unattended-upgrades.compat")
        allowed_origins = unattended_upgrade.get_allowed_origins()
        #print allowed_origins
        self.assertTrue("o=Google\, Inc.,a=stable" in allowed_origins)
        self.assertTrue("o=MoreCorp\, eink,a=stable" in allowed_origins)
        # test whitelist
        pkg = self._get_mock_package()
        self.assertTrue(is_allowed_origin(pkg.candidate, allowed_origins))

    def test_blacklist(self):
        # mock pkg (yeah, complicated)
        pkg = self._get_mock_package()
        # mock cache
        cache = MockCache()
        cache._depcache = MockDepCache()
        cache._depcache.broken_count = 0
        cache.append(pkg)
        # origins and blacklist
        allowed_origins = ["o=Ubuntu"]
        blacklist = ["linux-.*"]
        # with blacklist pkg
        self.assertFalse(check_changes_for_sanity(cache, allowed_origins, blacklist))
        # with "normal" pkg
        pkg.name = "apt"
        self.assertTrue(check_changes_for_sanity(cache, allowed_origins, blacklist))   

    def _get_mock_origin(self, aorigin="", label="", archive="",
                         site="", component=""):
        origin = MockOrigin()
        origin.origin = aorigin
        origin.label = label
        origin.archive = archive
        origin.site = site
        origin.compoent = component
        return origin

    def _get_mock_package(self):
        pkg = MockPackage()
        pkg._pkg = MockPackage()
        pkg._pkg.selected_state = 0
        pkg.name = "linux-image"
        pkg.marked_install = True
        pkg.marked_upgrade = True
        pkg.marked_delete = False
        pkg.candidate = MockCandidate()
        pkg.candidate.origins = [self._get_mock_origin("Ubuntu"),
                                 self._get_mock_origin(aorigin="Google, Inc.",
                                                       archive="stable"),
                                ]
        pkg.candidate.record = {}
        return pkg


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()

