#!/usr/bin/python

import apt_pkg
import logging
import unittest
import os

from mock import (
    patch,
)

import unattended_upgrade


class RebootTestCase(unittest.TestCase):

    def setUp(self):
        # create reboot required file
        REBOOT_REQUIRED_FILE = "./reboot-required"
        with open(REBOOT_REQUIRED_FILE, "w"):
            pass
        self.addCleanup(lambda: os.remove(REBOOT_REQUIRED_FILE))
        unattended_upgrade.REBOOT_REQUIRED_FILE = REBOOT_REQUIRED_FILE
        # enable automatic-reboot
        apt_pkg.config.set("Unattended-Upgrade::Automatic-Reboot", "1")
        apt_pkg.config.set("Unattended-Upgrade::Automatic-Reboot-WithUsers", "1")

    @patch("subprocess.call")
    def test_reboot_now(self, mock_call):
        unattended_upgrade.reboot_if_requested_and_needed()
        mock_call.assert_called_with(["/sbin/shutdown", "-r", "now"])

    @patch("subprocess.call")
    def test_reboot_time(self, mock_call):
        apt_pkg.config.set(
            "Unattended-Upgrade::Automatic-Reboot-Time", "03:00")
        unattended_upgrade.reboot_if_requested_and_needed()
        mock_call.assert_called_with(["/sbin/shutdown", "-r", "03:00"])

    @patch("subprocess.call")
    def test_reboot_withoutusers(self, mock_call):
        apt_pkg.config.set(
            "Unattended-Upgrade::Automatic-Reboot-WithUsers", "0")
        apt_pkg.config.set(
            "Unattended-Upgrade::Automatic-Reboot-Time", "04:00")
        # some pgm that allways output nothing
        unattended_upgrade.USERS = "/bin/true"
        unattended_upgrade.reboot_if_requested_and_needed()
        mock_call.assert_called_with(["/sbin/shutdown", "-r", "04:00"])

    @patch("subprocess.call")
    def test_reboot_withusers(self, mock_call):
        apt_pkg.config.set(
            "Unattended-Upgrade::Automatic-Reboot-WithUsers", "0")
        # some pgm that allways output a word
        unattended_upgrade.USERS = "/bin/uname"
        unattended_upgrade.reboot_if_requested_and_needed()
        assert not mock_call.called, "couldn't detect active sessions"

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
