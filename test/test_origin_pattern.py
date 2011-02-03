#!/usr/bin/python

import apt
import apt_pkg
import os
import logging
import unittest
import sys

import unattended_upgrade
import unattended_upgrade
from unattended_upgrade import match_whitelist_string

class MockOrigin():
    pass

class TestOriginPatern(unittest.TestCase):

    def setUp(self):
        pass
    def tearDown(self):
        pass
    def _get_mock_origin(self, aorigin, label, archive, site, component):
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()

