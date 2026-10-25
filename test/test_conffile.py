#!/usr/bin/python3

import os
import logging
import unittest
from unittest.mock import patch

import apt_pkg

import unattended_upgrade
from unattended_upgrade import (
    conffile_prompt,
    dpkg_conffile_prompt,
)
from test.test_base import TestBase, MockOptions
from test.test_mail import make_mock_sendmail


class TestConffilePrompt(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.rootdir = self.make_fake_aptroot(
            template=os.path.join(self.testdir, "root.conffile"))
        self.packagedir = os.path.join(self.testdir, "packages")
        with open(os.path.join(
                self.rootdir, "etc/configuration-file"), "w") as fp:
            fp.write("""This is a configuration file,
dfasddfasdff
No really.
""")

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
        os.remove(os.path.join(self.rootdir, "etc/configuration-file"))
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


class TestConffilePromptRun(TestBase):
    """ A package held back because of a conffile prompt is an error even
        when nothing else is pending (GH: #336) """

    def setUp(self):
        TestBase.setUp(self)
        self.rootdir = self.make_fake_aptroot(
            template=os.path.join(self.testdir, "root.unused-deps"),
            fake_pkgs=[
                ("test-package", "1.0",
                 {"Depends": ["test-package-dependency"]}),
                ("test-package-dependency", "1.0", {}),
            ])
        # fake on_ac_power
        os.environ["PATH"] = (os.path.join(self.rootdir, "usr", "bin") + ":"
                              + os.environ["PATH"])
        self.mail_txt = os.path.join(self.tempdir, "mail.txt")
        with open(os.path.join(self.rootdir, "etc/apt/apt.conf"), "a") as fp:
            fp.write('Unattended-Upgrade::Mail "root";\n')
            fp.write('Unattended-Upgrade::MailReport "only-on-error";\n')
        self.addCleanup(apt_pkg.config.clear, "Unattended-Upgrade")
        for name, value in (
                ("MAIL_BINARY", "./no-mailx-binary-here"),
                ("SENDMAIL_BINARY", make_mock_sendmail(self.tempdir))):
            patcher = patch.object(unattended_upgrade, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_conffile_prompt_only(self):
        # the host apt config may disable conffile prompts via
        # DPkg::Options (e.g. --force-confold on the CI runners)
        with patch.object(unattended_upgrade, "dpkg_conffile_prompt",
                          return_value=True), \
                patch.object(unattended_upgrade, "conffile_prompt",
                             return_value=True):
            ret = unattended_upgrade.main(MockOptions(), rootdir=self.rootdir)
        self.assertEqual(ret, 1)
        # the package is still reported as kept back (used by the motd)
        with open(os.path.join(
                self.rootdir, unattended_upgrade.KEPT_PACKAGES_FILE)) as fp:
            self.assertEqual(fp.read().split(), ["test-package"])
        # and the admin is told about it with "only-on-error"
        with open(self.mail_txt) as fp:
            self.assertIn("test-package", fp.read())


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
