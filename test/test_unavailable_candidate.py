#!/usr/bin/python3
# -*- coding: utf-8 -*-

import unittest

from mock import Mock

from unattended_upgrade import calculate_upgradable_pkgs


class TestUnavailableCandidate(unittest.TestCase):

    def test_if_pkg_candidate_is_unavailable_then_pkg_is_not_considered(self):
        origin = Mock()
        origin.origin = 'allowed-origin'

        pkg = Mock()
        pkg.name = 'findutils'
        pkg.is_upgradable = False
        pkg.is_installed = True
        pkg.installed = Mock()
        pkg.installed.policy_priority = -1
        pkg.installed.origins = [origin]
        pkg.installed.version = '1:0.1'
        pkg.candidate = None
        pkg.versions = [pkg.installed]

        cache = Mock()
        cache.__iter__ = Mock(return_value=iter([pkg]))
        options = Mock()

        pkgs_to_upgrade, pkgs_kept_back = \
            calculate_upgradable_pkgs(
                cache, options, ['o=allowed-origin'],
                ['findutils'], [])

        self.assertListEqual([], pkgs_to_upgrade)
        self.assertEqual(0, len(pkgs_kept_back))


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
