#!/usr/bin/python3

from datetime import date
import unittest
from mock import patch

import apt

import unattended_upgrade


class TestUpdateDays(unittest.TestCase):

    def setUp(self):
        apt.apt_pkg.config.clear("Unattended-Upgrade::Update-Days")

    def test_update_days_no_patch_days_always_runs_uu(self):
        apt.apt_pkg.config.clear("Unattended-Upgrade::Update-Days")
        self.assertTrue(unattended_upgrade.is_update_day())

    @patch("unattended_upgrade.date")
    def test_update_days_by_name(self, mock_date):
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        apt.apt_pkg.config.set("Unattended-Upgrade::Update-Days::", "Wed")
        apt.apt_pkg.config.set("Unattended-Upgrade::Update-Days::", "Sun")
        # that was a Wed
        mock_date.today.return_value = date(2007, 8, 22)
        self.assertTrue(unattended_upgrade.is_update_day())
        # that was a Th
        mock_date.today.return_value = date(2007, 8, 2)
        self.assertFalse(unattended_upgrade.is_update_day())
        # that was a Sun
        mock_date.today.return_value = date(2007, 7, 29)
        self.assertTrue(unattended_upgrade.is_update_day())

    @patch("unattended_upgrade.date")
    def test_update_days_by_number(self, mock_date):
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        # 0: Sun, 1: Mon, ...
        apt.apt_pkg.config.set("Unattended-Upgrade::Update-Days::", "3")
        apt.apt_pkg.config.set("Unattended-Upgrade::Update-Days::", "0")
        # that was a Wed
        mock_date.today.return_value = date(2007, 8, 22)
        self.assertTrue(unattended_upgrade.is_update_day())
        # that was a Thu
        mock_date.today.return_value = date(2007, 8, 2)
        self.assertFalse(unattended_upgrade.is_update_day())
        # that was a Sun
        mock_date.today.return_value = date(2007, 7, 29)
        self.assertTrue(unattended_upgrade.is_update_day())


if __name__ == "__main__":
    unittest.main()
