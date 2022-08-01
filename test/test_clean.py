#!/usr/bin/python3


import os
import os.path
import unittest

import apt_pkg
apt_pkg.config.set("Dir", os.path.join(os.path.dirname(__file__), "aptroot"))
import apt
import unattended_upgrade

try:
    from typing import List
    List   # pyflaks
except ImportError:
    pass

from test.test_base import TestBase


class MockFetcher:
    items = []  # type: List[MockAcquireItem]


class MockAcquireItem:
    def __init__(self, destfile):
        self.destfile = destfile


class TestClean(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        os.chdir(self.tempdir)

    def test_clean(self):
        apt.apt_pkg.config.set("dir::cache::archives", self.tempdir)
        self.addCleanup(apt.apt_pkg.config.clear, "dir::cache::archives")
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
