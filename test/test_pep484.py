#!/usr/bin/python3

import os
import subprocess
import unittest


def hasMyPy():
    try:
        subprocess.check_call(["mypy", "--version"])
    except Exception:
        return False
    return True


class PackagePep484TestCase(unittest.TestCase):
    @unittest.skipIf(not hasMyPy(), "no mypy available")
    # a source quality check does not belong in a test of the installed
    # package and a newer mypy can regress it at any time (Debian #1146138)
    @unittest.skipIf("AUTOPKGTEST_TMP" in os.environ,
                     "source check, skipped under autopkgtest")
    def test_pep484_clean(self):
        top_src_dir = os.path.join(os.path.dirname(__file__), "..")
        # FIXME: add pyi file for python-apt to get rid of the
        # --ignore-missing-imports
        # mypy only looks for its config in the current directory, and
        # only picks up *.py files from a directory: the main script is
        # found via the unattended_upgrade.py symlink, the shutdown
        # script has to be passed explicitly
        res = subprocess.call(["mypy", "--ignore-missing-imports",
                               "--config-file",
                               os.path.join(top_src_dir, "setup.cfg"),
                               top_src_dir,
                               os.path.join(top_src_dir,
                                            "unattended-upgrade-shutdown")])
        self.assertEqual(res, 0)


if __name__ == "__main__":
    unittest.main()
