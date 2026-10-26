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
        res = subprocess.call(["mypy", "--ignore-missing-imports", top_src_dir])
        self.assertEqual(res, 0)


if __name__ == "__main__":
    unittest.main()
