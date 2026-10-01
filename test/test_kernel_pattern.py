#!/usr/bin/python3

import re
import unittest

import apt_pkg

from unattended_upgrade import (KERNEL_VERSION_REGEXP,
                                versioned_kernel_pkgs_regexp)


class TestKernelPattern(unittest.TestCase):

    def setUp(self):
        apt_pkg.init_config()
        apt_pkg.config.clear("APT::VersionedKernelPackages")
        for p in ("linux-image", "linux-headers", "linux-image-extra",
                  "linux-modules", "linux-modules-extra"):
            apt_pkg.config.set("APT::VersionedKernelPackages::", p)

    # package names that must be recognized as versioned kernel packages
    SHOULD_MATCH = [
        # classic Debian "X.Y.Z-<ABI>-<flavour>"
        "linux-image-6.1.0-9-amd64",
        # Ubuntu "X.Y.Z-<ABI>-<flavour>"
        "linux-image-5.15.0-1021-kvm",
        # Debian trixie+ "X.Y.Z+debN-<flavour>" (GH #395)
        "linux-image-6.12.88+deb13-amd64",
        "linux-image-6.12.90+deb13-amd64",
        "linux-image-6.12.90+deb13.1-amd64",
        "linux-image-6.12.74+deb13+1-arm64",
        # ... including the assorted flavours/variants
        "linux-image-6.12.90+deb13-cloud-amd64",
        "linux-image-6.12.90+deb13-rt-amd64",
        "linux-image-6.12.90+deb13.1-amd64-unsigned",
        "linux-image-6.12.73+deb13-arm64-16k",
        "linux-headers-6.12.90+deb13-amd64",
        "linux-modules-6.12.90+deb13-amd64",
    ]

    # package names that must NOT be treated as versioned kernel packages
    SHOULD_NOT_MATCH = [
        "linux-image-amd64",
        "linux-image-arm64",
        "linux-image-cloud-amd64",
        "linux-image-rt-amd64",
        "linux-image-generic",
        "linux-headers-amd64",
    ]

    def test_versioned_kernel_pkgs_regexp(self):
        regexp = versioned_kernel_pkgs_regexp()
        for name in self.SHOULD_MATCH:
            self.assertTrue(regexp.match(name),
                            "%s should match %s" % (name, regexp.pattern))
        for name in self.SHOULD_NOT_MATCH:
            self.assertFalse(regexp.match(name),
                             "%s should not match %s" % (name, regexp.pattern))

    def test_kernel_version_regexp_strips_flavour(self):
        # KERNEL_VERSION_REGEXP is used to derive the flavour-independent
        # version from "uname -r" for the running-kernel protection
        cases = {
            "6.1.0-9-amd64": "6.1.0-9",
            "5.15.0-1021-kvm": "5.15.0-1021",
            "6.12.90+deb13-amd64": "6.12.90+deb13",
            "6.12.90+deb13.1-amd64": "6.12.90+deb13.1",
            "6.12.74+deb13+1-rt-amd64": "6.12.74+deb13+1",
        }
        for uname, expected in cases.items():
            match = re.match(KERNEL_VERSION_REGEXP, uname)
            self.assertIsNotNone(match, "no version found in %s" % uname)
            self.assertEqual(match[0], expected)


if __name__ == "__main__":
    unittest.main()
