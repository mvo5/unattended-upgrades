#!/usr/bin/python3

import apt_pkg
import logging
import re
import subprocess
import unittest

from unattended_upgrade import (running_kernel_pkgs_regexp,
                                versioned_kernel_pkgs_regexp)


class TestKernelPatterns(unittest.TestCase):

    def test_versioned(self):
        """kernel package patterns should cover versioned packages"""
        versioned_regexp = versioned_kernel_pkgs_regexp()
        running_regexp = running_kernel_pkgs_regexp()
        running_kernel_version = subprocess.check_output(
            ["uname", "-r"], universal_newlines=True).rstrip()
        running_escaped_regexp = ".*" + re.escape(running_kernel_version)
        try:
            running_noflavor_regexp = "linux.*-" + re.escape(
                re.match("[1-9][0-9]*\\.[0-9]+\\.[0-9]+-[0-9]+",
                         running_kernel_version)[0])
        except TypeError:
            self.skipTest("Could not find flavor of running kernel. It may "
                          "not be a packaged one.")

        cache = apt_pkg.Cache(None)
        not_matched = set()
        for pkg in cache.packages:
            pkg_name = pkg.name
            if re.match(running_noflavor_regexp, pkg_name):
                if re.match(running_escaped_regexp, pkg_name) \
                   and not re.match(running_regexp, pkg_name):
                    logging.debug("Package %s matched %s and %s, "
                                  "but did not match %s",
                                  pkg_name, running_noflavor_regexp,
                                  running_escaped_regexp,
                                  running_regexp)
                    not_matched.add(pkg_name)
                    continue
                if not re.match(versioned_regexp, pkg_name):
                    logging.debug("Package %s matched %s, "
                                  "but did not match %s",
                                  pkg_name, running_noflavor_regexp,
                                  versioned_regexp)
                    not_matched.add(pkg.name)

        self.assertTrue(not not_matched,
                        "kernel packages not matched: %s"
                        % " ".join(not_matched))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
