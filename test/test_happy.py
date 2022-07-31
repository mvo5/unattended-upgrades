#!/usr/bin/python3

import os
from mock import patch

import apt

import unattended_upgrade
from test.test_base import TestBase, MockOptions

apt.apt_pkg.config.set("APT::Architecture", "amd64")


class TestHappy(TestBase):
    """ Test the unattended-upgrades happy path"""

    def setUp(self):
        TestBase.setUp(self)
        self.rootdir = self.make_fake_aptroot(
            template=os.path.join(self.testdir, "root.unused-deps"),
            fake_pkgs=[("test-package", "1.0", {})],
        )
        self.mock_distro("ubuntu", "lucid", "Ubuntu 10.04")
        # FIXME: mock via TestBase and subprocess.call() magic mocking?
        # fake on_ac_power
        os.environ["PATH"] = (
            os.path.join(self.rootdir, "usr", "bin") + ":" + os.environ["PATH"]
        )
        # logs
        self.log = os.path.join(
            self.rootdir, "var", "log", "unattended-upgrades", "unattended-upgrades.log"
        )
        self.dpkg_log = os.path.join(
            self.rootdir,
            "var",
            "log",
            "unattended-upgrades",
            "unattended-upgrades-dpkg.log",
        )

    def test_simple_and_happy(self):
        """ Ensure a single package is upgraded"""
        options = MockOptions()
        unattended_upgrade.main(options, rootdir=self.rootdir)
        with open(self.log) as fp:
            # XXX: assertContains?
            self.assertTrue("Packages that will be upgraded: test-package" in fp.read())
        # with open(self.dpkg_log) as fp:
        #    self.assertRegex(
        #        fp.read(), r"(?sm)usr/bin/dpkg'.*'--unpack'.*test-package_2.0_all.deb"
        #    )

    @patch("unattended_upgrade.try_nice")
    def test_simple_uses_context_manager(self, mock_try_nice):
        options = MockOptions()
        unattended_upgrade.main(options, rootdir=self.rootdir)
        mock_try_nice.assert_called_once_with(20)
