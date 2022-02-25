#!/usr/bin/python3

import logging
import os
import os.path
import sys
import tempfile
import unittest

import apt_pkg
apt_pkg.config.set("Dir", os.path.join(os.path.dirname(__file__), "./aptroot"))

from test.test_base import TestBase, MockOptions

from unattended_upgrade import _setup_logging


class TestLogInstallProgress(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.mock_options = MockOptions()

    def test_log_installprogress(self):
        logdir = os.path.join(self.tempdir, "mylog")
        apt_pkg.config.set("Unattended-Upgrade::LogDir", logdir)
        # XXX: move this into TestBase
        logging.root.handlers = []
        # FIXME: this test is really not testing much, see if that
        # can be improved
        _setup_logging(self.mock_options)
        self.assertTrue(os.path.exists(logdir))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
