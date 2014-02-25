import os
import subprocess
import unittest


class PackagePep8TestCase(unittest.TestCase):

    def test_pep8_clean(self):
        top_src_dir = os.path.join(os.path.dirname(__file__), "..")
        targets = [
            top_src_dir,
            os.path.join(top_src_dir, "unattended-upgrade"),
            os.path.join(top_src_dir, "unattended-upgrade-shutdown"),
            ]
        self.assertEqual(subprocess.call(["pep8", "--repeat", ] + targets), 0)


if __name__ == "__main__":
    unittest.main()
