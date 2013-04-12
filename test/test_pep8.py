import glob
import os
import subprocess
import unittest


class PackagePep8TestCase(unittest.TestCase):

    def test_all_code(self):
        res = 0
        py_files = glob.glob(os.path.join(os.path.dirname(__file__), "*.py"))
        res += subprocess.call(["pep8", "--repeat", ] + py_files)
        self.assertEqual(res, 0)


if __name__ == "__main__":
    unittest.main()
