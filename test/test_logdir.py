#!/usr/bin/python

import apt_pkg
import logging
import os
import mock
import sys
import tempfile
import unittest

sys.path.insert(0, "..")
from unattended_upgrade import _setup_logging

class MockOptions:
    dry_run = False

class TestLogdir(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        apt_pkg.init()
        self.mock_options = MockOptions()

    def test_logdir(self):
        # test log
        logdir = os.path.join(self.tempdir, "mylog")
        apt_pkg.config.set("Unattended-Upgrade::LogDir", logdir)
        _setup_logging(self.mock_options)
        self.assertTrue(os.path.exists(logdir))

    def test_logdir_depreated(self):
        # test if the deprecated APT::UnattendedUpgrades dir is not used
        # if the new UnaUnattendedUpgrades::LogDir is given
        logdir = os.path.join(self.tempdir, "mylog-use")
        logdir2 = os.path.join(self.tempdir, "mylog-dontuse")
        apt_pkg.config.set("Unattended-Upgrade::LogDir", logdir)
        apt_pkg.config.set("APT::UnattendedUpgrades::LogDir", logdir2)
        _setup_logging(self.mock_options)
        self.assertTrue(os.path.exists(logdir))
        self.assertFalse(os.path.exists(logdir2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
