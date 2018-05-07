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
    def test_pep484_clean(self):
        top_src_dir = os.path.join(os.path.dirname(__file__), "..")
        # FIXME: add pyi file for python-apt to get rid of the
        # --ignore-missing-imports
        self.assertEqual(
            subprocess.call(
                ["mypy", "--ignore-missing-imports",
                 "--no-strict-optional", top_src_dir]), 0)


if __name__ == "__main__":
    unittest.main()
