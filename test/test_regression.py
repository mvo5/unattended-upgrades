#!/usr/bin/python3
# -*- coding: utf-8 -*-

import io
import os
import tempfile
import unittest

from mock import (
    Mock,
    patch,
)

from unattended_upgrade import do_install


class TestRegression(unittest.TestCase):

    @patch("unattended_upgrade.upgrade_normal")
    def test_do_install_fail_unicode_write(self, mock_upgrade_normal):
        """ test if the substitute function works """
        def _raise(*args):
            raise Exception("meepä")
        tmp = tempfile.TemporaryFile()
        old_stderr = os.dup(2)
        os.dup2(tmp.fileno(), 2)

        mock_upgrade_normal.side_effect = _raise
        logfile_dpkg = io.StringIO()
        # mock pkg
        pkg = Mock()
        pkg.name = "meep"
        # mock options
        options = Mock()
        options.minimal_upgrade_steps = False
        do_install(cache=Mock(), pkgs_to_upgrade=[pkg], blacklisted_pkgs=[],
                   options=options, logfile_dpkg=logfile_dpkg)
        # if there is no exception here, we are good
        os.dup2(old_stderr, 2)
        tmp.seek(0)
        self.assertEqual(tmp.read().decode("utf-8"), "Exception: meepä\n")

if __name__ == "__main__":
    #logging.basicConfig(level=logging.DEBUG)
    unittest.main()
