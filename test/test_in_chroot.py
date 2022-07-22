#!/usr/bin/python3

import logging
import glob
import os
import re
import shutil
import subprocess
import time
import unittest

import apt_pkg

apt_pkg.config.set("Dir", os.path.join(os.path.dirname(__file__), "aptroot"))
import apt

# debian
# SOURCES_LIST="""
# deb http://ftp.de.debian.org/debian squeeze main contrib non-free
# deb http://ftp.de.debian.org/debian squeeze-updates main contrib non-free
# deb http://ftp.de.debian.org/debian squeeze-proposed-updates main contrib \
#  non-free
# deb http://security.debian.org squeeze/updates main contrib non-free
# """
# DISTRO="squeeze"
# ARCH="i386"
# TARBALL="%s-%s.tgz" % (DISTRO, ARCH)
# MIRROR="http://ftp.de.debian.org/debian"
# APT_CONF="""APT::Architecture "%s";""" % ARCH
# ORIGINS_PATTERN="origin=Debian,archive=stable,label=Debian-Security"


# ubuntu
SOURCES_LIST = """
deb http://archive.ubuntu.com/ubuntu/ lucid main restricted
deb-src http://archive.ubuntu.com/ubuntu/ lucid main restricted

deb http://archive.ubuntu.com/ubuntu/ lucid-updates main restricted
deb-src http://archive.ubuntu.com/ubuntu/ lucid-updates main restricted

deb http://security.ubuntu.com/ubuntu/ lucid-security main restricted
deb-src http://security.ubuntu.com/ubuntu/ lucid-security main restricted
"""
DISTRO = "lucid"
ARCH = "i386"
TARBALL = "%s-%s.tgz" % (DISTRO, ARCH)
MIRROR = "http://archive.ubuntu.com/ubuntu"
APT_CONF = """APT::Architecture "%s";""" % ARCH
ORIGINS_PATTERN = "origin=Ubuntu,archive=lucid-security"

apt.apt_pkg.config.set("APT::Architecture", ARCH)

import unattended_upgrade
from test.test_base import TestBase, MockOptions


class TestUnattendedUpgrade(TestBase):
    def _create_new_debootstrap_tarball(self, tarball, target):
        print("creating initial test tarball, this is needed only once")
        # force i386
        subprocess.call(
            [
                "debootstrap",
                "--arch=%s" % ARCH,
                # smaller version of the minimal system
                "--variant=minbase",
                "--include=python-apt,apt-utils,gpgv,ubuntu-keyring," "ca-certificates",
                DISTRO,
                target,
                MIRROR,
            ]
        )
        subprocess.call(["chroot", target, "apt-get", "clean"])
        subprocess.call(["tar", "czf", tarball, target])

    def _unpack_debootstrap_tarball(self, tarball, target):
        subprocess.call(["tar", "xzf", tarball])

    @unittest.skip("FIXME: test needs porting")
    @unittest.skipIf(os.getuid() != 0, "must run as root")
    def setUp(self):
        TestBase.setUp(self)

    def test_normal_upgrade(self):
        print("Running normal unattended upgrade in chroot")
        options = MockOptions()
        options.minimal_upgrade_steps = True
        # run it
        target = self._run_upgrade_test_in_real_chroot(options)
        # ensure we upgraded the expected packages
        self.assertTrue(
            self._verify_install_log_in_real_chroot(target, "ca-certificates")
        )

    def test_non_minimal_steps_upgrade(self):
        print("Running non-minimal steps unattended upgrade in chroot")
        options = MockOptions()
        options.minimal_upgrade_steps = False
        # run it
        target = self._run_upgrade_test_in_real_chroot(options)
        # ensure we upgraded the expected packages
        self.assertTrue(
            self._verify_install_log_in_real_chroot(target, "ca-certificates")
        )

    def test_upgrade_on_shutdown_upgrade(self):
        print(
            "Running unattended upgrade on shutdown (download and install) " "in chroot"
        )
        # ensure that it actually installs in shutdown env mode
        options = MockOptions()
        os.environ["UNATTENDED_UPGRADES_FORCE_INSTALL_ON_SHUTDOWN"] = "1"
        apt.apt_pkg.config.set("Unattended-Upgrade::InstallOnShutdown", "1")
        target = self._run_upgrade_test_in_real_chroot(options)
        self.assertTrue(
            self._verify_install_log_in_real_chroot(target, "ca-certificates")
        )

    def test_whitelist_upgrade(self):
        print("Running unattended upgrade in chroot with whitelisted pkg")
        options = MockOptions()
        apt.apt_pkg.config.set("Unattended-Upgrade::Package-Whitelist::", "^libc6$")
        # run it
        target = self._run_upgrade_test_in_real_chroot(options)
        # libc6 has a strict dependency on libc-bin so both packages
        # will have to get installed. ensure that the relaxed whitelist is ok
        self.assertTrue(self._verify_install_log_in_real_chroot(target, "libc6"))
        self.assertFalse(
            self._verify_install_log_in_real_chroot(target, "ca-certificates")
        )
        apt.apt_pkg.config.clear("Unattended-Upgrade::Package-Whitelist")

    def test_whitelist_upgrade_strict(self):
        print("Running unattended upgrade in chroot with strict whitelisted pkg")
        options = MockOptions()
        apt.apt_pkg.config.set("Unattended-Upgrade::Package-Whitelist::", "^apt$")
        apt.apt_pkg.config.set("Unattended-Upgrade::Package-Whitelist::", "^libc6$")
        apt.apt_pkg.config.set("Unattended-Upgrade::Package-Whitelist-Strict", "true")
        # run it
        target = self._run_upgrade_test_in_real_chroot(options)
        # we upgraded apt, but not libc6 because libc6 needs libc-bin and
        # its not whitelisted (in strict mode)
        self.assertTrue(self._verify_install_log_in_real_chroot(target, "apt"))
        self.assertFalse(self._verify_install_log_in_real_chroot(target, "libc6"))
        self.assertFalse(self._verify_install_log_in_real_chroot(target, "libc-bin"))
        apt.apt_pkg.config.clear("Unattended-Upgrade::Package-Whitelist")

    def _get_logfile_location(self, target):
        return os.path.join(
            target, "var/log/unattended-upgrades/unattended-upgrades.log"
        )

    def _setup_chroot(self, target):
        """ helper that setups a clean chroot """
        if os.path.exists(target):
            subprocess.call(["umount", os.path.join(target, "dev", "pts")])
            shutil.rmtree(target)
        if not os.path.exists(TARBALL):
            self._create_new_debootstrap_tarball(TARBALL, target)
        # create new
        self._unpack_debootstrap_tarball(TARBALL, target)
        open(os.path.join(target, "etc/apt/apt.conf"), "w").write(APT_CONF)
        open(os.path.join(target, "etc/apt/sources.list"), "w").write(SOURCES_LIST)

    def _run_upgrade_test_in_real_chroot(self, options, clean_chroot=True):
        """ helper that runs the unattended-upgrade in a chroot
            and does some basic verifications
        """
        # clear to avoid pollution in the chroot
        apt.apt_pkg.config.clear("Acquire::http::ProxyAutoDetect")

        # create chroot
        target = "./test-chroot.%s" % DISTRO

        # setup chroot if needed
        if clean_chroot:
            self._setup_chroot(target)

        # ensure we have /dev/pts in the chroot
        ret = subprocess.call(
            ["mount", "-t", "devpts", "devptsfs", os.path.join(target, "dev", "pts")]
        )
        if ret != 0:
            raise Exception("Failed to mount %s/proc" % target)
        self.addCleanup(
            lambda: subprocess.call(["umount", os.path.join(target, "dev", "pts")])
        )

        # and run the upgrade test
        pid = os.fork()
        if pid == 0:
            # chroot
            os.chroot(target)
            os.chdir("/")
            if not os.path.exists("/var/log/unattended-upgrades/"):
                os.makedirs("/var/log/unattended-upgrades/")
            # make sure we are up-to-date
            subprocess.call(["apt-get", "update", "-q", "-q"])
            # run it
            apt.apt_pkg.config.clear("Unattended-Upgrade::Allowed-Origins")
            apt.apt_pkg.config.clear("Unattended-Upgrade::Origins-Pattern")
            apt.apt_pkg.config.set(
                "Unattended-Upgrade::Origins-Pattern::", ORIGINS_PATTERN
            )
            unattended_upgrade.DISTRO_CODENAME = DISTRO
            unattended_upgrade.main(options)
            os._exit(0)
        else:
            has_progress = False
            all_progress = ""
            last_progress = ""
            progress_log = os.path.join(target, "var/run/unattended-upgrades.progress")
            while True:
                time.sleep(0.01)
                if os.path.exists(progress_log):
                    progress = open(progress_log).read()
                    if progress and progress != last_progress:
                        has_progress = progress.startswith("Progress")
                        last_progress = progress
                    all_progress += progress
                # check exit status
                (apid, status) = os.waitpid(pid, os.WNOHANG)
                if pid == apid:
                    ret = os.WEXITSTATUS(status)
                    break
        # print("*******************", all_progress)
        self.assertEqual(ret, 0)
        # this number is a bit random, we just want to be sure we have
        # progress data
        self.assertTrue(has_progress, True)
        self.assertTrue(len(all_progress) > 5)
        return target

    def _verify_install_log_in_real_chroot(self, target, needle_pkg):
        # examine log
        log = self._get_logfile_location(target)
        logfile = open(log).read()
        # print(logfile)
        if not re.search("Packages that will be upgraded:.*%s" % needle_pkg,
                         logfile):
            logging.warn(
                "Can not find expected %s upgrade in log" % needle_pkg)
            return False
        if "ERROR Installing the upgrades failed" in logfile:
            logging.warn("Got a ERROR in the logfile")
            return False
        dpkg_log = os.path.join(target, "var/log/unattended-upgrades/*-dpkg*.log")
        dpkg_logfile = open(glob.glob(dpkg_log)[0]).read()
        if not "Preparing to replace %s" % needle_pkg in dpkg_logfile:
            logging.warn("Did not find %s upgrade in %s" % (dpkg_log, needle_pkg))
            return False
        # print(dpkg_logfile)
        return True


if __name__ == "__main__":
    # logging.basicConfig(level=logging.DEBUG)
    unittest.main()
