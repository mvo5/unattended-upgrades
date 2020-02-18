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
        cache.allowed_origins = ["o=allowed-origin"]
        cache.blacklist = ['findutils']
        cache.whitelist = []
        options = Mock()

        pkgs_to_upgrade = \
            calculate_upgradable_pkgs(cache, options)

        self.assertListEqual([], pkgs_to_upgrade)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
