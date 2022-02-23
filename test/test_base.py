#!/usr/bin/python3

import os
import tempfile
import unittest

import apt


# FIXME: dataclass?
class MockOptions(object):
    debug = True
    verbose = False
    download_only = False
    dry_run = True
    apt_debug = False
    minimal_upgrade_steps = True


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.rootdir = tempfile.mkdtemp()
        dpkg_status = os.path.abspath(
            os.path.join(self.rootdir, "var", "lib", "dpkg", "status"))
        apt.apt_pkg.config.set("Dir::State::status", dpkg_status)
        apt.apt_pkg.config.clear("DPkg::Pre-Invoke")
        apt.apt_pkg.config.clear("DPkg::Post-Invoke")
        self.log = os.path.join(
            self.rootdir, "var", "log", "unattended-upgrades",
            "unattended-upgrades.log")
        os.makedirs(os.path.join(self.rootdir, "var", "lib", "dpkg", "updates"))
