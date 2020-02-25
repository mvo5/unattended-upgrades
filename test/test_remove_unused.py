#!/usr/bin/python3

import os
import subprocess
import unittest

import apt_pkg
apt_pkg.config.set("Dir", "./aptroot")
import apt

import unattended_upgrade

apt.apt_pkg.config.set("APT::Architecture", "amd64")


class MockOptions(object):
    debug = True
    verbose = False
    download_only = False
    dry_run = False
    apt_debug = False
    minimal_upgrade_steps = True


class TestRemoveUnused(unittest.TestCase):

    def setUp(self):
        self.rootdir = os.path.abspath("./root.unused-deps")
        # fake on_ac_power
        os.environ["PATH"] = (os.path.join(self.rootdir, "usr", "bin") + ":"
                              + os.environ["PATH"])
        dpkg_status = os.path.abspath(
            os.path.join(self.rootdir, "var", "lib", "dpkg", "status"))
        # fake dpkg status
        with open(dpkg_status, "w") as fp:
            fp.write("""Package: test-package
Status: install ok installed
Architecture: all
Version: 1.0.test.pkg
Depends: test-package-dependency

Package: test-package-dependency
Status: install ok installed
Architecture: all
Version: 1.0

Package: any-old-unused-modules
Status: install ok installed
Architecture: all
Version: 1.0

Package: linux-image-4.05.0-1021-kvm
Status: install ok installed
Architecture: all
Version: 1.0

Package: z-package
Status: install ok installed
Architecture: all
Version: 1.0

Package: old-unused-dependency
Status: install ok installed
Architecture: all
Version: 1.0
""")
        apt.apt_pkg.config.set("Dir::State::status", dpkg_status)
        apt.apt_pkg.config.clear("DPkg::Pre-Invoke")
        apt.apt_pkg.config.clear("DPkg::Post-Invoke")
        apt.apt_pkg.config.set("Debug::NoLocking", "true")
        # we don't really run dpkg
        apt.apt_pkg.config.set(
            "Dir::Bin::Dpkg", os.path.join(self.rootdir, "bin", "dpkg"))
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
        unattended_upgrade.DISTRO_DESC = "Ubuntu 10.04"
        unattended_upgrade.LOCK_FILE = "./u-u.lock"
        unattended_upgrade.main(
            options, rootdir="./root.unused-deps")
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
        unattended_upgrade.DISTRO_DESC = "Ubuntu 10.04"
        unattended_upgrade.LOCK_FILE = "./u-u.lock"
        unattended_upgrade.main(
            options, rootdir="./root.unused-deps")
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
