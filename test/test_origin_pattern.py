#!/usr/bin/python

import apt
import apt_pkg
import os
import logging
import unittest
import sys

import unattended_upgrade
import unattended_upgrade
from unattended_upgrade import match_whitelist_string, check_changes_for_sanity

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
    def _get_mock_origin(self, aorigin="", label="", archive="",
                         site="", component=""):
        origin = MockOrigin()
        origin.origin = aorigin
        origin.label = label
        origin.archive = archive
        origin.site = site
        origin.compoent = component
        return origin
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

    def test_blacklist(self):
        # mock pkg (yeah, complicated)
        pkg = MockPackage()
        pkg._pkg = MockPackage()
        pkg._pkg.selected_state = 0
        pkg.name = "linux-image"
        pkg.marked_install = True
        pkg.marked_delete = False
        pkg.candidate = MockCandidate()
        pkg.candidate.origins = [self._get_mock_origin("Ubuntu")]
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()

