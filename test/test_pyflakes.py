import os
import subprocess
import unittest


class TestPyflakesClean(unittest.TestCase):
    """ ensure that the tree is pyflakes clean """

    def test_pyflakes_clean(self):
        path = os.path.join(
            os.path.dirname(__file__), "unattended_upgrade.py")
        self.assertEqual(subprocess.call(["pyflakes",  path]), 0)


if __name__ == "__main__":
    unittest.main()
