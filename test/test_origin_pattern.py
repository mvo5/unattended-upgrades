#!/usr/bin/python3

import apt_pkg
import logging
import unittest

apt_pkg.config.set("Dir", "./aptroot")

import unattended_upgrade
from unattended_upgrade import (
    check_changes_for_sanity,
    is_allowed_origin,
    get_distro_codename,
    match_whitelist_string,
    UnknownMatcherError,
)


class MockOrigin():
    trusted = True


class MockCandidate():
    pass


class MockPackage():
    pass


class MockCache(dict):
    def __iter__(self):
        for pkgname in self.keys():
            yield self[pkgname]

    def get_changes(self):
        for pkgname in self.keys():
            yield self[pkgname]


class MockDepCache():
    pass


class TestOriginPatern(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_match_whitelist_string(self):
        origin = self._get_mock_origin(
            "OriginUbuntu", "LabelUbuntu", "ArchiveUbuntu",
            "archive.ubuntu.com", "main")
        # good
        s = "o=OriginUbuntu"
        self.assertTrue(match_whitelist_string(s, origin))
        s = "o=OriginUbuntu,l=LabelUbuntu,a=ArchiveUbuntu," \
            "site=archive.ubuntu.com"
        self.assertTrue(match_whitelist_string(s, origin))
        # bad
        s = ""
        self.assertFalse(match_whitelist_string(s, origin))
        s = "o=something"
        self.assertFalse(match_whitelist_string(s, origin))
        s = "o=LabelUbuntu,a=no-match"
        self.assertFalse(match_whitelist_string(s, origin))
        # with escaping
        origin = self._get_mock_origin("Google, Inc.", archive="stable")
        # good
        s = "o=Google\, Inc.,a=stable"
        self.assertTrue(match_whitelist_string(s, origin))

    def test_match_whitelist_from_conffile(self):
        # read some
        apt_pkg.config.clear("Unattended-Upgrade")
        apt_pkg.read_config_file(
            apt_pkg.config, "./data/50unattended-upgrades.Test")
        allowed_origins = unattended_upgrade.get_allowed_origins()
        #print allowed_origins
        self.assertTrue("o=aOrigin,a=aArchive" in allowed_origins)
        self.assertTrue("s=aSite,l=aLabel" in allowed_origins)
        self.assertTrue("o=Google\, Inc.,suite=stable" in allowed_origins)

    def test_macro(self):
        codename = get_distro_codename()
        s = "a=${distro_codename}"
        origin = self._get_mock_origin("Foo", archive=codename)
        self.assertTrue(match_whitelist_string(s, origin))

    def test_compatiblity(self):
        apt_pkg.config.clear("Unattended-Upgrade")
        apt_pkg.read_config_file(
            apt_pkg.config, "./data/50unattended-upgrades.compat")
        allowed_origins = unattended_upgrade.get_allowed_origins()
        #print allowed_origins
        self.assertTrue("o=Google\, Inc.,a=stable" in allowed_origins)
        self.assertTrue("o=MoreCorp\, eink,a=stable" in allowed_origins)
        # test whitelist
        pkg = self._get_mock_package()
        self.assertTrue(is_allowed_origin(pkg.candidate, allowed_origins))

    def test_escaped_colon(self):
        apt_pkg.config.clear("Unattended-Upgrade")
        apt_pkg.read_config_file(
            apt_pkg.config, "./data/50unattended-upgrades.colon")
        allowed_origins = unattended_upgrade.get_allowed_origins()

        self.assertIn('o=http://foo.bar,a=stable', allowed_origins)

    def test_unkown_matcher(self):
        apt_pkg.config.clear("Unattended-Upgrade")
        s = "xxx=OriginUbuntu"
        with self.assertRaises(UnknownMatcherError):
            self.assertTrue(match_whitelist_string(s, None))

    def test_blacklist(self):
        # get the mocks
        pkg = self._get_mock_package("linux-image")
        cache = self._get_mock_cache()
        cache[pkg.name] = pkg
        # origins and blacklist
        allowed_origins = ["o=Ubuntu"]
        blacklist = ["linux-.*"]
        # with blacklist pkg
        self.assertFalse(
            check_changes_for_sanity(
                cache, allowed_origins, blacklist, [".*"]))
        # with "normal" pkg
        pkg.name = "apt"
        self.assertTrue(
            check_changes_for_sanity(
                cache, allowed_origins, blacklist, [".*"]))

    def test_whitelist_with_strict_whitelisting(self):
        cache = self._get_mock_cache()
        for pkgname in ["not-whitelisted", "whitelisted"]:
            pkg = self._get_mock_package(name=pkgname)
            cache[pkg.name] = pkg
        # origins and blacklist
        allowed_origins = ["o=Ubuntu"]
        whitelist = ["whitelisted"]
        # test with strict whitelist
        apt_pkg.config.set(
            "Unattended-Upgrade::Package-Whitelist-Strict", "true")
        # ensure that a not-whitelisted pkg will fail
        self.assertTrue(cache["not-whitelisted"].marked_upgrade)
        self.assertFalse(
            check_changes_for_sanity(cache, allowed_origins, [], whitelist))

    def _get_mock_cache(self):
        cache = MockCache()
        cache._depcache = MockDepCache()
        cache._depcache.broken_count = 0
        cache.install_count = 1
        return cache

    def _get_mock_origin(self, aorigin="", label="", archive="",
                         site="", component=""):
        origin = MockOrigin()
        origin.origin = aorigin
        origin.label = label
        origin.archive = archive
        origin.site = site
        origin.compoent = component
        return origin

    def _get_mock_package(self, name="foo"):
        pkg = MockPackage()
        pkg._pkg = MockPackage()
        pkg._pkg.selected_state = 0
        pkg.name = name
        pkg.marked_install = True
        pkg.marked_upgrade = True
        pkg.marked_delete = False
        pkg.candidate = MockCandidate()
        pkg.candidate.origins = [self._get_mock_origin("Ubuntu"),
                                 self._get_mock_origin(aorigin="Google, Inc.",
                                                       archive="stable")]
        pkg.candidate.record = {}
        return pkg

    def test_match_whitelist_wildcard(self):
        origin = self._get_mock_origin(
            "OriginUbuntu", "LabelUbuntu", "ArchiveUbuntu",
            "archive.ubuntu.com", "main")
        # good
        s = "o=OriginU*"
        self.assertTrue(match_whitelist_string(s, origin))
        # bad
        s = "o=X*"
        self.assertFalse(match_whitelist_string(s, origin))
        # good
        s = "o=?riginUbunt?"
        self.assertTrue(match_whitelist_string(s, origin))
        # good
        s = "o=*Ubunt?"
        self.assertTrue(match_whitelist_string(s, origin))

    def test_get_allowed_origins_legacy(self):
        for cfg, (distro_id, distro_codename) in (
                # ":" as separator
                ("Ubuntu:lucid-security", ("Ubuntu", "lucid-security")),
                ("http\://foo.bar:stable", ("http://foo.bar", "stable")),
                # space as separator
                ("Ubuntu lucid-security", ("Ubuntu", "lucid-security")),
                ("http\://baz.mee stable", ("http://baz.mee", "stable"))):
            apt_pkg.config.clear("Unattended-Upgrade::Allowed-Origins")
            apt_pkg.config.set("Unattended-Upgrade::Allowed-Origins::", cfg)
            li = unattended_upgrade.get_allowed_origins_legacy()
            self.assertEqual(len(li), 1)
            self.assertEqual(li[0], "o=%s,a=%s" % (distro_id, distro_codename))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
