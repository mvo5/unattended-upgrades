#!/usr/bin/python

import apt_pkg
import logging
import unittest
import os

from mock import (
   patch,
   Mock,
)

import unattended_upgrade

class ConffilePromptTestCase(unittest.TestCase):

    @patch("subprocess.call")
    def test_reboot_now(self, mock_call):
        # setup
        fake_fd = 0
        REBOOT_REQUIRED_FILE = "./reboot-required"
        with open(REBOOT_REQUIRED_FILE, "w") as f:
            pass
        self.addCleanup(lambda: os.remove(REBOOT_REQUIRED_FILE))
        apt_pkg.config.set("Unattended-Upgrade::Automatic-Reboot", "1")
        unattended_upgrade.REBOOT_REQUIRED_FILE = REBOOT_REQUIRED_FILE
        # run 
        unattended_upgrade.reboot_if_requested_and_needed(0)
        # check
        mock_call.assert_called_with(["/sbin/reboot"])
        


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
