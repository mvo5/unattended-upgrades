#!/usr/bin/python3

import logging
import os
import os.path
import shutil
import subprocess
import tempfile
import unittest

from unittest.mock import patch

import apt

import unattended_upgrade


class MockOptions(object):
    debug = True
    verbose = False
    download_only = False
    dry_run = False
    apt_debug = False
    minimal_upgrade_steps = True


class TestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # XXX: find a more elegant way
        pkgdir = os.path.join(os.path.dirname(__file__), "packages")
        subprocess.check_call(["make", "-C", pkgdir])

    def setUp(self):
        super(TestBase, self).setUp()
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir)
        self.testdir = os.path.dirname(__file__)
        # ensure custom logging gets reset (XXX: does this work?)
        self.addCleanup(logging.shutdown)
        logging.root.handlers = []
        # XXX: workaround for most tests assuming to run inside the "test"
        # dir
        os.chdir(self.testdir)
        # fake the lock file
        unattended_upgrade.LOCK_FILE = os.path.join(self.tempdir, "u-u.lock")
        # reset apt config
        apt.apt_pkg.init_config()
        # must be last
        self._saved_apt_conf = {}
        for k in apt.apt_pkg.config.keys():
            if not k.endswith("::"):
                self._saved_apt_conf[k] = apt.apt_pkg.config.get(k)
        self.addCleanup(self.enforce_apt_config_reset)
        # important to ensure that the updated apt config is applied
        self.addCleanup(apt.apt_pkg.init_system)

    def enforce_apt_config_reset(self):
        for k in self._saved_apt_conf:
            v = self._saved_apt_conf[k]
            apt.apt_pkg.config.set(k, v)

    def make_fake_aptroot(self, template=None, fake_pkgs=[]):
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir)
        aptroot = os.path.join(tmpdir, "aptroot")
        shutil.copytree(template, aptroot)
        # fake dpkg status
        mock_dpkg_status = os.path.join(aptroot, "var/lib/dpkg/status")
        with open(mock_dpkg_status, "a") as fp:
            for (pkgname, ver, deps) in fake_pkgs:
                # only "Depends" supported right now, extend as needed
                self.assertIn(set(deps.keys()), (set([]), set(["Depends"])))
                dep_str = ""
                if deps.get("Depends"):
                    dep_str = "Depends: {}".format(",".join(deps.get("Depends", [])))
                fp.write(
                    """
Package: %s
Status: install ok installed
Architecture: all
Version: %s
%s
"""
                    % (pkgname, ver, dep_str)
                )
        # setup everything to run dpkg
        apt.apt_pkg.config.set("Dir::State::status", mock_dpkg_status)
        apt.apt_pkg.config.clear("DPkg::Pre-Invoke")
        apt.apt_pkg.config.clear("DPkg::Post-Invoke")
        apt.apt_pkg.config.set("Debug::NoLocking", "true")
        # we don't really run dpkg
        fake_dpkg = os.path.join(aptroot, "usr", "bin", "dpkg")
        if not os.path.exists(fake_dpkg):
            os.makedirs(os.path.dirname(fake_dpkg), exist_ok=True)
            with open(fake_dpkg, "w") as fp:
                fp.write(
                    """#!/usr/bin/python3
import sys
print(sys.argv)
"""
                )
        os.chmod(fake_dpkg, 0o755)
        apt.apt_pkg.config.set("Dir::Bin::Dpkg", fake_dpkg)
        return aptroot

    def mock_distro(self, distro_id, codename, descr):
        for attr, fake_value in [
            ("DISTRO_ID", distro_id),
            ("DISTRO_CODENAME", codename),
            ("DISTRO_DESC", descr),
        ]:
            patcher = patch("unattended_upgrade.{}".format(attr), fake_value)
            patcher.start()
            self.addCleanup(patcher.stop)
