#!/usr/bin/python3

from __future__ import annotations

import os
import os.path
import unittest
from unittest.mock import patch

import apt
import unattended_upgrade

from test.test_base import TestBase


class MockFetcher:
    items: list[MockAcquireItem] = []


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

    def test_retained_transaction_archives(self):
        apt.apt_pkg.config.set("dir::cache::archives", self.tempdir)
        fetcher = MockFetcher()
        names = ("driver", "dependency", "ordinary")
        for name in names:
            with open(name, "w"):
                pass
        fetcher.items = [MockAcquireItem(name) for name in names]
        with patch("unattended_upgrade.pkgname_from_deb", side_effect=lambda p: p):
            unattended_upgrade.clean_downloaded_packages(
                fetcher, {"driver", "dependency"})
        self.assertTrue(os.path.exists("driver"))
        self.assertTrue(os.path.exists("dependency"))
        self.assertFalse(os.path.exists("ordinary"))


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
