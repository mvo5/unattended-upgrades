#!/usr/bin/python

import apt
import apt_pkg
import os
import logging
import unittest
import sys
import time

import unattended_upgrade
from unattended_upgrade import upgrade_in_minimal_steps

class TestMinimalPartitions(unittest.TestCase):

    def setUp(self):
        # setup dry-run mode for apt
        apt_pkg.config.set("Dir::Cache", "/tmp")
        apt_pkg.config.set("Debug::NoLocking","1")
        apt_pkg.config.set("Debug::pkgDPkgPM","1")
        apt_pkg.config.set("Dir::State::extended_states", "./extended_states")
        apt_pkg.config.clear("Dpkg::Post-Invoke")
        apt_pkg.config.clear("Dpkg::Pre-Install-Pkgs")
        self.cache = apt.Cache()

    def tearDown(self):
        if os.path.exists("./extended_states"):
            os.remove("./extended_states")

    def test_upgrade_in_minimal_steps(self):
        self.cache.upgrade(True)
        pkgs_to_upgrade = [pkg.name for pkg in self.cache.get_changes()]
        upgrade_in_minimal_steps(self.cache, pkgs_to_upgrade)
        

if __name__ == "__main__":
    #logging.basicConfig(level=logging.DEBUG)
    unittest.main()
