#!/usr/bin/python3

import os
import unittest

from unittest.mock import patch

import apt_pkg

from test.test_base import MockOptions, TestBase

import unattended_upgrade


class TestOnBattery(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.rootdir = self.make_fake_aptroot(
            template=os.path.join(self.testdir, "root.on-battery"))
        # FIXME: make this more elegant
        # fake on_ac_power
        os.environ["PATH"] = (os.path.join(self.rootdir, "usr", "bin") + ":"
                              + os.environ["PATH"])
        self.log = os.path.join(
            self.rootdir, "var", "log", "unattended-upgrades",
            "unattended-upgrades.log")

    def test_on_battery(self):
        self.make_power_supply("BAT0", "Battery", capacity=20)
        # run it
        options = MockOptions()
        with patch.object(unattended_upgrade, "POWER_SUPPLY_DIR",
                          os.path.join(self.tempdir, "power_supply")):
            ret = unattended_upgrade.main(options, rootdir=self.rootdir)
        self.assertEqual(ret, 1)
        # read the log to see what happend
        with open(self.log) as f:
            needle = "System is on battery power, stopping"
            haystack = f.read()
            self.assertTrue(needle in haystack,
                            "Can not find '%s' in '%s'" % (needle, haystack))

    def make_power_supply(self, name, supply_type, capacity=None,
                          scope=None, present=None):
        supply = os.path.join(self.tempdir, "power_supply", name)
        os.makedirs(supply)
        with open(os.path.join(supply, "type"), "w") as f:
            f.write(supply_type + "\n")
        if capacity is not None:
            with open(os.path.join(supply, "capacity"), "w") as f:
                f.write("%d\n" % capacity)
        if scope is not None:
            with open(os.path.join(supply, "scope"), "w") as f:
                f.write(scope + "\n")
        if present is not None:
            with open(os.path.join(supply, "present"), "w") as f:
                f.write("%d\n" % present)

    def should_stop(self, min_battery_level=None, only_on_ac_power=None):
        for key, value in (
                ("Unattended-Upgrade::MinBatteryLevel", min_battery_level),
                ("Unattended-Upgrade::OnlyOnACPower", only_on_ac_power)):
            apt_pkg.config.clear(key)
            if value is not None:
                apt_pkg.config.set(key, value)
        apt_pkg.config.set(
            "Unattended-Upgrade::Skip-Updates-On-Metered-Connections",
            "false")
        with patch.object(unattended_upgrade, "POWER_SUPPLY_DIR",
                          os.path.join(self.tempdir, "power_supply")), \
                patch.object(unattended_upgrade, "logged_msgs", set()):
            return unattended_upgrade.should_stop()

    def test_min_battery_level(self):
        self.make_power_supply("ADP1", "Mains")
        self.make_power_supply("BAT0", "Battery", capacity=60)
        self.assertFalse(self.should_stop("50"))
        self.assertFalse(self.should_stop("60"))
        self.assertTrue(self.should_stop("61"))
        self.assertTrue(self.should_stop("100"))
        self.assertFalse(self.should_stop("0"))
        self.assertTrue(self.should_stop("ac-only"))
        # empty means unset
        self.assertFalse(self.should_stop(""))
        self.assertTrue(self.should_stop("", only_on_ac_power="true"))

    def test_min_battery_level_default(self):
        self.make_power_supply("BAT0", "Battery", capacity=40)
        self.assertFalse(self.should_stop())

    def test_min_battery_level_default_below(self):
        self.make_power_supply("BAT0", "Battery", capacity=39)
        self.assertTrue(self.should_stop())

    def test_only_on_ac_power(self):
        self.make_power_supply("BAT0", "Battery", capacity=60)
        self.assertTrue(self.should_stop(only_on_ac_power="true"))
        self.assertTrue(self.should_stop(only_on_ac_power="1"))
        self.assertTrue(self.should_stop(only_on_ac_power="yes"))
        self.assertFalse(self.should_stop(only_on_ac_power="false"))
        self.assertFalse(self.should_stop(only_on_ac_power="0"))
        self.assertFalse(self.should_stop(only_on_ac_power="no"))
        # percentages are for MinBatteryLevel only
        self.assertTrue(self.should_stop(only_on_ac_power="50"))

    def test_min_battery_level_overrides_only_on_ac_power(self):
        self.make_power_supply("BAT0", "Battery", capacity=60)
        with self.assertLogs(level="WARNING") as logs:
            self.assertFalse(self.should_stop("50", only_on_ac_power="true"))
        self.assertIn("ignoring OnlyOnACPower", logs.output[0])
        self.assertTrue(self.should_stop("ac-only", only_on_ac_power="false"))

    def test_min_battery_level_on_ac(self):
        self.make_power_supply("BAT0", "Battery", capacity=10)
        # fake on_ac_power reporting AC
        on_ac = os.path.join(self.testdir, "root.unused-deps", "usr", "bin")
        with patch.dict(os.environ,
                        {"PATH": on_ac + ":" + os.environ["PATH"]}):
            self.assertFalse(self.should_stop("50"))
            self.assertFalse(self.should_stop("ac-only"))
            self.assertFalse(self.should_stop())

    def test_min_battery_level_averages_batteries(self):
        self.make_power_supply("BAT0", "Battery", capacity=20)
        self.make_power_supply("BAT1", "Battery", capacity=80)
        self.assertFalse(self.should_stop("50"))
        self.assertTrue(self.should_stop("51"))

    def test_min_battery_level_ignores_peripherals(self):
        self.make_power_supply("BAT0", "Battery", capacity=20)
        self.make_power_supply("hidpp_battery_0", "Battery", capacity=100,
                               scope="Device")
        self.assertTrue(self.should_stop("50"))

    def test_min_battery_level_unknown_level(self):
        self.make_power_supply("BAT0", "Battery")
        self.assertTrue(self.should_stop("50"))

    def test_min_battery_level_one_unknown_level(self):
        self.make_power_supply("BAT0", "Battery", capacity=80)
        self.make_power_supply("BAT1", "Battery")
        self.assertTrue(self.should_stop("50"))

    def test_min_battery_level_ignores_empty_bays(self):
        self.make_power_supply("BAT0", "Battery", capacity=60)
        # absent batteries have no readable capacity
        self.make_power_supply("BAT1", "Battery", present=0)
        self.assertFalse(self.should_stop("50"))

    def test_min_battery_level_no_battery(self):
        os.makedirs(os.path.join(self.tempdir, "power_supply"))
        self.assertTrue(self.should_stop("50"))

    def test_min_battery_level_invalid(self):
        self.make_power_supply("BAT0", "Battery", capacity=60)
        for value in ("50%", "101", "-1", "\u00b2", "true", "false"):
            with self.assertLogs(level="WARNING") as logs:
                self.assertTrue(self.should_stop(value))
            self.assertIn("Invalid MinBatteryLevel", logs.output[0])
        # no fallback to OnlyOnACPower
        self.assertTrue(self.should_stop("50%", only_on_ac_power="false"))


if __name__ == "__main__":
    # do not setup logging in here or the test will break
    unittest.main()
