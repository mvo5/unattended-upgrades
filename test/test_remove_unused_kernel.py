#!/usr/bin/python3

import os
import subprocess
import unittest

import apt

from test.test_base import TestBase, MockOptions
import unattended_upgrade

apt.apt_pkg.config.set("APT::Architecture", "amd64")


class TestRemoveUnusedKernel(TestBase):
    """Regression test for GH #395.

    Debian trixie+ kernels carry the Debian revision in the package name
    (e.g. linux-image-6.12.90+deb13-amd64).  Make sure such an auto-removable
    kernel is recognized as a versioned kernel package and handled through the
    dedicated kernel-removal path instead of slipping through unclassified.
    """

    def setUp(self):
        TestBase.setUp(self)
        self.rootdir = self.make_fake_aptroot(
            template=os.path.join(self.testdir, "root.unused-deps"),
            fake_pkgs=[
                # the two newest kernels are kept by apt's kernel protection
                ("linux-image-6.12.91+deb13-amd64", "6.12.91", {}),
                ("linux-image-6.12.90+deb13-amd64", "6.12.90", {}),
                # the oldest, auto-installed and now unused kernel -> removable
                ("linux-image-6.12.88+deb13-amd64", "6.12.88", {}),
            ]
        )
        # FIXME: make this more elegant
        # fake on_ac_power
        os.environ["PATH"] = (os.path.join(self.rootdir, "usr", "bin") + ":"
                              + os.environ["PATH"])
        # pretend the old kernel was pulled in automatically
        extended_states = os.path.join(
            self.rootdir, "var", "lib", "apt", "extended_states")
        with open(extended_states, "w") as f:
            f.write("""
Package: linux-image-6.12.88+deb13-amd64
Architecture: all
Auto-Installed: 1
""")
        # clean log
        self.log = os.path.join(
            self.rootdir, "var", "log", "unattended-upgrades",
            "unattended-upgrades.log")
        if not os.path.exists(os.path.dirname(self.log)):
            os.makedirs(os.path.dirname(self.log))
        with open(self.log, "w"):
            pass
        # clean cache
        subprocess.check_call(
            ["rm", "-f",
             os.path.join(self.rootdir, "var", "cache", "apt", "*.bin")])

    def test_remove_unused_debian_versioned_kernel(self):
        apt.apt_pkg.config.clear("APT::VersionedKernelPackages")
        apt.apt_pkg.config.set("APT::VersionedKernelPackages::", "linux-image")
        apt_conf = os.path.join(self.rootdir, "etc", "apt", "apt.conf")
        with open(apt_conf, "w") as fp:
            fp.write("""
Unattended-Upgrade::Keep-Debs-After-Install "true";
Unattended-Upgrade::Allowed-Origins {
    "Ubuntu:lucid-security";
};
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Skip-Updates-On-Metered-Connections "false";
""")
        options = MockOptions()
        unattended_upgrade.main(options, rootdir=self.rootdir)
        with open(self.log) as f:
            haystack = f.read()
        # the +deb13 kernel must be recognized as a kernel package and removed
        # through the dedicated kernel-removal path (before the GH #395 fix it
        # was not matched by the versioned-kernel regexp at all)
        needle = "Removing unused kernel packages: "\
                 "linux-image-6.12.88+deb13-amd64\n"
        self.assertIn(needle, haystack,
                      "Can not find '%s' in '%s'" % (needle, haystack))
        # the newest kernel must not be removed
        self.assertNotIn("linux-image-6.12.90+deb13-amd64", haystack.replace(
            needle, ""))


if __name__ == "__main__":
    unittest.main()
