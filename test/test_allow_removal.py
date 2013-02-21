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


class AllowRemovalTestCase(unittest.TestCase):

    def setUp(self):
        for g in ["./fake-aptroot/var/log/apt/*",
                  "./fake-aptroot/var/log/*"]:
            for f in glob.glob(g):
                if os.path.isfile(f):
                    os.remove(f)
        # get a lucid based cache (test good until 04/2015)
        cache = apt.Cache(rootdir="./fake-aptroot")
        cache # pyflakes

    def test_against_fake_archive(self):
        # create mock options
        options = MockOptions(dry_run=False, debug=True)
        # run unattended-upgrades against fake system
        logdir = os.path.abspath("./fake-aptroot/var/log/")
        logfile = os.path.join(logdir, "unattended-upgrades.log")
        apt_pkg.config.set("APT::UnattendedUpgrades::LogDir", logdir)
        apt_pkg.config.clear("DPkg::Post-Invoke")
        apt_pkg.config.clear("DPkg::Pre-Invoke")

        # main
        res = unattended_upgrade.main(
            options, os.path.abspath("./fake-aptroot"))

        # check if the log file exists
        self.assertTrue(os.path.exists(logfile))
        log = open(logfile).read()
        # ensure upgrade works
        res = re.search("Packages that will be upgraded:.*ubuntuone-client", log)
        #print log[res.start():res.end()]
        self.assertNotEqual(res, None)
            


if __name__ == "__main__":
    import locale
    locale.setlocale(locale.LC_ALL, "C")
    unittest.main()
