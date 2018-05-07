#!/usr/bin/python3

import datetime
import logging
import os
import unittest

import apt_pkg
apt_pkg.config.set("Dir", "./aptroot")

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
        apt_pkg.config.set(
            "Unattended-Upgrade::Automatic-Reboot-WithUsers", "1")

    @patch("subprocess.call")
    def test_no_reboot_done_because_no_stamp(self, mock_call):
        unattended_upgrade.REBOOT_REQUIRED_FILE = "/no/such/file/or/directory"
        unattended_upgrade.reboot_if_requested_and_needed()
        self.assertEqual(mock_call.called, False)

    @patch("subprocess.call")
    def test_no_reboot_done_because_no_option(self, mock_call):
        apt_pkg.config.set("Unattended-Upgrade::Automatic-Reboot", "0")
        unattended_upgrade.reboot_if_requested_and_needed()
        self.assertEqual(mock_call.called, False)

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
        """Ensure that a reboot happens when no users are logged in"""
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
        """Ensure that a reboot does not happen if a user is logged in"""
        apt_pkg.config.set(
            "Unattended-Upgrade::Automatic-Reboot-WithUsers", "0")
        # some pgm that allways output a word
        unattended_upgrade.USERS = "/bin/uname"
        unattended_upgrade.reboot_if_requested_and_needed()
        self.assertEqual(
            mock_call.called, False,
            "Called '%s' when nothing should have "
            "happen" % mock_call.call_args_list)

    @patch("subprocess.call")
    def test_logged_in_users(self, mock_call):
        # some pgm that allways output a word
        unattended_upgrade.USERS = ["/bin/date", "+%Y %Y %Y"]
        users = unattended_upgrade.logged_in_users()
        today = datetime.date.today()
        self.assertEqual(users, set([today.strftime("%Y")]))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
