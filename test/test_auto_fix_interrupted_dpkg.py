#!/usr/bin/python3

import json
import os
import subprocess
import sys
import traceback
import unittest
from unittest.mock import patch

import apt

from test.test_base import TestBase, MockOptions
import unattended_upgrade

apt.apt_pkg.config.set("APT::Architecture", "amd64")

# exits with 0 if the lock file given as argument can be locked
TRY_LOCK = """
import fcntl, os, sys
fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT)
try:
    fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError:
    sys.exit(1)
"""


class TestAutoFixInterruptedDpkg(TestBase):
    """A dirty dpkg journal makes apt_pkg.pkgsystem_lock() fail, the
       AutoFixInterruptedDpkg fix has to run before it
    """

    def setUp(self):
        TestBase.setUp(self)
        self.rootdir = self.make_fake_aptroot(
            template=os.path.join(self.testdir, "root.unused-deps"),
            fake_pkgs=[
                ("test-package", "1.0",
                 {"Depends": ["test-package-dependency"]}),
                ("test-package-dependency", "1.0", {}),
            ]
        )
        # fake on_ac_power
        os.environ["PATH"] = (os.path.join(self.rootdir, "usr", "bin") + ":"
                              + os.environ["PATH"])
        self.apt_conf = os.path.join(self.rootdir, "etc", "apt", "apt.conf")
        with open(self.apt_conf, "w") as fp:
            fp.write("""
Unattended-Upgrade::Allowed-Origins {
    "Ubuntu:lucid-security";
};
Unattended-Upgrade::Skip-Updates-On-Metered-Connections "false";
""")
        self.log = os.path.join(
            self.rootdir, "var", "log", "unattended-upgrades",
            "unattended-upgrades.log")
        os.makedirs(os.path.dirname(self.log), exist_ok=True)
        with open(self.log, "w"):
            pass
        admindir = os.path.join(self.rootdir, "var", "lib", "dpkg")
        self.frontend_lock = os.path.join(admindir, "lock-frontend")
        # an interrupted dpkg run leaves the journal dirty
        self.journal = os.path.join(admindir, "updates", "0000")
        with open(self.journal, "w"):
            pass
        self.dpkg_calls = []

    def frontend_lock_is_free(self):
        return subprocess.call(
            [sys.executable, "-c", TRY_LOCK, self.frontend_lock]) == 0

    def fake_dpkg(self, cmd, *args, **kwargs):
        if cmd[0] != "dpkg":
            return self.check_output(cmd, *args, **kwargs)
        self.dpkg_calls.append(
            (cmd, kwargs.get("env", {}).get("DPKG_FRONTEND_LOCKED"),
             self.frontend_lock_is_free()))
        os.unlink(self.journal)
        return "Setting up test-package (1.0) ...\n"

    def run_main_with_real_locks(self, options):
        # use the real dpkg locks of the fake root, like on a real system;
        # main() never releases the apt lock (the process exits) and apt
        # keeps its lock fds and count globally, so run it in a child
        # process to keep that state out of the other tests
        result = os.path.join(self.tempdir, "dpkg-calls.json")
        pid = os.fork()
        if pid == 0:
            ret = 255
            try:
                apt.apt_pkg.config.set("Debug::NoLocking", "false")
                # the lock count of the earlier tests (Debug::NoLocking
                # counts as well) would skip the real lock
                while True:
                    try:
                        apt.apt_pkg.pkgsystem_unlock()
                    except SystemError:
                        break
                ret = unattended_upgrade.main(options, rootdir=self.rootdir)
                with open(result, "w") as fp:
                    json.dump(self.dpkg_calls, fp)
            except BaseException:
                traceback.print_exc()
            finally:
                sys.stdout.flush()
                sys.stderr.flush()
                os._exit(ret)
        _, status = os.waitpid(pid, 0)
        self.assertTrue(os.path.exists(result), "main() failed in the child")
        with open(result) as fp:
            self.dpkg_calls = [tuple(call) for call in json.load(fp)]
        return os.WEXITSTATUS(status)

    def run_uu(self, dry_run=False, download_only=False):
        options = MockOptions()
        options.dry_run = dry_run
        options.download_only = download_only
        self.check_output = subprocess.check_output
        with patch.object(unattended_upgrade.subprocess, "check_output",
                          side_effect=self.fake_dpkg):
            self.ret = self.run_main_with_real_locks(options)
        with open(self.log) as fp:
            return fp.read()

    def test_dirty_journal_fixed(self):
        log = self.run_uu()
        # dpkg runs with the frontend lock held, like apt does
        self.assertEqual(self.dpkg_calls, [
            (["dpkg", "--force-confold", "--configure", "-a"], "1", False)])
        self.assertIn("Unclean dpkg state detected, trying to correct", log)
        self.assertIn("Setting up test-package (1.0) ...", log)
        # the run goes on as usual
        self.assertNotIn("Lock could not be acquired", log)
        self.assertIn("Packages that were upgraded: test-package", log)
        self.assertEqual(self.ret, 0)

    def test_dirty_journal_another_package_manager(self):
        # a running package manager has entries in the journal too, it
        # must not be reported as an unclean dpkg state (LP: #754330)
        holder = subprocess.Popen(
            [sys.executable, "-c", TRY_LOCK + "print(flush=True)\n"
             "sys.stdin.read()", self.frontend_lock],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.addCleanup(holder.wait)
        self.addCleanup(holder.stdin.close)
        holder.stdout.readline()
        log = self.run_uu()
        self.assertEqual(self.dpkg_calls, [])
        self.assertNotIn("Unclean dpkg state detected", log)
        self.assertIn("Lock could not be acquired", log)
        self.assertEqual(self.ret, 1)

    def test_dirty_journal_dry_run(self):
        log = self.run_uu(dry_run=True)
        self.assertEqual(self.dpkg_calls, [])
        self.assertNotIn("Unclean dpkg state detected", log)
        self.assertTrue(os.path.exists(self.journal))

    def test_dirty_journal_download_only(self):
        # the daily download run of apt-daily.service leaves it to the
        # install run of apt-daily-upgrade.service
        log = self.run_uu(download_only=True)
        self.assertEqual(self.dpkg_calls, [])
        self.assertNotIn("Unclean dpkg state detected", log)
        self.assertTrue(os.path.exists(self.journal))

    def test_dirty_journal_auto_fix_disabled(self):
        with open(self.apt_conf, "a") as fp:
            fp.write('Unattended-Upgrade::AutoFixInterruptedDpkg "false";\n')
        log = self.run_uu()
        self.assertEqual(self.dpkg_calls, [])
        # apt refuses to lock with a dirty journal
        self.assertIn("Lock could not be acquired", log)
        self.assertEqual(self.ret, 1)

    def test_clean_journal(self):
        os.unlink(self.journal)
        log = self.run_uu()
        self.assertEqual(self.dpkg_calls, [])
        self.assertNotIn("Unclean dpkg state detected", log)
        self.assertIn("Packages that were upgraded: test-package", log)
        self.assertEqual(self.ret, 0)


if __name__ == "__main__":
    # do not setup logging in here or the test will break
    unittest.main()
