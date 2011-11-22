#!/usr/bin/python

import apt
import logging
import glob
import os
import re
import shutil
import subprocess
import sys
import time
import unittest

# debian
#SOURCES_LIST="""
#deb http://ftp.de.debian.org/debian squeeze main contrib non-free
#deb http://ftp.de.debian.org/debian squeeze-updates main contrib non-free
#deb http://ftp.de.debian.org/debian squeeze-proposed-updates main contrib non-f#ree
#deb http://security.debian.org squeeze/updates main contrib non-free
#"""
#DISTRO="squeeze"
#ARCH="i386"
#TARBALL="%s-%s.tgz" % (DISTRO, ARCH)
#MIRROR="http://ftp.de.debian.org/debian"
#APT_CONF="""APT::Architecture "%s";""" % ARCH
#ORIGINS_PATTERN="origin=Debian,archive=stable,label=Debian-Security"


# ubuntu
SOURCES_LIST="""
deb http://archive.ubuntu.com/ubuntu/ lucid main restricted
deb-src http://archive.ubuntu.com/ubuntu/ lucid main restricted

deb http://archive.ubuntu.com/ubuntu/ lucid-updates main restricted
deb-src http://archive.ubuntu.com/ubuntu/ lucid-updates main restricted

deb http://security.ubuntu.com/ubuntu/ lucid-security main restricted
deb-src http://security.ubuntu.com/ubuntu/ lucid-security main restricted
"""
DISTRO="lucid"
ARCH="i386"
TARBALL="%s-%s.tgz" % (DISTRO, ARCH)
MIRROR="http://archive.ubuntu.com/ubuntu"
APT_CONF="""APT::Architecture "%s";""" % ARCH
ORIGINS_PATTERN="origin=Ubuntu,archive=lucid-security"

apt.apt_pkg.config.set("APT::Architecture", ARCH)
sys.path.insert(0, "..")
import unattended_upgrade

class MockOptions(object):
    debug = True
    dry_run = False
    minimal_upgrade_steps = False

class TestUnattendedUpgrade(unittest.TestCase):

    def _create_new_debootstrap_tarball(self, tarball, target):
        print "creating initial test tarball, this is needed only once"
        # force i386
        subprocess.call(["debootstrap",
                         "--arch=%s" % ARCH,
                         DISTRO, 
                         target,
                         MIRROR])
        subprocess.call(["chroot", target, "apt-get", "clean"])
        subprocess.call(["tar", "czf", tarball, target])

    def _unpack_debootstrap_tarball(self, tarball, target):
        subprocess.call(["tar", "xzf", tarball])

    def test_normal_upgrade(self):
        print "Running normal unattended upgrade in chroot"
        options = MockOptions()
        options.minimal_upgrade_steps = False
        self._run_upgrade_test_in_real_chroot(options)

    def test_minimal_steps_upgrade(self):
        print "Running minimal steps unattended upgrade in chroot"
        options = MockOptions()
        options.minimal_upgrade_steps = True
        self._run_upgrade_test_in_real_chroot(options)

    def _run_upgrade_test_in_real_chroot(self, options):
        """ helper that runs the unattended-upgrade in a chroot
            and does some basic verifications
        """
        if os.getuid() != 0:
            print "Skipping because uid != 0"
            return

        # clear to avoid pollution in the chroot
        apt.apt_pkg.config.clear("Acquire::http::ProxyAutoDetect")

        # create chroot
        target = "./test-chroot.%s" % DISTRO
        # cleanup 
        if os.path.exists(target):
            shutil.rmtree(target)
        if not os.path.exists(TARBALL):
            self._create_new_debootstrap_tarball(TARBALL, target)
        # create new
        self._unpack_debootstrap_tarball(TARBALL, target)
        open(os.path.join(target, "etc/apt/apt.conf"), "w").write(APT_CONF)
        open(os.path.join(target, "etc/apt/sources.list"), "w").write(
            SOURCES_LIST)
        # and run the upgrade test
        pid = os.fork()
        if pid == 0:
            # chroot
            os.chroot(target)
            os.chdir("/")
            if not os.path.exists("/var/log/unattended-upgrades/"):
                os.makedirs("/var/log/unattended-upgrades/")
            # make sure we are up-to-date
            subprocess.call(["apt-get","update", "-q", "-q"])
            # run it
            apt.apt_pkg.config.clear("Unattended-Upgrade::Allowed-Origins")
            apt.apt_pkg.config.clear("Unattended-Upgrade::Origins-Pattern")
            apt.apt_pkg.config.set(
                "Unattended-Upgrade::Origins-Pattern::", ORIGINS_PATTERN)
            unattended_upgrade.DISTRO_CODENAME = "lucid"
            unattended_upgrade.main(options)
            os._exit(0)
        else:
            has_progress=True
            all_progress = ""
            progress_log = os.path.join(
                target, "var/run/unattended-upgrades.progress")
            while True:
                time.sleep(0.01)
                if os.path.exists(progress_log):
                    progress = open(progress_log).read()
                    if progress:
                        has_progress &= progress.startswith("Progress")
                    all_progress += progress
                # check exit status
                (apid, status) = os.waitpid(pid, os.WNOHANG)
                if pid == apid:
                    ret = os.WEXITSTATUS(status)
                    break
        #print "*******************", all_progress
        self.assertEqual(ret, 0)
        self.assertTrue(has_progress, True)
        # this is a bit random, we just want to be sure we have data
        self.assertTrue(len(all_progress) > 10)
        # examine log
        log = os.path.join(
            target, "var/log/unattended-upgrades/unattended-upgrades.log")
        logfile = open(log).read()
        #print logfile
        self.assertNotEqual(
            re.search("Packages that are upgraded:.*bzip2", logfile), None)
        self.assertFalse("ERROR Installing the upgrades failed" in logfile)
        dpkg_log = os.path.join(target, "var/log/unattended-upgrades/*-dpkg*.log")
        dpkg_logfile = open(glob.glob(dpkg_log)[0]).read()
        self.assertTrue("Preparing to replace bzip2 1.0.5-4" in dpkg_logfile)
        #print dpkg_logfile


if __name__ == "__main__":
    #logging.basicConfig(level=logging.DEBUG)
    unittest.main()
