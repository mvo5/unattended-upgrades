import os
import subprocess
import unittest

class TestPyflakesClean(unittest.TestCase):
    """ ensure that the tree is pyflakes clean """

    def test_pyflakes_clean(self):
        target = os.path.join(os.path.dirname(__file__), "..", "unattended-upgrade")
        self.assertEqual(subprocess.call(["pyflakes", target]), 0)


if __name__ == "__main__":
    unittest.main()
