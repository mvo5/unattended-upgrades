#!/usr/bin/python3


import os
import shutil
import tempfile
import unittest

import apt_pkg
apt_pkg.config.set("Dir", "./aptroot")
import apt
import unattended_upgrade

try:
    from typing import List
    List   # pyflaks
except ImportError:
    pass


class MockFetcher:
    items = []  # type: List[MockAcquireItem]


class MockAcquireItem:
    def __init__(self, destfile):
        self.destfile = destfile


class TestClean(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir)
        os.chdir(self.tempdir)

    def test_clean(self):
        apt.apt_pkg.config.set("dir::cache::archives", self.tempdir)
        os.makedirs("dir")
        with open("file1", "w"):
            pass
        with open("file2", "w"):
            pass
        with open("lock", "w"):
            pass
        fetcher = MockFetcher()
        fetcher.items = [MockAcquireItem("file1"), MockAcquireItem("file2")]
        unattended_upgrade.clean_downloaded_packages(fetcher)
        # files get removed
        self.assertEqual(os.path.exists("file1"), False)
        self.assertEqual(os.path.exists("file2"), False)
        # exluces are honored
        self.assertEqual(os.path.exists("lock"), True)
        # dirs are untouched
        self.assertEqual(os.path.exists("dir"), True)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
