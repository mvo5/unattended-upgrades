#!/usr/bin/python3

import os
import shutil
import subprocess
import tempfile
import unittest

import unattended_upgrade


class TestOsRelease(unittest.TestCase):

    def tearDown(self):
        # restore the real (host) distro info that may have been overridden
        unattended_upgrade.init_distro_info()

    def _init_from(self, content):
        with tempfile.NamedTemporaryFile(
                "w", suffix="os-release", delete=False) as f:
            f.write(content)
            path = f.name
        self.addCleanup(os.unlink, path)
        unattended_upgrade.init_distro_info(paths=[path])

    def test_parse_debian_stable(self):
        self._init_from(
            'PRETTY_NAME="Debian GNU/Linux 13 (trixie)"\n'
            'NAME="Debian GNU/Linux"\n'
            'VERSION_ID="13"\n'
            'VERSION="13 (trixie)"\n'
            'VERSION_CODENAME=trixie\n'
            'ID=debian\n')
        self.assertEqual(unattended_upgrade.DISTRO_ID, "Debian")
        self.assertEqual(unattended_upgrade.DISTRO_CODENAME, "trixie")
        self.assertEqual(unattended_upgrade.DISTRO_RELEASE, "13")
        self.assertEqual(unattended_upgrade.DISTRO_DESC,
                         "Debian GNU/Linux 13 (trixie)")

    def test_parse_ubuntu(self):
        # ID is lower case in os-release but lsb_release reports "Ubuntu";
        # the NAME field carries the canonical casing
        self._init_from(
            'PRETTY_NAME="Ubuntu 24.04.3 LTS"\n'
            'NAME="Ubuntu"\n'
            'VERSION_ID="24.04"\n'
            'VERSION_CODENAME=noble\n'
            'ID=ubuntu\n'
            'UBUNTU_CODENAME=noble\n')
        self.assertEqual(unattended_upgrade.DISTRO_ID, "Ubuntu")
        self.assertEqual(unattended_upgrade.DISTRO_CODENAME, "noble")
        self.assertEqual(unattended_upgrade.DISTRO_RELEASE, "24.04")

    def test_parse_missing_fields_fall_back_to_na(self):
        # Debian testing/sid has no VERSION_CODENAME / VERSION_ID, matching
        # the "n/a" that lsb_release emits in that case
        self._init_from(
            'PRETTY_NAME="Debian GNU/Linux trixie/sid"\n'
            'NAME="Debian GNU/Linux"\n'
            'ID=debian\n')
        self.assertEqual(unattended_upgrade.DISTRO_ID, "Debian")
        self.assertEqual(unattended_upgrade.DISTRO_CODENAME, "n/a")
        self.assertEqual(unattended_upgrade.DISTRO_RELEASE, "n/a")

    def test_missing_file_returns_empty(self):
        self.assertEqual(
            unattended_upgrade.parse_os_release(paths=["/does/not/exist"]), {})

    @unittest.skipUnless(shutil.which("lsb_release"),
                         "lsb_release not installed")
    def test_matches_lsb_release(self):
        """our os-release parsing must produce the same values lsb_release
        derives from os-release on this system"""
        unattended_upgrade.init_distro_info()

        def lsb(flag):
            return subprocess.check_output(
                ["lsb_release", flag, "-s"], universal_newlines=True).strip()

        self.assertEqual(unattended_upgrade.DISTRO_ID, lsb("-i"))
        self.assertEqual(unattended_upgrade.DISTRO_CODENAME, lsb("-c"))
        self.assertEqual(unattended_upgrade.DISTRO_RELEASE, lsb("-r"))
        self.assertEqual(unattended_upgrade.DISTRO_DESC, lsb("-d"))


if __name__ == "__main__":
    unittest.main()
