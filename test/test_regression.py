#!/usr/bin/python3
# -*- coding: utf-8 -*-

import apt_pkg
apt_pkg.config.set("Dir", "./aptroot")
import io
import os
import sys
import tempfile
import unittest

from mock import (
    Mock,
    patch,
)

from unattended_upgrade import do_install


class MockCache:
    def __iter__(self):
        raise StopIteration

    def get_changes(self):
        return []


class TestRegression(unittest.TestCase):

    @unittest.skipIf(sys.version_info[0] != 3, "only works on py3")
    @patch("unattended_upgrade.upgrade_normal")
    def test_do_install_fail_unicode_write(self, mock_upgrade_normal):
        """ test if the substitute function works """
        def _raise(*args):
            raise Exception("meepä")
        tmp = tempfile.TemporaryFile()
        old_stderr = os.dup(2)
        # comment this line if you need to debug stuff
        os.dup2(tmp.fileno(), 2)

        mock_upgrade_normal.side_effect = _raise
        logfile_dpkg = io.StringIO()
        # mock pkg
        pkg = Mock()
        pkg.name = "meep"
        # mock options
        options = Mock()
        options.minimal_upgrade_steps = False
        apt_pkg.config.set("Unattended-Upgrade::MinimalSteps", "False")
        do_install(cache=MockCache(), pkgs_to_upgrade=[pkg],
                   blacklisted_pkgs=[],
                   whitelisted_pkgs=[], options=options,
                   logfile_dpkg=logfile_dpkg)
        # if there is no exception here, we are good
        os.dup2(old_stderr, 2)
        tmp.seek(0)
        content = tmp.read().decode("utf-8").splitlines()
        tmp.close()
        self.assertEqual(content[-1], "Exception: meepä")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
