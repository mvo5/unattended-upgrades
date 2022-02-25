#!/usr/bin/python3

import logging
import os
import os.path
import shutil
import tempfile
import unittest

import unattended_upgrade


class MockOptions(object):
    debug = True
    verbose = False
    download_only = False
    dry_run = False
    apt_debug = False
    minimal_upgrade_steps = True


class TestBase(unittest.TestCase):
    def setUp(self):
        super(TestBase, self).setUp()
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir)
        self.testdir = os.path.dirname(__file__)
        # ensure custom logging gets reset (XXX: does this work?)
        self.addCleanup(logging.shutdown)
        logging.root.handlers = []
        # XXX: workaround for most tests assuming to run inside the "test"
        # dir
        os.chdir(self.testdir)
        # fake the lock file
        unattended_upgrade.LOCK_FILE = os.path.join(self.tempdir, "u-u.lock")
