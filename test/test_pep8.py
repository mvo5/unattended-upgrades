#!/usr/bin/python3

import os
import subprocess
import unittest

# E126: I don't even know what its supposed to tell me :(
IGNORE = "E126,E265,E402,W503"


class PackagePep8TestCase(unittest.TestCase):

    def test_pep8_clean(self):
        top_src_dir = os.path.join(os.path.dirname(__file__), "..")
        targets = [
            top_src_dir,
            os.path.join(top_src_dir, "unattended-upgrade"),
            os.path.join(top_src_dir, "unattended-upgrade-shutdown"),
        ]
        # use max-line-length=88 for upcoming "black" compatibility
        try:
            self.assertEqual(subprocess.call(["pycodestyle",
                                              "--repeat",
                                              "--max-line-length=88",
                                              "--ignore=%s"
                                              % IGNORE]
                                             + targets),
                             0)
        except FileNotFoundError:
            self.assertEqual(subprocess.call(["pep8",
                                              "--repeat",
                                              "--max-line-length=88",
                                              "--ignore=%s" % IGNORE]
                                             + targets), 0)


if __name__ == "__main__":
    unittest.main()
