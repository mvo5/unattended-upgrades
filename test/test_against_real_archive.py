#!/usr/bin/python3
"""Test unattended_upgrades against the real archive in a chroot.

Note that this test is not run by the makefile in this folder, as it requires
network access, and it fails in some situations (unclear which).
"""

import apt
import apt_pkg
import glob
import logging
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
        for g in ["./aptroot/var/log/apt/*",
                  "./aptroot/var/log/*"]:
            for f in glob.glob(g):
                if os.path.isfile(f):
                    os.remove(f)
        # get a lucid based cache (test good until 04/2015)
        cache = apt.Cache(rootdir="./aptroot")
        cache.update()
        del cache
        # ensure apt does not do any post-invoke stuff that fails
        # (because we are not root)
        apt_pkg.config.clear("DPkg::Post-Invoke")
        apt_pkg.config.clear("DPkg::Pre-Invoke")
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
        logging.debug(res)
        # check if the log file exists
        self.assertTrue(os.path.exists(logfile))
        with open(logfile) as fp:
            log = fp.read()
        # check that stuff worked
        self.assertFalse(" ERROR " in log, log)
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
        # test dpkg install log
        #term_log = open("aptroot/var/log/apt/term.log").read()
        # FIXME: when we redirect STDIN the below test will break - however
        #        we need to redirect it as otherwise we may hang forever
        #        - this is actually a bug in apt that uses "tcgetattr(0, &tt)"
        #          on FD=0 instead of FD=1
        #print term_log
        #self.assertTrue(
        #    re.search(
        #        "fake-dpkg: --status-fd .* --configure.*awstats", term_log))


if __name__ == "__main__":
    import locale
    locale.setlocale(locale.LC_ALL, "C")
    unittest.main()
