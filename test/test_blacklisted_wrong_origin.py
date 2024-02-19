#!/usr/bin/python3
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import (
    Mock,
)

from test.test_base import TestBase

from unattended_upgrade import calculate_upgradable_pkgs


class TestBlacklistedWrongOrigin(TestBase):

    def test_if_origin_does_not_match_then_blacklist_is_not_checked(self):
        origin = Mock()
        origin.origin = "some-other-origin"

        pkg = Mock()
        pkg.name = "postgresql"
        pkg.is_upgradable = True
        pkg.candidate = Mock()
        pkg.candidate.policy_priority = 500
        pkg.candidate.origins = [origin]
        pkg.versions = [pkg.candidate]

        cache = Mock()
        cache.__iter__ = Mock(return_value=iter([pkg]))
        options = Mock()
        cache.allowed_origins = ["o=allowed-origin"]
        cache.blacklist = ["postgresql"]
        cache.whitelist = []

        pkgs_to_upgrade = calculate_upgradable_pkgs(cache, options)

        self.assertListEqual([], pkgs_to_upgrade)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
