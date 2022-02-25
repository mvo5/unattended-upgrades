#!/usr/bin/python3

import os
import os.path
import shutil
import tempfile
import unittest


class MockOptions(object):
    debug = False
    verbose = False
    download_only = False
    dry_run = True
    apt_debug = False
    minimal_upgrade_steps = True


class TestBase(unittest.TestCase):
    def setUp(self):
        super(TestBase, self).setUp()
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir)
        self.testdir = os.path.dirname(__file__)
        os.chdir(self.testdir)
