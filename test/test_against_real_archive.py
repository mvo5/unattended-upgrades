#!/usr/bin/python

import apt
import apt_pkg
import glob
import os
import logging
import unittest
import sys

import unattended_upgrade

apt_pkg.config.set("APT::Architecture", "amd64")

class MockOptions():
    def __init__(self, debug=True, dry_run=True):
        self.debug = debug
        self.dry_run = dry_run

class TestAgainstRealArchive(unittest.TestCase):

    def setUp(self):
        for f in glob.glob("./aptroot/var/log/*"):
            if os.path.isfile(f):
                os.remove(f)

    def test_against_real_archive(self):
        # get a lucid based cache (test good for 5y)
        cache = apt.Cache(rootdir="./aptroot")
        cache.update()
        del cache
        # create mock options
        options = MockOptions(debug=False)
        # run unattended-upgrades against fake system
        logdir = os.path.abspath("./aptroot/var/log/")
        logfile = os.path.join(logdir, "unattended-upgrades.log")
        apt_pkg.config.set("APT::UnattendedUpgrades::LogDir", logdir)
        unattended_upgrade.main(options, "./aptroot")
        # check if the log file exists
        self.assertTrue(os.path.exists(logfile))
        log = open(logfile).read()
        # check if we actually have the expected ugprade in it
        self.assertTrue("INFO Packages that are upgraded: awstats" in log)

if __name__ == "__main__":
    unittest.main()

