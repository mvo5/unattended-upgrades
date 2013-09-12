import os
import subprocess
import unittest


class TestPyflakesClean(unittest.TestCase):
    """ ensure that the tree is pyflakes clean """

    def test_pyflakes_clean(self):
        top_src_dir = os.path.join(os.path.dirname(__file__), "..")
        targets = [
            top_src_dir,
            os.path.join(top_src_dir, "unattended-upgrade"),
            os.path.join(top_src_dir, "unattended-upgrade-shutdown"),
            ]
        self.assertEqual(subprocess.call(["pyflakes", ] + targets), 0)


if __name__ == "__main__":
    unittest.main()
