import glob
import os
import subprocess
import unittest


class TestPyflakesClean(unittest.TestCase):
    """ ensure that the tree is pyflakes clean """

    def test_pyflakes_clean(self):
        files = glob.glob(
            os.path.join(os.path.dirname(__file__), "..", "test", "*.py"))
        files.append(
            os.path.join(os.path.dirname(__file__), "unattended_upgrade.py"))
        self.assertEqual(subprocess.call(["pyflakes"] + files), 0)


if __name__ == "__main__":
    unittest.main()
