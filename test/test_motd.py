#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import os
import unittest

from unattended_upgrade import update_kept_pkgs_file
from test.test_base import TestBase


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


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
