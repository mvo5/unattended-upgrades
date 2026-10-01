#!/usr/bin/python3

import datetime
import json
import os
import shutil
import tempfile
import unittest

from unittest.mock import Mock, patch

import apt_pkg

import unattended_upgrade
from unattended_upgrade import (
    calculate_upgradable_pkgs,
    first_seen_age_days,
    first_seen_age_delta,
    load_seen_versions,
    minimum_age_reason_for_version,
    parse_minimum_age_setting,
    record_seen_versions,
    MINIMUM_AGE_FALLBACK_HOLD,
    MINIMUM_AGE_FALLBACK_INSTALL,
    save_seen_versions,
    SEEN_VERSIONS_FILE,
)

from test.test_base import TestBase, MockOptions


class TestParseMinimumAgeSetting(unittest.TestCase):

    def test_plain_integer_means_days(self):
        delta, label = parse_minimum_age_setting("7")
        self.assertEqual(delta, datetime.timedelta(days=7))
        self.assertEqual(label, "7d")

    def test_days_suffix(self):
        delta, label = parse_minimum_age_setting("2d")
        self.assertEqual(delta, datetime.timedelta(days=2))
        self.assertEqual(label, "2d")

    def test_hours_suffix(self):
        delta, label = parse_minimum_age_setting("12h")
        self.assertEqual(delta, datetime.timedelta(hours=12))
        self.assertEqual(label, "12h")

    def test_invalid_value_disables_minimum_age(self):
        delta, label = parse_minimum_age_setting("abc")
        self.assertEqual(delta, datetime.timedelta(0))
        self.assertEqual(label, "0d")


class TestLoadSeenVersions(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir)

    def test_load_missing_file(self):
        path = os.path.join(self.tmpdir, "nonexistent.json")
        result = load_seen_versions(path)
        self.assertEqual(result, {})

    def test_load_valid_file(self):
        path = os.path.join(self.tmpdir, "seen.json")
        data = {
            "_format_version": 1,
            "packages": {
                "bash": {"5.2-3": "2026-02-08T01:02:03Z"},
                "openssl": {"3.0.13-1": "2026-02-01T04:05:06Z"},
            },
        }
        with open(path, "w") as fp:
            json.dump(data, fp)
        result = load_seen_versions(path)
        self.assertEqual(result, data["packages"])

    def test_load_corrupt_json(self):
        path = os.path.join(self.tmpdir, "corrupt.json")
        with open(path, "w") as fp:
            fp.write("{not valid json!!")
        result = load_seen_versions(path)
        self.assertEqual(result, {})

    def test_load_wrong_format_version(self):
        path = os.path.join(self.tmpdir, "wrong.json")
        data = {
            "_format_version": 99,
            "packages": {"bash": {"1.0": "2026-01-01T00:00:00Z"}},
        }
        with open(path, "w") as fp:
            json.dump(data, fp)
        result = load_seen_versions(path)
        self.assertEqual(result, {})


class TestSaveSeenVersions(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir)

    def test_save_creates_file(self):
        path = os.path.join(self.tmpdir, "subdir", "seen.json")
        packages = {"bash": {"5.2-3": "2026-02-08T01:02:03Z"}}
        save_seen_versions(path, packages)
        self.assertTrue(os.path.exists(path))
        with open(path, "r") as fp:
            data = json.load(fp)
        self.assertEqual(data["_format_version"], 1)
        self.assertEqual(data["packages"], packages)

    def test_save_roundtrip(self):
        path = os.path.join(self.tmpdir, "seen.json")
        packages = {
            "bash": {"5.2-3": "2026-02-08T01:02:03Z"},
            "openssl": {"3.0.13-1": "2026-02-01T04:05:06Z"},
        }
        save_seen_versions(path, packages)
        loaded = load_seen_versions(path)
        self.assertEqual(loaded, packages)


class TestFirstSeenAge(unittest.TestCase):

    def test_first_seen_age_delta_hours(self):
        now = datetime.datetime(2026, 2, 15, 12, 0, 0)
        seen = {"bash": {"5.2-3": "2026-02-15T00:00:00Z"}}
        age = first_seen_age_delta("bash", "5.2-3", seen, now=now)
        self.assertEqual(age, datetime.timedelta(hours=12))

    def test_first_seen_age_days_compat(self):
        today = datetime.date(2026, 2, 15)
        seen = {"bash": {"5.2-3": "2026-02-08T00:00:00Z"}}
        age = first_seen_age_days("bash", "5.2-3", seen, today=today)
        self.assertEqual(age, 7)

    def test_first_seen_unknown_package(self):
        seen = {"bash": {"5.2-3": "2026-02-08T00:00:00Z"}}
        age = first_seen_age_delta("curl", "7.88.1-10", seen)
        self.assertIsNone(age)

    def test_first_seen_unknown_version(self):
        seen = {"bash": {"5.2-3": "2026-02-08T00:00:00Z"}}
        age = first_seen_age_delta("bash", "5.2-4", seen)
        self.assertIsNone(age)

    def test_first_seen_clock_skew_negative(self):
        now = datetime.datetime(2026, 2, 10, 0, 0, 0)
        seen = {"bash": {"5.2-3": "2026-02-15T00:00:00Z"}}
        age = first_seen_age_delta("bash", "5.2-3", seen, now=now)
        self.assertEqual(age, datetime.timedelta(0))

    def test_first_seen_invalid_timestamp(self):
        seen = {"bash": {"5.2-3": "2026-02-08"}}
        age = first_seen_age_delta("bash", "5.2-3", seen)
        self.assertIsNone(age)


class TestMinimumAgeReasonForVersion(unittest.TestCase):

    def test_minimum_age_disabled(self):
        result = minimum_age_reason_for_version(
            "bash", "5.2-3", datetime.timedelta(0), {},
            MINIMUM_AGE_FALLBACK_HOLD)
        self.assertIsNone(result)

    def test_minimum_age_too_young_days(self):
        now = datetime.datetime(2099, 1, 15, 0, 0, 0)
        seen = {"bash": {"5.2-3": "2099-01-13T00:00:00Z"}}
        result = minimum_age_reason_for_version(
            "bash", "5.2-3", datetime.timedelta(days=7), seen,
            MINIMUM_AGE_FALLBACK_HOLD, now=now, minimum_age_label="7d")
        self.assertIsNotNone(result)
        self.assertIn("keeping back", result)
        self.assertIn("MinimumAge: 7d", result)

    def test_minimum_age_old_enough_days(self):
        now = datetime.datetime(2099, 1, 15, 0, 0, 0)
        seen = {"bash": {"5.2-3": "2099-01-05T00:00:00Z"}}
        result = minimum_age_reason_for_version(
            "bash", "5.2-3", datetime.timedelta(days=7), seen,
            MINIMUM_AGE_FALLBACK_HOLD, now=now, minimum_age_label="7d")
        self.assertIsNone(result)

    def test_minimum_age_too_young_hours(self):
        now = datetime.datetime(2099, 1, 15, 12, 0, 0)
        seen = {"bash": {"5.2-3": "2099-01-15T00:00:00Z"}}
        result = minimum_age_reason_for_version(
            "bash", "5.2-3", datetime.timedelta(hours=24), seen,
            MINIMUM_AGE_FALLBACK_HOLD, now=now, minimum_age_label="24h")
        self.assertIsNotNone(result)
        self.assertIn("MinimumAge: 24h", result)

    def test_minimum_age_exactly_enough_hours(self):
        now = datetime.datetime(2099, 1, 16, 0, 0, 0)
        seen = {"bash": {"5.2-3": "2099-01-15T00:00:00Z"}}
        result = minimum_age_reason_for_version(
            "bash", "5.2-3", datetime.timedelta(hours=24), seen,
            MINIMUM_AGE_FALLBACK_HOLD, now=now, minimum_age_label="24h")
        self.assertIsNone(result)


class TestFallbackPolicy(unittest.TestCase):

    NOW = datetime.datetime(2099, 1, 15, 0, 0, 0)
    MIN_AGE = datetime.timedelta(days=7)

    def test_fallback_hold_unknown_version(self):
        result = minimum_age_reason_for_version(
            "bash", "5.2-3", self.MIN_AGE, {},
            MINIMUM_AGE_FALLBACK_HOLD, now=self.NOW, minimum_age_label="7d")
        self.assertIsNotNone(result)
        self.assertIn("keeping back", result)

    def test_fallback_install_unknown_version(self):
        result = minimum_age_reason_for_version(
            "bash", "5.2-3", self.MIN_AGE, {},
            MINIMUM_AGE_FALLBACK_INSTALL, now=self.NOW,
            minimum_age_label="7d")
        self.assertIsNone(result)


def _make_mock_pkg(name, version, origin_name="allowed-origin",
                   installed_version="0.0.1"):
    """Build a mock package that looks upgradable from an allowed origin."""
    origin = Mock()
    origin.origin = origin_name
    origin.trusted = True

    candidate = Mock()
    candidate.version = version
    candidate.origins = [origin]
    candidate.policy_priority = 500

    installed = Mock()
    installed.version = installed_version
    installed.policy_priority = 500
    installed.origins = [origin]

    pkg = Mock()
    pkg.name = name
    pkg.is_upgradable = True
    pkg.is_installed = True
    pkg.is_auto_installed = False
    pkg.candidate = candidate
    pkg.installed = installed
    pkg.versions = [candidate]
    return pkg


def _make_mock_cache(pkgs, seen_versions, minimum_age_value,
                     fallback=MINIMUM_AGE_FALLBACK_HOLD):
    """Build a mock cache with MinimumAge attributes wired up."""
    cache = Mock()
    cache.__iter__ = Mock(return_value=iter(pkgs))
    cache.get_changes = Mock(return_value=[])
    cache.allowed_origins = ["o=allowed-origin"]
    cache.blacklist = []
    cache.whitelist = []
    cache.strict_whitelist = False

    if isinstance(minimum_age_value, str):
        min_delta, min_label = parse_minimum_age_setting(minimum_age_value)
    elif isinstance(minimum_age_value, int):
        min_delta = datetime.timedelta(days=minimum_age_value)
        min_label = "%dd" % minimum_age_value
    else:
        min_delta = minimum_age_value
        min_label = "0d"

    cache.minimum_age_delta = min_delta
    cache.minimum_age_label = min_label
    cache.minimum_age_days = int(min_delta.total_seconds() // (24 * 3600))
    cache.seen_versions = seen_versions
    cache.minimum_age_fallback = fallback

    from unattended_upgrade import minimum_age_reason_for_version as fn
    cache.minimum_age_reason = (
        lambda pkg_name, version: fn(
            pkg_name, version, cache.minimum_age_delta,
            cache.seen_versions, cache.minimum_age_fallback,
            minimum_age_label=cache.minimum_age_label))

    return cache


class TestCalculateUpgradablePkgsMinimumAge(unittest.TestCase):
    """Integration: MinimumAge filtering inside calculate_upgradable_pkgs."""

    @patch("unattended_upgrade.try_to_upgrade",
           side_effect=lambda pkg, lst, cache: lst.append(pkg))
    def test_too_young_pkg_is_skipped_days(self, _mock_try):
        pkg = _make_mock_pkg("bash", "5.2-3")
        seen = {"bash": {"5.2-3": "2099-01-13T00:00:00Z"}}
        cache = _make_mock_cache([pkg], seen, minimum_age_value="7")
        options = Mock()

        with patch("unattended_upgrade.utcnow_without_microseconds") as mock_now:
            mock_now.return_value = datetime.datetime(2099, 1, 15, 0, 0, 0)
            result = calculate_upgradable_pkgs(cache, options)

        self.assertEqual(result, [])
        _mock_try.assert_not_called()

    @patch("unattended_upgrade.try_to_upgrade",
           side_effect=lambda pkg, lst, cache: lst.append(pkg))
    def test_old_enough_pkg_passes_days(self, _mock_try):
        pkg = _make_mock_pkg("bash", "5.2-3")
        seen = {"bash": {"5.2-3": "2099-01-05T00:00:00Z"}}
        cache = _make_mock_cache([pkg], seen, minimum_age_value="7d")
        options = Mock()

        with patch("unattended_upgrade.utcnow_without_microseconds") as mock_now:
            mock_now.return_value = datetime.datetime(2099, 1, 15, 0, 0, 0)
            result = calculate_upgradable_pkgs(cache, options)

        self.assertEqual(result, [pkg])
        _mock_try.assert_called_once()

    @patch("unattended_upgrade.try_to_upgrade",
           side_effect=lambda pkg, lst, cache: lst.append(pkg))
    def test_too_young_pkg_is_skipped_hours(self, _mock_try):
        pkg = _make_mock_pkg("bash", "5.2-3")
        seen = {"bash": {"5.2-3": "2099-01-15T00:00:00Z"}}
        cache = _make_mock_cache([pkg], seen, minimum_age_value="24h")
        options = Mock()

        with patch("unattended_upgrade.utcnow_without_microseconds") as mock_now:
            mock_now.return_value = datetime.datetime(2099, 1, 15, 23, 0, 0)
            result = calculate_upgradable_pkgs(cache, options)

        self.assertEqual(result, [])
        _mock_try.assert_not_called()

    @patch("unattended_upgrade.try_to_upgrade",
           side_effect=lambda pkg, lst, cache: lst.append(pkg))
    def test_minimum_age_zero_lets_everything_through(self, _mock_try):
        pkg = _make_mock_pkg("bash", "5.2-3")
        cache = _make_mock_cache([pkg], {}, minimum_age_value="0")
        options = Mock()

        result = calculate_upgradable_pkgs(cache, options)

        self.assertEqual(result, [pkg])
        _mock_try.assert_called_once()

    @patch("unattended_upgrade.try_to_upgrade",
           side_effect=lambda pkg, lst, cache: lst.append(pkg))
    def test_fallback_hold_blocks_unknown(self, _mock_try):
        pkg = _make_mock_pkg("bash", "5.2-3")
        cache = _make_mock_cache([pkg], {}, minimum_age_value="7d",
                                 fallback=MINIMUM_AGE_FALLBACK_HOLD)
        options = Mock()

        result = calculate_upgradable_pkgs(cache, options)

        self.assertEqual(result, [])
        _mock_try.assert_not_called()

    @patch("unattended_upgrade.try_to_upgrade",
           side_effect=lambda pkg, lst, cache: lst.append(pkg))
    def test_fallback_install_passes_unknown(self, _mock_try):
        pkg = _make_mock_pkg("bash", "5.2-3")
        cache = _make_mock_cache([pkg], {}, minimum_age_value="7d",
                                 fallback=MINIMUM_AGE_FALLBACK_INSTALL)
        options = Mock()

        result = calculate_upgradable_pkgs(cache, options)

        self.assertEqual(result, [pkg])
        _mock_try.assert_called_once()


class TestSkipInstalledCandidate(unittest.TestCase):
    """Packages where allowed-origin candidate == installed should be skipped."""

    def test_record_seen_versions_skips_installed_version(self):
        """If the best version from allowed origins is already installed,
        record_seen_versions must not add it to seen_versions."""
        pkg = _make_mock_pkg("linux-firmware", "1.40",
                             installed_version="1.40")
        cache = _make_mock_cache([pkg], {}, minimum_age_value="7d")
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)
        state_file = os.path.join(tmpdir, "seen.json")

        now = datetime.datetime(2099, 1, 15, 0, 0, 0)
        seen = record_seen_versions(cache, state_file, now=now)
        self.assertNotIn("linux-firmware", seen)

    @patch("unattended_upgrade.try_to_upgrade",
           side_effect=lambda pkg, lst, cache: lst.append(pkg))
    def test_calculate_upgradable_skips_installed_candidate(self, _mock_try):
        """If allowed-origin candidate == installed, the package must not
        reach try_to_upgrade or appear in the result list."""
        pkg = _make_mock_pkg("linux-firmware", "1.40",
                             installed_version="1.40")
        seen = {"linux-firmware": {"1.40": "2099-01-01T00:00:00Z"}}
        cache = _make_mock_cache([pkg], seen, minimum_age_value="7d")
        options = Mock()

        result = calculate_upgradable_pkgs(cache, options)

        self.assertEqual(result, [])
        _mock_try.assert_not_called()


class TestMinimumAgeRealAptroot(TestBase):
    """Integration tests using a real apt cache (root.rewind aptroot)."""

    UPGRADABLE = ["test-package", "test2-package", "test3-package"]
    FIXED_NOW = datetime.datetime(2099, 1, 15, 0, 0, 0)

    def _make_cache(self):
        self.mock_allowed_origins("origin=Ubuntu,archive=lucid-security")
        rootdir = self.make_fake_aptroot(
            os.path.join(self.testdir, "root.rewind"))
        cache = unattended_upgrade.UnattendedUpgradesCache(rootdir=rootdir)
        return rootdir, cache

    def test_baseline_no_minimum_age(self):
        rootdir, cache = self._make_cache()
        self.assertEqual(cache.minimum_age_delta, datetime.timedelta(0))

        options = MockOptions()
        pkgs = calculate_upgradable_pkgs(cache, options)
        self.assertEqual([p.name for p in pkgs], self.UPGRADABLE)

    def test_minimum_age_blocks_fresh_packages(self):
        apt_pkg.config.set("Unattended-Upgrade::MinimumAge", "7")
        self.addCleanup(
            apt_pkg.config.set, "Unattended-Upgrade::MinimumAge", "0")
        rootdir, cache = self._make_cache()
        self.assertEqual(cache.minimum_age_label, "7d")

        seen_file = os.path.join(rootdir, SEEN_VERSIONS_FILE)
        cache.seen_versions = record_seen_versions(
            cache, seen_file, now=self.FIXED_NOW)

        self.assertTrue(os.path.exists(seen_file))
        loaded = load_seen_versions(seen_file)
        for pkg_name in self.UPGRADABLE:
            self.assertIn(pkg_name, loaded)
            self.assertIn("2.0", loaded[pkg_name])

        options = MockOptions()
        with patch("unattended_upgrade.utcnow_without_microseconds") as mock_now:
            mock_now.return_value = self.FIXED_NOW
            pkgs = calculate_upgradable_pkgs(cache, options)
        self.assertEqual(pkgs, [])

    def test_minimum_age_passes_old_packages(self):
        apt_pkg.config.set("Unattended-Upgrade::MinimumAge", "7")
        self.addCleanup(
            apt_pkg.config.set, "Unattended-Upgrade::MinimumAge", "0")
        rootdir, cache = self._make_cache()

        ten_days_ago = (self.FIXED_NOW - datetime.timedelta(days=10)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        seen = {}
        for pkg_name in self.UPGRADABLE:
            seen[pkg_name] = {"2.0": ten_days_ago}
        seen_file = os.path.join(rootdir, SEEN_VERSIONS_FILE)
        save_seen_versions(seen_file, seen)

        cache.seen_versions = record_seen_versions(
            cache, seen_file, now=self.FIXED_NOW)

        options = MockOptions()
        with patch("unattended_upgrade.utcnow_without_microseconds") as mock_now:
            mock_now.return_value = self.FIXED_NOW
            pkgs = calculate_upgradable_pkgs(cache, options)
        self.assertEqual([p.name for p in pkgs], self.UPGRADABLE)

    def test_minimum_age_hours_blocks_23h_and_allows_24h(self):
        apt_pkg.config.set("Unattended-Upgrade::MinimumAge", "24h")
        self.addCleanup(
            apt_pkg.config.set, "Unattended-Upgrade::MinimumAge", "0")
        rootdir, cache = self._make_cache()
        self.assertEqual(cache.minimum_age_label, "24h")

        seen_file = os.path.join(rootdir, SEEN_VERSIONS_FILE)
        initial_seen = {}
        for pkg_name in self.UPGRADABLE:
            initial_seen[pkg_name] = {"2.0": "2099-01-15T00:00:00Z"}
        save_seen_versions(seen_file, initial_seen)
        cache.seen_versions = load_seen_versions(seen_file)

        options = MockOptions()
        with patch("unattended_upgrade.utcnow_without_microseconds") as mock_now:
            mock_now.return_value = datetime.datetime(2099, 1, 15, 23, 0, 0)
            pkgs_23h = calculate_upgradable_pkgs(cache, options)
        self.assertEqual(pkgs_23h, [])

        with patch("unattended_upgrade.utcnow_without_microseconds") as mock_now:
            mock_now.return_value = datetime.datetime(2099, 1, 16, 0, 0, 0)
            pkgs_24h = calculate_upgradable_pkgs(cache, options)
        self.assertEqual([p.name for p in pkgs_24h], self.UPGRADABLE)


if __name__ == "__main__":
    unittest.main()
