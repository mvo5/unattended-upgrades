#!/usr/bin/python

import apt
import apt_pkg
import os
import logging
import unittest
import sys
import time

import unattended_upgrade
from unattended_upgrade import MyCache, upgrade_in_minimal_steps

class TestMinimalPartitions(unittest.TestCase):

    def setUp(self):
        apt_pkg.config.set("Debug::NoLocking","1")
        self.cache = MyCache()

    def test_get_allowed_origins_with_substitute(self):
        self.cache.upgrade(True)
        pkgs_to_upgrade = [pkg.name for pkg in self.cache.get_changes()]
        apt_pkg.config.set("Debug::pkgDPkgPM","1")
        upgrade_in_minimal_steps(self.cache, pkgs_to_upgrade)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
