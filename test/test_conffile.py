#!/usr/bin/python3

import os
import logging
import shutil
import unittest

import apt_pkg
apt_pkg.config.set("Dir", os.path.join(os.path.dirname(__file__), "aptroot"))

from unattended_upgrade import (
    conffile_prompt,
    dpkg_conffile_prompt,
)
from test.test_base import TestBase


class ConffilePromptTestCase(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.rootdir = os.path.join(self.testdir, "root.conffile")
        self.packagedir = os.path.join(self.testdir, "packages")
        mock_dpkg_status = os.path.join(self.rootdir, "var/lib/dpkg/status")
        apt_pkg.config.set("Dir::State::status", mock_dpkg_status)
        with open(os.path.join(
                self.rootdir, "etc/configuration-file"), "w") as fp:
            fp.write("""This is a configuration file,
dfasddfasdff
No really.
""")

    def tearDown(self):
        try:
            os.remove(os.path.join(self.rootdir, "etc/configuration-file"))
        except Exception:
            pass
        try:
            shutil.rmtree(os.path.join(self.rootdir, "etc/configuration-file"))
        except Exception:
            pass

    def test_will_prompt(self):
        # conf-test 0.9 is installed, 1.1 gets installed
        # they both have different config files
        test_pkg = os.path.join(self.packagedir, "conf-test-package_1.1.deb")
        self.assertTrue(conffile_prompt(test_pkg, prefix=self.rootdir),
                        "conffile prompt detection incorrect")

    def test_will_prompt_on_moves(self):
        # changed /etc/foo becomes different /etc/foo/foo
        test_pkg = os.path.join(self.packagedir, "test-package_1.2_all.deb")
        self.assertTrue(conffile_prompt(test_pkg, prefix=self.rootdir),
                        "conffile prompt detection incorrect")
        # changed /etc/foo/foo becomes different /etc/foo
        test_pkg = os.path.join(self.packagedir, "test-package-2_1.2_all.deb")
        self.assertTrue(conffile_prompt(test_pkg, prefix=self.rootdir),
                        "conffile prompt detection incorrect")

    def test_prompt_on_deleted_modified_conffile(self):
        # conf-test 0.9 is installed, 1.1 gets installed
        # they both have different config files, this triggers a prompt
        os.remove("./root.conffile/etc/configuration-file")
        test_pkg = os.path.join(self.packagedir, "conf-test-package_1.1.deb")
        self.assertTrue(conffile_prompt(test_pkg, prefix=self.rootdir),
                        "conffile prompt detection incorrect")

    def test_will_not_prompt(self):
        # conf-test 0.9 is installed, 1.0 gets installed
        # they both have the same config files
        test_pkg = os.path.join(self.packagedir, "conf-test-package_1.0.deb")
        self.assertFalse(conffile_prompt(test_pkg, prefix=self.rootdir),
                         "conffile prompt detection incorrect")

    def test_will_not_prompt_on_moves(self):
        # changed /etc/foo becomes /etc/foo/foo, same as shipped before
        test_pkg = os.path.join(self.packagedir, "test-package_1.3_all.deb")
        self.assertFalse(conffile_prompt(test_pkg, prefix=self.rootdir),
                         "conffile prompt detection incorrect")
        # changed /etc/foo/foo becomes /etc/foo, same as shipped before
        test_pkg = os.path.join(
            self.packagedir, "test-package-2_1.3_all.deb")
        self.assertFalse(conffile_prompt(test_pkg, prefix=self.rootdir),
                         "conffile prompt detection incorrect")

    def test_with_many_entries(self):
        # ensure we don't crash when encountering a conffile with overly
        # many entries
        test_pkg = os.path.join(
            self.packagedir, "conf-test-package-257-conffiles_1.deb")
        self.assertFalse(conffile_prompt(test_pkg, prefix=self.rootdir),
                         "conffile prompt detection incorrect")

    def test_will_not_prompt_because_of_conffile_removal(self):
        # no conffiles anymore in the pkg
        test_pkg = os.path.join(
            self.packagedir, "conf-test-package-no-conffiles-anymore_2.deb")
        self.assertFalse(conffile_prompt(test_pkg, prefix=self.rootdir),
                         "conffile prompt detection incorrect")

    def test_will_prompt_multiple(self):
        # multiple conffiles
        test_pkg = os.path.join(
            self.packagedir, "multiple-conffiles_2_all.deb")
        self.assertTrue(conffile_prompt(test_pkg, prefix=self.rootdir),
                        "conffile prompt detection incorrect")

    def test_will_prompt_for_new_conffile(self):
        # debian bug #673237, a package that was not a conffile now
        # becomes a conffile
        test_pkg = os.path.join(
            self.packagedir, "conf-test-package-new-conffile_1.deb")
        self.assertTrue(conffile_prompt(test_pkg, prefix=self.rootdir),
                        "conffile prompt detection incorrect")

    def test_xz_compression(self):
        test_pkg = os.path.join(self.packagedir, "conf-test-xz_1.0_all.deb")
        self.assertFalse(
            conffile_prompt(test_pkg, prefix=self.rootdir),
            "conffile prompt detection incorrect")


class DpkgConffileTestCase(TestBase):
    """
    This tests that the detection if dpkg will prompt at all works,
    i.e. if the user has decided to use a --force-conf{old,new} option
    """

    def setUp(self):
        TestBase.setUp(self)
        apt_pkg.config.clear("DPkg::Options")

    def test_no_dpkg_prompt_option(self):
        self.assertTrue(dpkg_conffile_prompt())

    def test_regression_lp1061498(self):
        apt_pkg.config.set("DPkg::Options::", "muup")
        self.assertTrue(dpkg_conffile_prompt())

    def test_dpkg_will_never_prompt(self):
        apt_pkg.config.set("DPkg::Options::", "--force-confold")
        self.assertFalse(dpkg_conffile_prompt())


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
