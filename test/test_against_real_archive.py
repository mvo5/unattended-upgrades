#!/usr/bin/python

import apt
import apt_pkg
import glob
import os
import re
import unittest

import unattended_upgrade

apt_pkg.config.set("APT::Architecture", "amd64")


class MockOptions():
    def __init__(self, debug=True, dry_run=False):
        self.debug = debug
        self.dry_run = dry_run
        self.minimal_upgrade_steps = False
        self.verbose = False


class TestAgainstRealArchive(unittest.TestCase):

    def setUp(self):
        for f in glob.glob("./aptroot/var/log/*"):
            if os.path.isfile(f):
                os.remove(f)
        # get a lucid based cache (test good until 04/2015)
        cache = apt.Cache(rootdir="./aptroot")
        cache.update()
        del cache
        # ensure apt does not do any post-invoke stuff that fails
        # (because we are not root)
        apt_pkg.config.clear("DPkg::Post-Invoke")
        unattended_upgrade.DISTRO_CODENAME = "lucid"

    def test_against_real_archive(self):
        # create mock options
        options = MockOptions(dry_run=False, debug=True)
        # run unattended-upgrades against fake system
        logdir = os.path.abspath("./aptroot/var/log/")
        logfile = os.path.join(logdir, "unattended-upgrades.log")
        apt_pkg.config.set("APT::UnattendedUpgrades::LogDir", logdir)

        # main
        res = unattended_upgrade.main(options, os.path.abspath("./aptroot"))

        # check if the log file exists
        self.assertTrue(os.path.exists(logfile))
        log = open(logfile).read()
        # check that stuff worked
        self.assertFalse(" ERROR " in log)
        # check if we actually have the expected ugprade in it
        self.assertTrue(
            re.search("INFO Packages that will be upgraded:.*awstats", log))
        # apt-doc has a higher version in -updates than in -security
        # and no other dependencies so its a perfect test
        self.assertTrue(
            re.search("INFO Packages that will be upgraded:.*apt-doc", log))
        self.assertFalse(
            re.search("INFO Packages that will be upgraded:.*ant-doc", log))
        self.assertTrue(
            re.search("DEBUG skipping blacklisted package 'ant-doc'", log))
        # test install log 
        #print open("aptroot/var/log/apt/history.log").read()
        #print open("aptroot/var/log/apt/term.log").read()


if __name__ == "__main__":
    import locale
    locale.setlocale(locale.LC_ALL, "C")
    unittest.main()

