#!/usr/bin/python3

import logging
import os
import unittest

import apt_pkg
apt_pkg.config.set("Dir", os.path.join(os.path.dirname(__file__), "aptroot"))

from unattended_upgrade import _setup_logging
from test.test_base import TestBase, MockOptions


class TestLogdir(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.mock_options = MockOptions()

    def test_logdir(self):
        # test log
        logdir = os.path.join(self.tempdir, "mylog")
        apt_pkg.config.set("Unattended-Upgrade::LogDir", logdir)
        logging.root.handlers = []
        _setup_logging(self.mock_options)
        self.assertTrue(os.path.exists(logdir))

    def test_logdir_depreated(self):
        # test if the deprecated APT::UnattendedUpgrades dir is not used
        # if the new UnaUnattendedUpgrades::LogDir is given
        logdir = os.path.join(self.tempdir, "mylog-use")
        logdir2 = os.path.join(self.tempdir, "mylog-dontuse")
        apt_pkg.config.set("Unattended-Upgrade::LogDir", logdir)
        apt_pkg.config.set("APT::UnattendedUpgrades::LogDir", logdir2)
        logging.root.handlers = []
        _setup_logging(self.mock_options)
        self.assertTrue(os.path.exists(logdir))
        self.assertFalse(os.path.exists(logdir2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
