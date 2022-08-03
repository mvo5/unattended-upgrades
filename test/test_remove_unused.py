#!/usr/bin/python3

import os
import subprocess
import unittest

import apt_pkg
apt_pkg.config.set("Dir", os.path.join(os.path.dirname(__file__), "aptroot"))
import apt

from test.test_base import TestBase, MockOptions
import unattended_upgrade

apt.apt_pkg.config.set("APT::Architecture", "amd64")


class TestRemoveUnused(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.rootdir = self.make_fake_aptroot(
            template=os.path.join(self.testdir, "root.unused-deps"),
            fake_pkgs=[
                ("test-package", "1.0", {"Depends": ["test-package-dependency"]}),
                ("test-package-dependency", "1.0", {}),
                ("any-old-unused-modules", "1.0", {}),
                ("linux-image-4.05.0-1021-kvm", "1.21", {}),
                ("linux-image-4.05.0-1022-kvm", "1.22", {}),
                ("linux-image-4.05.0-1023-kvm", "1.23", {}),
                ("z-package", "1.0", {}),
                ("old-unused-dependency", "1.0", {}),
            ]
        )
        self.mock_distro("ubuntu", "lucid", "ubuntu 10.04")
        # FIXME: make this more elegant
        # fake on_ac_power
        os.environ["PATH"] = (os.path.join(self.rootdir, "usr", "bin") + ":"
                              + os.environ["PATH"])
        # pretend test-package-dependency is auto-installed
        extended_states = os.path.join(
            self.rootdir, "var", "lib", "apt", "extended_states")
        with open(extended_states, "w") as f:
            f.write("""
Package: old-unused-dependency
Architecture: all
Auto-Installed: 1

Package: test-package-dependency
Architecture: all
Auto-Installed: 1

Package: any-old-unused-modules
Architecture: all
Auto-Installed: 1

Package: linux-image-4.05.0-1021-kvm
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

    def test_remove_unused_dependencies(self):
        apt.apt_pkg.config.clear("APT::VersionedKernelPackages")
        apt_conf = os.path.join(self.rootdir, "etc", "apt", "apt.conf")
        with open(apt_conf, "w") as fp:
            fp.write("""
Unattended-Upgrade::MinimalSteps "false";
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
            # both the new and the old unused dependency are removed
            needle = "Packages that were successfully auto-removed: "\
                     "any-old-unused-modules linux-image-4.05.0-1021-kvm "\
                     "old-unused-dependency test-package-dependency\n"
            haystack = f.read()
            self.assertTrue(needle in haystack,
                            "Can not find '%s' in '%s'" % (needle, haystack))

    def test_remove_unused_dependencies_new_unused_only(self):
        apt.apt_pkg.config.set("APT::VersionedKernelPackages::", "linux-image")
        apt.apt_pkg.config.set("APT::VersionedKernelPackages::", ".*-modules")
        apt.apt_pkg.config.set("APT::VersionedKernelPackages::",
                               "linux-headers")
        apt_conf = os.path.join(self.rootdir, "etc", "apt", "apt.conf")
        with open(apt_conf, "w") as fp:
            fp.write("""
Unattended-Upgrade::Keep-Debs-After-Install "true";
Unattended-Upgrade::Allowed-Origins {
    "Ubuntu:lucid-security";
};
Unattended-Upgrade::Remove-New-Unused-Dependencies "true";
Unattended-Upgrade::Skip-Updates-On-Metered-Connections "false";
""")
        options = MockOptions()
        unattended_upgrade.main(options, rootdir=self.rootdir)
        with open(self.log) as f:
            # ensure its only exactly one package that is removed
            needle_kernel_bad = "Removing unused kernel packages: "\
                                "any-old-unused-modules\n"
            needle_kernel_good = "Removing unused kernel packages: "\
                                 "linux-image-4.05.0-1021-kvm\n"
            needle = "Packages that were successfully auto-removed: "\
                     "test-package-dependency\n"
            haystack = f.read()
            self.assertTrue(needle in haystack,
                            "Can not find '%s' in '%s'" % (needle, haystack))
            self.assertTrue(needle_kernel_good in haystack,
                            "Can not find '%s' in '%s'" % (needle_kernel_good,
                                                           haystack))
            self.assertFalse(needle_kernel_bad in haystack,
                             "Found '%s' in '%s'" % (needle_kernel_bad,
                                                     haystack))

    def test_remove_valid(self):
        cache = unattended_upgrade.UnattendedUpgradesCache(
            rootdir=self.rootdir)
        auto_removable = unattended_upgrade.get_auto_removable(cache)
        print(auto_removable)
        cache["old-unused-dependency"].mark_delete()
        res = unattended_upgrade.is_autoremove_valid(
            cache, "test-package-dependency", auto_removable)
        self.assertTrue(res, "Simple autoremoval set is not valid")

        res = unattended_upgrade.is_autoremove_valid(
            cache, "test-package-dependency", set())
        self.assertFalse(res, "Autoremoving non-autoremovable package")

        cache["forbidden-dependency"].mark_install()
        auto_removable.add("forbidden-dependency")
        res = unattended_upgrade.is_autoremove_valid(
            cache, "test-package-dependency", auto_removable)
        self.assertFalse(
            res, "Package set to reinstall in cache is reinstalled")


if __name__ == "__main__":
    # do not setup logging in here or the test will break
    unittest.main()
