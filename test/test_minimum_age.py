#!/usr/bin/python3

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import apt_pkg

from unattended_upgrade import (
    MinimumAge,
    NoAllowedOriginError,
    sanity_problem,
    ver_in_allowed_origin,
)


class TestMinimumAge(unittest.TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

        apt_pkg.config.clear("Unattended-Upgrade::MinimumAge")
        apt_pkg.config.clear("Unattended-Upgrade::MinimumAge-Exempt-Origins")
        self.addCleanup(apt_pkg.config.clear, "Unattended-Upgrade::MinimumAge")
        self.addCleanup(
            apt_pkg.config.clear,
            "Unattended-Upgrade::MinimumAge-Exempt-Origins")

        # Match Ubuntu's security pocket independently of the test host.
        self.distro = patch("unattended_upgrade.get_distro_id",
                            return_value="Ubuntu")
        self.codename = patch("unattended_upgrade.get_distro_codename",
                              return_value="noble")
        self.distro.start()
        self.codename.start()
        self.addCleanup(self.distro.stop)
        self.addCleanup(self.codename.stop)

        self.allowed = ["origin=Ubuntu"]
        self.now = 200000
        clock = patch("unattended_upgrade.time.time", return_value=self.now)
        clock.start()
        self.addCleanup(clock.stop)

    def package(self, version="2", architecture="amd64", security=False,
                name="example"):
        origin = SimpleNamespace(
            origin="Ubuntu", archive="noble-security" if security else
            "noble-updates", codename="noble", trusted=True,
            component="main", label="Ubuntu", site="archive.ubuntu.com")

        candidate = SimpleNamespace(version=version, origins=[origin],
                                    record={}, dependencies=[])
        package = SimpleNamespace(
            name=name, fullname=name + ":" + architecture,
            versions=[candidate], candidate=candidate, marked_install=True,
            marked_upgrade=False, marked_delete=False,
            _pkg=SimpleNamespace(selected_state=apt_pkg.SELSTATE_INSTALL))
        candidate.package = package
        return package

    def cache(self, policy, packages):
        return SimpleNamespace(
            minimum_age=policy, _depcache=SimpleNamespace(broken_count=0),
            install_count=len(packages), get_changes=lambda: packages,
            allowed_origins=self.allowed, blacklist=[], whitelist=[],
            strict_whitelist=False)

    def dependency(self, package, target):
        package.candidate.dependencies.append([
            SimpleNamespace(rawtype="Depends", installed_target_versions=[],
                            target_versions=[target.candidate])])

    def policy(self, setting="48h"):
        apt_pkg.config.set("Unattended-Upgrade::MinimumAge", setting)
        return MinimumAge(self.directory.name, self.allowed)

    def test_disabled_by_default(self):
        policy = MinimumAge(self.directory.name, self.allowed)
        package = self.package()

        self.assertIsNone(policy.reason(package, package.candidate))
        policy.observe([package], now=self.now)
        self.assertFalse(os.path.exists(policy.state_file))

    def test_exact_boundary(self):
        policy = self.policy()
        package = self.package()
        policy.observe([package], now=self.now)

        self.assertIsNotNone(policy.reason(
            package, package.candidate, now=self.now + 48 * 3600 - 1))
        self.assertIsNone(policy.reason(
            package, package.candidate, now=self.now + 48 * 3600))

    def test_state_survives_new_instance(self):
        package = self.package()
        self.policy().observe([package], now=self.now)

        policy = self.policy()
        policy.observe([package], now=self.now + 48 * 3600)

        self.assertIsNone(policy.reason(
            package, package.candidate, now=self.now + 48 * 3600))

    def test_replacement_version_starts_new_cooldown(self):
        policy = self.policy()
        policy.observe([self.package()], now=self.now)

        package = self.package(version="3")
        policy.observe([package], now=self.now + 48 * 3600)

        self.assertIsNotNone(policy.reason(
            package, package.candidate, now=self.now + 48 * 3600))

    def test_architectures_have_separate_timestamps(self):
        policy = self.policy()
        policy.observe([self.package()], now=self.now)

        package = self.package(architecture="arm64")
        policy.observe([package], now=self.now + 48 * 3600)

        self.assertIsNotNone(policy.reason(
            package, package.candidate, now=self.now + 48 * 3600))

    def test_security_is_immediately_eligible(self):
        policy = self.policy()
        package = self.package(security=True)

        self.assertIsNone(
            policy.reason(package, package.candidate, now=self.now))

    def test_untrusted_security_origin_is_not_exempt(self):
        policy = self.policy()
        package = self.package(security=True)
        package.candidate.origins[0].trusted = False

        self.assertIsNotNone(
            policy.reason(package, package.candidate, now=self.now))

    def test_disallowed_security_origin_is_not_exempt(self):
        policy = self.policy()
        policy.allowed_origins = ["archive=noble-updates"]
        package = self.package(security=True)

        self.assertIsNotNone(
            policy.reason(package, package.candidate, now=self.now))

    def test_dry_run_does_not_write_state(self):
        policy = self.policy()
        policy.observe([self.package()], dry_run=True, now=self.now)

        self.assertFalse(os.path.exists(policy.state_file))

    def test_corrupt_state_restarts_cooldown(self):
        policy = self.policy()
        os.makedirs(os.path.dirname(policy.state_file))
        with open(policy.state_file, "w") as state:
            state.write("invalid JSON")

        package = self.package()
        policy.observe([package], now=self.now)

        self.assertIsNotNone(
            policy.reason(package, package.candidate, now=self.now))

    def test_invalid_timestamp_restarts_cooldown(self):
        policy = self.policy()
        package = self.package()
        os.makedirs(os.path.dirname(policy.state_file))
        with open(policy.state_file, "w") as state:
            json.dump({package.fullname: {"2": "invalid"}}, state)

        policy.observe([package], now=self.now)

        self.assertIsNotNone(
            policy.reason(package, package.candidate, now=self.now))

    def test_clock_rollback_does_not_release_package(self):
        policy = self.policy()
        package = self.package()
        policy.observe([package], now=self.now)

        self.assertIsNotNone(
            policy.reason(package, package.candidate, now=self.now - 3600))

    def test_older_security_candidate_remains_eligible(self):
        policy = self.policy()

        # APT may prefer a newer ordinary update over an older security fix.
        package = self.package(version="3")
        security = self.package(version="2", security=True).candidate
        package.versions.append(security)
        policy.observe([package], now=self.now)

        self.assertIs(security, ver_in_allowed_origin(
            package, self.allowed, policy))

    def test_young_ordinary_candidate_is_not_selected(self):
        policy = self.policy()
        package = self.package()
        policy.observe([package], now=self.now)

        with self.assertRaises(NoAllowedOriginError):
            ver_in_allowed_origin(package, self.allowed, policy)

    def test_ordinary_dependency_cannot_bypass_cooldown(self):
        policy = self.policy()
        package = self.package()
        dependency = self.package(name="dependency")
        self.dependency(package, dependency)

        policy.observe([package], now=self.now - 48 * 3600)
        policy.observe([package, dependency], now=self.now)

        self.assertIn("dependency:amd64", sanity_problem(
            self.cache(policy, [package, dependency]), package))

    def test_security_dependency_is_exempt(self):
        policy = self.policy()
        package = self.package(security=True)
        dependency = self.package(name="dependency")
        self.dependency(package, dependency)
        policy.observe([package, dependency], now=self.now)

        self.assertIsNone(sanity_problem(
            self.cache(policy, [package, dependency]), package))

    def test_security_does_not_exempt_unrelated_upgrade(self):
        policy = self.policy()
        package = self.package(security=True)
        unrelated = self.package(name="unrelated")
        policy.observe([package, unrelated], now=self.now)

        self.assertIn("unrelated:amd64", sanity_problem(
            self.cache(policy, [package, unrelated]), package))

    def test_security_dependency_still_respects_blacklist(self):
        policy = self.policy()
        package = self.package(security=True)
        dependency = self.package(name="dependency")
        self.dependency(package, dependency)
        policy.observe([package, dependency], now=self.now)

        cache = self.cache(policy, [package, dependency])
        cache.blacklist = ["dependency"]

        self.assertIn("blacklisted", sanity_problem(cache, package))


if __name__ == "__main__":
    unittest.main()
