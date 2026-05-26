#!/usr/bin/python3
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock

from unattended_upgrade import transitive_dependencies


class TestDependencies(unittest.TestCase):

    def _get_pkg_with_deps(self, *dep_names):
        pkg = Mock()
        pkg.candidate = Mock()
        pkg.candidate.dependencies = [
            [Mock(name=name, rawtype="Depends")] for name in dep_names]
        for dep, dep_name in zip(pkg.candidate.dependencies, dep_names):
            dep[0].name = dep_name
        return pkg

    def test_transitive_dependencies_keeps_independent_calls_separate(self):
        cache = {}
        first_pkg = self._get_pkg_with_deps("first-dependency")
        second_pkg = self._get_pkg_with_deps("second-dependency")

        self.assertEqual(
            {"first-dependency"}, transitive_dependencies(first_pkg, cache))
        self.assertEqual(
            {"second-dependency"}, transitive_dependencies(second_pkg, cache))


if __name__ == "__main__":
    unittest.main()
