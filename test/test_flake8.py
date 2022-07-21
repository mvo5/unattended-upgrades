import os
import subprocess
import unittest


class TestFlake8Clean(unittest.TestCase):
    """ensure that the tree is flake8 clean"""

    def test_flake8_clean(self):
        top_src_dir = os.path.join(os.path.dirname(__file__), "..")
        targets = [
            top_src_dir,
            os.path.join(top_src_dir, "unattended-upgrade"),
            os.path.join(top_src_dir, "unattended-upgrade-shutdown"),
        ]
        subprocess.check_call(
            [
                "flake8",
                # use max-line-length=88 for upcoming "black" compatibility
                "--max-line-length=88",
                # E402 ignored because we need to import/config apt_pkg before
                #      importing unattended_upgrade
                # W503 ignored because some lines with binary operators are long
                "--ignore=E402,W503",
            ]
            + targets
        )


if __name__ == "__main__":
    unittest.main()
