#!/usr/bin/python3

import os
import os.path
import shutil
import tempfile
import unittest


class TestBase(unittest.TestCase):
    def setUp(self):
        super(TestBase, self).setUp()
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir)
        self.testdir = os.path.dirname(__file__)
        os.chdir(self.testdir)
