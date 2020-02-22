#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import os
import shutil
import tempfile
import unittest

from unattended_upgrade import update_kept_pkgs_file


class MotdTestCase(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir)
        self.addCleanup(logging.shutdown)

    def test_packages_kept(self):
        pkgs_kept_back = {"Debian wheezy-security": ["linux-image"],
                          "Debian wheezy": ["hello", "tworld"]}
        update_kept_pkgs_file(pkgs_kept_back, os.path.join(self.tmpdir,
                                                           "kept-back"))
        with open(os.path.join(self.tmpdir, "kept-back"), "rb") as fp:
            kept_txt = fp.read().decode("utf-8")
        self.assertEqual('hello linux-image tworld', kept_txt)
        update_kept_pkgs_file({}, os.path.join(self.tmpdir, "kept-back"))
        self.assertFalse(
            os.path.exists(os.path.join(self.tmpdir, "kept-back")))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
