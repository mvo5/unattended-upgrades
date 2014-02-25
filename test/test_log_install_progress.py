#!/usr/bin/python

import apt_pkg
import logging
import os
import sys
import tempfile
import unittest

sys.path.insert(0, "..")

from unattended_upgrades import _setup_logging


class MockOptions:
    dry_run = False
    debug = False
    verbose = False


class TestLogInstallProgress(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        apt_pkg.init()
        self.mock_options = MockOptions()

    def test_log_installprogress(self):
        logdir = os.path.join(self.tempdir, "mylog")
        apt_pkg.config.set("Unattended-Upgrade::LogDir", logdir)
        logging.root.handlers = []
        _setup_logging(self.mock_options)
        self.assertTrue(os.path.exists(logdir))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
