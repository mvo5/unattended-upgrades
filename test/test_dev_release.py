#!/usr/bin/python3

import datetime
import logging
import os
import unittest

import apt

import unattended_upgrade

apt.apt_pkg.config.set("APT::Architecture", "amd64")


class MockOptions(object):
    debug = True
    verbose = False
    dry_run = True
    apt_debug = False
    minimal_upgrade_steps = False
    download_only = False


class MockDistroAuto(object):

    start_updates = datetime.date.today()
    release = (datetime.date.today()
               + unattended_upgrade.DEVEL_UNTIL_RELEASE
               + datetime.timedelta(days=1))
    series = "artful"

    def devel(self, result):
        assert result == "object"
        return self


class MockDistroNoAuto(object):

    release = (datetime.date.today()
               + unattended_upgrade.DEVEL_UNTIL_RELEASE)
    series = "artful"

    def devel(self, result):
        assert result == "object"
        return self


class MockDistroNoRelease(object):

    release = None
    series = "artful"

    def devel(self, result):
        assert result == "object"
        return self


class MockDistroInfoModule(object):

    def __init__(self, ubuntu):
        self.UbuntuDistroInfo = ubuntu


class TestUntrusted(unittest.TestCase):

    def setUp(self):
        apt.apt_pkg.config.set("Unattended-Upgrade::"
                               "Skip-Updates-On-Metered-Connections",
                               "false")
        apt.apt_pkg.config.set("Unattended-Upgrade::OnlyOnAcPower",
                               "false")
        unattended_upgrade.LOCK_FILE = "./u-u.lock"
        self.rootdir = os.path.abspath("./root.untrusted")
        self.log = os.path.join(
            self.rootdir, "var", "log", "unattended-upgrades",
            "unattended-upgrades.log")

        self.apt_conf = os.path.join(self.rootdir, "etc", "apt",
                                     "apt.conf")

        os.rename(self.apt_conf, self.apt_conf + ".bak")
        for hdlr in logging.root.handlers:
            hdlr.close()
        logging.root.handlers = []

    def tearDown(self):
        os.remove(self.log)
        os.rename(self.apt_conf + ".bak", self.apt_conf)

    def write_config(self, devrelease):
        with open(self.apt_conf, "w") as fp:
            fp.write("""Unattended-Upgrade::DevRelease "%s";
Unattended-Upgrade::Skip-Updates-On-Metered-Connections "false";
Unattended-Upgrade::OnlyOnAcPower "false";
""" % devrelease)

    def test_do_not_run_on_devrelease(self):
        self.write_config("false")

        # run it
        options = MockOptions()
        unattended_upgrade.DISTRO_DESC = "Artful Aardvark (development branch)"
        unattended_upgrade.main(options, rootdir=self.rootdir)
        # read the log to see what happend
        with open(self.log) as f:
            needle = "Not running on the development release"
            haystack = f.read()
            self.assertTrue(needle in haystack,
                            "Can not find '%s' in '%s'" % (needle, haystack))

    def test_auto_devrelease(self):
        """We are not ready to auto upgrade just yet"""
        self.write_config("auto")

        # run it
        unattended_upgrade.distro_info = MockDistroInfoModule(MockDistroAuto)

        options = MockOptions()
        unattended_upgrade.DISTRO_DESC = "Artful Aardvark (development branch)"
        unattended_upgrade.DISTRO_CODENAME = "artful"
        unattended_upgrade.DISTRO_ID = "ubuntu"
        unattended_upgrade.main(options, rootdir=self.rootdir)
        # read the log to see what happend
        with open(self.log) as f:
            needle = ("Not running on this development release before %s"
                      % MockDistroAuto.start_updates)
            haystack = f.read()
            self.assertTrue(needle in haystack,
                            "Can not find '%s' in '%s'" % (needle, haystack))

    def test_noauto_devrelease(self):
        """We are in the valid time period"""
        self.write_config("auto")
        # run it
        unattended_upgrade.distro_info = MockDistroInfoModule(MockDistroNoAuto)

        options = MockOptions()
        unattended_upgrade.DISTRO_DESC = "Artful Aardvark (development branch)"
        unattended_upgrade.DISTRO_CODENAME = "artful"
        unattended_upgrade.DISTRO_ID = "ubuntu"
        unattended_upgrade.main(options, rootdir=self.rootdir)
        # read the log to see what happend
        with open(self.log) as f:
            # Check that we could have run
            needle = "Running on the development release"
            haystack = f.read()
            self.assertTrue(needle in haystack,
                            "Can not find '%s' in '%s'" % (needle, haystack))

    def test_norelease_devrelease(self):
        """The devel series has no release update, so do updates"""
        self.write_config("auto")
        # run it
        unattended_upgrade.distro_info = MockDistroInfoModule(MockDistroNoAuto)

        options = MockOptions()
        unattended_upgrade.DISTRO_DESC = "Artful Aardvark (development branch)"
        unattended_upgrade.DISTRO_CODENAME = "artful"
        unattended_upgrade.DISTRO_ID = "ubuntu"
        unattended_upgrade.main(options, rootdir=self.rootdir)
        # read the log to see what happend
        with open(self.log) as f:
            # Check that we could have run
            needle = "Running on the development release"
            haystack = f.read()
            self.assertTrue(needle in haystack,
                            "Can not find '%s' in '%s'" % (needle, haystack))


if __name__ == "__main__":
    # do not setup logging in here or the test will break
    unittest.main()
