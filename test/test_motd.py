#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import os
import unittest

import unattended_upgrade
from unattended_upgrade import update_kept_pkgs_file
from test.test_base import TestBase, MockOptions


class MotdTestCase(TestBase):

    def test_packages_kept(self):
        pkgs_kept_back = {"Debian wheezy-security": ["linux-image"],
                          "Debian wheezy": ["hello", "tworld"]}
        update_kept_pkgs_file(pkgs_kept_back, os.path.join(self.tempdir,
                                                           "kept-back"))
        with open(os.path.join(self.tempdir, "kept-back"), "rb") as fp:
            kept_txt = fp.read().decode("utf-8")
        self.assertEqual('hello linux-image tworld', kept_txt)
        update_kept_pkgs_file({}, os.path.join(self.tempdir, "kept-back"))
        self.assertFalse(
            os.path.exists(os.path.join(self.tempdir, "kept-back")))

    def test_dry_run_keeps_kept_packages_file(self):
        rootdir = self.make_fake_aptroot(
            template=os.path.join(self.testdir, "root.untrusted"))
        kept_file = os.path.join(rootdir, unattended_upgrade.KEPT_PACKAGES_FILE)
        with open(kept_file, "w") as fp:
            fp.write("linux-image")
        options = MockOptions()
        options.dry_run = True
        unattended_upgrade.main(options, rootdir=rootdir)
        with open(kept_file) as fp:
            self.assertEqual("linux-image", fp.read())


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
