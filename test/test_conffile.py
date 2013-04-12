#!/usr/bin/python3

import apt_pkg
import logging
import unittest

from unattended_upgrade import (
    conffile_prompt,
    dpkg_conffile_prompt,
)


class ConffilePromptTestCase(unittest.TestCase):

    def setUp(self):
        apt_pkg.config.set("Dir::State::status",
                           "./root.conffile/var/lib/dpkg/status")

    def test_will_prompt(self):
        # conf-test 0.9 is installed, 1.1 gets installed
        # they both have different config files
        test_pkg = "./packages/conf-test-package_1.1.deb"
        self.assertTrue(conffile_prompt(test_pkg, prefix="./root.conffile"),
                        "conffile prompt detection incorrect")

    def test_will_not_prompt(self):
        # conf-test 0.9 is installed, 1.0 gets installed
        # they both have the same config files
        test_pkg = "./packages/conf-test-package_1.0.deb"
        self.assertFalse(conffile_prompt(test_pkg, prefix="./root.conffile"),
                         "conffile prompt detection incorrect")

    def test_with_many_entries(self):
        # ensure we don't crash when encountering a conffile with overly
        # many entries
        test_pkg = "./packages/conf-test-package-257-conffiles_1.deb"
        self.assertFalse(conffile_prompt(test_pkg, prefix="./root.conffile"),
                         "conffile prompt detection incorrect")

    def test_will_not_prompt_because_of_conffile_removal(self):
        # no conffiles anymore in the pkg
        test_pkg = "./packages/conf-test-package-no-conffiles-anymore_2.deb"
        self.assertFalse(conffile_prompt(test_pkg, prefix="./root.conffile"),
                         "conffile prompt detection incorrect")

    def test_will_prompt_multiple(self):
        # multiple conffiles
        test_pkg = "./packages/multiple-conffiles_2_all.deb"
        self.assertTrue(conffile_prompt(test_pkg, prefix="./root.conffile"),
                        "conffile prompt detection incorrect")

    def test_will_prompt_for_new_conffile(self):
        # debian bug #673237, a package that was not a conffile now
        # becomes a conffile
        test_pkg = "./packages/conf-test-package-new-conffile_1.deb"
        self.assertTrue(conffile_prompt(test_pkg, prefix="./root.conffile"),
                        "conffile prompt detection incorrect")

    def test_xz_compression(self):
        test_pkg = "./packages/conf-test-xz_1.0_all.deb"
        self.assertFalse(
            conffile_prompt(test_pkg, prefix="./root.conffile"),
            "conffile prompt detection incorrect")


class DpkgConffileTestCase(unittest.TestCase):
    """
    This tests that the detection if dpkg will prompt at all works,
    i.e. if the user has decided to use a --force-conf{old,new} option
    """

    def setUp(self):
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
